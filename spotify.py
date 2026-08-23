from variables import *
import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.cache_handler import MemoryCacheHandler
import requests # for get_redirect_link
import random
from spotipy_anon import SpotifyAnon
from db_functions import (
    get_telegram_audio_id,
    get_cached_collection_track_ids,
    save_cached_collection_track_ids,
)
from log import *
import time

def _spotipy_auth_manager():
    """None = official client credentials. SpotifyAnon = old web-player path."""
    if spotify_auth_mode == "anon":
        return SpotifyAnon()
    return None

# auth_manager=None means official client credentials (no web-player token).
def create_spotipy_instance(requests_session=warp_session, auth_manager=None):
    # random spotify app from list to avoid rate limiting
    random.seed(time.time())
    spotify_app = random.choice(spotify_apps_list)
    spotify_client_id = spotify_app[0]
    spotify_client_secret = spotify_app[1]
    # Authentication - without user
    # Memory cache only: a .cache file can keep a token minted during the
    # Premium-owner 403 window and replay it for up to an hour.
    client_credentials_manager = SpotifyClientCredentials(
        client_id=spotify_client_id,
        client_secret=spotify_client_secret,
        cache_handler=MemoryCacheHandler(),
    )
    # spotipy instance
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager,
                         requests_session=requests_session,
                         auth_manager=auth_manager)
    return sp
    # fixme: looks like spotipy.Spitify requests_session has True/False values, not a session object.
    # fixme: update: despite above sentence, looks like that's the correct way to use it.
    # there is another `proxies` parameter in it. check it out.

def get_redirect_link(shortened_link):
    response = requests.head(shortened_link, allow_redirects=True)
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

def _track_ids_from_playlist_items(items):
    track_ids = []
    for t in items:
        try:
            if ("track" in t) and (t["track"] is not None) and ("id" in t["track"]) and (t["track"]["id"] is not None):
                # due to a bug, a small number of tracks in playlists don't have
                # ["track"]["id"] and cause the program to crash
                # like 75th track in https://open.spotify.com/playlist/64r1Ry0JIWHboowR4LWp5R
                # which is https://open.spotify.com/track/46cdw28EXOhDPnD1emDC6T
                # so we check and make sure this field exists
                track_ids.append(t["track"]["id"])
        except Exception:
            print("error in getting a track id")
    return track_ids

def _paginate_spotipy_playlist(sp, playlist_id):
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return _track_ids_from_playlist_items(tracks)

def get_playlist_track_ids_via_anon(playlist_id):
    """Previous path: official client credentials, then SpotifyAnon on failure."""
    sp = create_spotipy_instance(auth_manager=None)
    try:
        return _paginate_spotipy_playlist(sp, playlist_id)
    except Exception as e:
        log(f"🛑 error in getting playlist tracks:\n\n{e}\n\n\ntrying again with spotipyAnon:")
        sp = create_spotipy_instance(auth_manager=SpotifyAnon())
        track_ids = _paginate_spotipy_playlist(sp, playlist_id)
        log("spotifyAnon worked fine✅")
        return track_ids

def get_album_track_ids_via_partner(album_id):
    """SpotipyFree album tracks (sync). Official album_tracks can 403 on a stale Spotipy token."""
    from SpotipyFree import Spotify as FreeSpotify
    results = FreeSpotify().album_tracks(album_id)
    items = results["items"] if isinstance(results, dict) else results
    return [t["id"] for t in items if t.get("id")]

def get_playlist_track_ids_via_partner(playlist_id):
    """SpotipyFree / api-partner, sync paginate (playlist_items() breaks inside uvicorn's event loop)."""
    import spotapi
    from SpotipyFree.Formatter import SpotifyFormatter
    track_ids = []
    for chunk in spotapi.PublicPlaylist(playlist_id).paginate_playlist():
        for track in chunk.get("items") or []:
            try:
                meta = SpotifyFormatter.formatPlaylistTrack(track)
                tid = (meta.get("track") or {}).get("id")
                if tid:
                    track_ids.append(tid)
            except Exception:
                print("error in getting a track id")
    return track_ids

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
            if spotify_auth_mode == "anon":
                sp = create_spotipy_instance(auth_manager=_spotipy_auth_manager())
                tracks = sp.album_tracks(link_id)["items"]
                track_ids = [t["id"] for t in tracks]
            else:
                track_ids = get_album_track_ids_via_partner(link_id)
        else:
            if spotify_auth_mode == "anon":
                track_ids = get_playlist_track_ids_via_anon(link_id)
            else:
                track_ids = get_playlist_track_ids_via_partner(link_id)
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
    """Cover URL. oembed first: official Web API often 403/timeouts and is not needed for covers."""
    oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/track/{track_id}"
    try:
        r = warp_session.get(oembed_url, timeout=10)
        r.raise_for_status()
        return r.json()["thumbnail_url"]
    except Exception as e:
        log(f"oembed get_track_image failed, trying official:\n{e}")
        sp = create_spotipy_instance(auth_manager=_spotipy_auth_manager())
        return sp.track(track_id)['album']['images'][0]['url']

# search for a track name in spotify and return their track ids
def search_track_ids(query):
    sp = create_spotipy_instance(auth_manager=_spotipy_auth_manager())
    # Perform a search for tracks using the provided query
    results = sp.search(q=query, type='track', limit=10)
    
    # Extract and return the relevant track information
    tracks = []
    for track in results['tracks']['items']:
        track_info = {
            'id': track['id'],
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'uri': track['uri'],
            'url': track['external_urls']['spotify'],
            'album': track['album']['name']
        }
        tracks.append(track_info)

    available_track_ids = []
    for track in tracks:
        telegram_audio_id = get_telegram_audio_id(track['id'])
        if telegram_audio_id is not None:
            track['telegram_audio_id'] = telegram_audio_id
            available_track_ids.append(track)
    
    return available_track_ids

def get_track_info_from_track_id(track_id):
    '''return "{artist} - {name}" from track id'''
    sp = create_spotipy_instance(auth_manager=_spotipy_auth_manager())
    track = sp.track(track_id)
    artist = track["artists"][0]["name"]
    name = track["name"]
    return f"{artist} - {name}"
