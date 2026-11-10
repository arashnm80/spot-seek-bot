from variables import *
import re
import requests  # for get_redirect_link / oembed / private-router
from db_functions import (
    get_telegram_audio_id,
    get_cached_collection_track_ids,
    save_cached_collection_track_ids,
    normalize_search_query,
    get_cached_search_results,
    save_cached_search_results,
)
from log import *

# Spotify Web API credentials live in private-router (diamond Premium account).


def _router_headers():
    if not private_router_token:
        raise RuntimeError("PRIVATE_ROUTER_TOKEN is not set")
    return {"Authorization": f"Bearer {private_router_token}"}


def _router_post(path, payload, timeout=60):
    url = f"{private_router_url}{path}"
    response = requests.post(url, headers=_router_headers(), json=payload, timeout=timeout)
    if not response.ok:
        detail = response.text[:500]
        raise RuntimeError(f"private-router {path} -> {response.status_code}: {detail}")
    return response.json()


def get_redirect_link(shortened_link):
    response = warp_session.head(shortened_link, allow_redirects=True, timeout=15)
    return response.url

def get_link_type(text):
    if re.match(spotify_track_link_pattern, text):
        return "track"
    elif re.match(spotify_album_link_pattern, text):
        return "album"
    elif re.match(spotify_playlist_link_pattern, text):
        return "playlist"
    elif re.match(spotify_shortened_link_pattern, text):
        return "shortened"
    else:
        return False

def get_valid_spotify_links(text):
    regexes = [spotify_shortened_link_pattern, spotify_track_link_pattern, spotify_album_link_pattern, spotify_playlist_link_pattern]
    # Create a compiled regular expression object
    # by joining the regex patterns with the OR operator |
    regex_combined = re.compile("|".join(regexes))
    # Find all matches and store them in a list
    all_matches = [match.group() for match in regex_combined.finditer(text)]
    print(all_matches) # as debug
    return all_matches

def get_track_ids(link):    
    # get id of link, album or playlist
    link_id = link.split("/")[-1].split("?")[0]

    link_type = get_link_type(link)
    if link_type == "track":
        # extract track id directly from link without api
        return [link_id]
    if link_type not in ("album", "playlist"):
        return []

    ttl = album_cache_ttl_seconds if link_type == "album" else playlist_cache_ttl_seconds
    cached = get_cached_collection_track_ids(link_type, link_id)
    if cached:
        track_ids, age = cached
        if age <= ttl and track_ids:
            print(f"collection cache hit: {link_type} {link_id} ({len(track_ids)} tracks, {age // 86400}d old)")
            return track_ids

    try:
        if link_type == "album":
            data = _router_post("/v1/spotify/albums/tracks", {"album_id": link_id})
        else:
            data = _router_post("/v1/spotify/playlists/tracks", {"playlist_id": link_id})
        track_ids = data.get("track_ids") or []
    except Exception as e:
        log(f"collection fetch failed for {link_type} {link_id}: {e}")
        if cached and cached[0]:
            print(f"collection cache stale fallback: {link_type} {link_id}")
            return cached[0]
        raise

    if track_ids:
        save_cached_collection_track_ids(link_type, link_id, track_ids)
    return track_ids

def get_track_image(track_id):
    """Cover URL. oembed first: Web API is not needed for covers when oembed works."""
    oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/track/{track_id}"
    try:
        r = warp_session.get(oembed_url, timeout=10)
        r.raise_for_status()
        return r.json()["thumbnail_url"]
    except Exception as e:
        log(f"oembed get_track_image failed, trying private-router:\n{e}")
        data = _router_post("/v1/spotify/tracks/get", {"track_id": track_id})
        image = data.get("album_image_url")
        if not image:
            raise RuntimeError(f"no album image for track {track_id}")
        return image

# search for a track name in spotify and return their track ids
def _artist_name(track):
    artists = track.get("artists") or []
    if not artists:
        return ""
    first = artists[0]
    if isinstance(first, dict):
        return first.get("name") or ""
    return str(first)


def _album_name(track):
    album = track.get("album") or {}
    if isinstance(album, dict):
        return album.get("name") or ""
    return ""


def _parse_search_hits(items):
    parsed = []
    seen = set()
    for track in items:
        track_id = track.get("id") or track.get("track_id")
        if not track_id or track_id in seen:
            continue
        seen.add(track_id)
        name = track.get("name") or ""
        artist = _artist_name(track)
        parsed.append({
            "id": track_id,
            "name": name,
            "artist": artist,
            "uri": track.get("uri") or f"spotify:track:{track_id}",
            "url": (track.get("external_urls") or {}).get("spotify")
            or f"https://open.spotify.com/track/{track_id}",
            "album": _album_name(track),
        })
    return parsed


def _parse_album_hits(items):
    parsed = []
    seen = set()
    for album in items:
        album_id = album.get("id")
        if not album_id or album_id in seen:
            continue
        seen.add(album_id)
        name = album.get("name") or ""
        artist = _artist_name(album)
        parsed.append({
            "id": album_id,
            "name": name,
            "artist": artist,
            "url": (album.get("external_urls") or {}).get("spotify")
            or f"https://open.spotify.com/album/{album_id}",
            "total_tracks": album.get("total_tracks") or 0,
        })
    return parsed


def _album_from_track(track):
    album = track.get("album")
    if not isinstance(album, dict):
        return None
    album_id = album.get("id")
    if not album_id:
        uri = album.get("uri") or ""
        if "album:" in uri:
            album_id = uri.split("album:")[-1]
    if not album_id:
        return None
    return {
        "id": album_id,
        "name": album.get("name") or "",
        "artists": album.get("artists") or track.get("artists") or [],
        "external_urls": album.get("external_urls") or {},
        "total_tracks": album.get("total_tracks") or 0,
    }


def _search_spotify_hits(query, limit):
    data = _router_post(
        "/v1/spotify/search",
        {"q": query, "type": "track", "limit": limit},
        timeout=90,
    )
    return _parse_search_hits(data.get("items") or [])


def _search_album_hits(query, limit):
    try:
        data = _router_post(
            "/v1/spotify/search",
            {"q": query, "type": "album", "limit": limit},
            timeout=90,
        )
        parsed = _parse_album_hits(data.get("items") or [])
        if parsed:
            return parsed
    except Exception as e:
        log(f"album search failed, trying albums from tracks:\n{e}")
    track_data = _router_post(
        "/v1/spotify/search",
        {"q": query, "type": "track", "limit": 40},
        timeout=90,
    )
    raw_tracks = track_data.get("items") or []
    albums = [_album_from_track(t) for t in raw_tracks]
    return _parse_album_hits([a for a in albums if a])[:limit]


def _query_matches(query, name, artist):
    tokens = [tok for tok in query.lower().split() if len(tok) > 1]
    if not tokens:
        return True
    hay = f"{name} {artist}".lower()
    return all(tok in hay for tok in tokens)


def _search_cache_age_label(age):
    if age < 3600:
        return f"cache ({age // 60}m old)"
    if age < 86400:
        return f"cache ({age // 3600}h old)"
    return f"cache ({age // 86400}d old)"


def search_spotify_items(query, kind="track", require_in_db=False):
    """Spotify search. kind is track or album. Inline track search must set require_in_db."""
    kind = "album" if kind == "album" else "track"
    limit = 40 if kind == "track" else 20
    query_key = normalize_search_query(query)
    cache_key = f"{kind}:{query_key}" if query_key else None
    cached = get_cached_search_results(cache_key) if cache_key else None
    # Older track cache rows were stored without a kind prefix.
    if cached is None and kind == "track" and query_key:
        cached = get_cached_search_results(query_key)
    parsed = None
    source = "spotify"

    if cached:
        hits, age = cached
        if age <= search_cache_ttl_seconds and hits:
            parsed = [dict(t) for t in hits]
            source = _search_cache_age_label(age)

    if parsed is None:
        try:
            if kind == "album":
                parsed = _search_album_hits(query, limit)
            else:
                parsed = _search_spotify_hits(query, limit)
            if parsed and cache_key:
                save_cached_search_results(cache_key, parsed)
        except Exception as e:
            if cached and cached[0]:
                parsed = [dict(t) for t in cached[0]]
                source = f"stale cache after search error: {e}"
                log(f"{kind} search {query!r} failed, using stale cache:\n{e}")
            else:
                raise

    if kind == "track":
        for track in parsed:
            track["telegram_audio_id"] = get_telegram_audio_id(track["id"])

    relevant = [t for t in parsed if _query_matches(query, t["name"], t["artist"])]
    pool = relevant if relevant else parsed
    if require_in_db:
        pool = [t for t in pool if t.get("telegram_audio_id")]
    out = pool[:10]
    in_db = sum(1 for t in out if t.get("telegram_audio_id")) if kind == "track" else 0
    extra = f", {in_db}/{len(out)} in db" if kind == "track" else ""
    log(
        f"{kind} search {query!r}: {len(parsed)} hits via {source}, "
        f"{len(relevant)} relevant, {len(out)} shown{extra}"
    )
    return out


def search_track_ids(query, require_in_db=False):
    """Spotify track search. Chat search can include not-yet-downloaded tracks; inline cannot."""
    return search_spotify_items(query, kind="track", require_in_db=require_in_db)

def get_track_info_from_track_id(track_id):
    '''return "{artist} - {name}" from track id'''
    data = _router_post("/v1/spotify/tracks/get", {"track_id": track_id})
    return data.get("label") or f"{data.get('artist', '')} - {data.get('name', '')}"
