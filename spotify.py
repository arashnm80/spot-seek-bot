import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests # for get_redirect_link
import random
from spotipy_anon import SpotifyAnon
from variables import *
from csv_functions import get_telegram_audio_id

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

def get_track_ids(link):
    # experimental new multiple spotify app system
    spotify_app = random.choice(spotify_apps_list)
    spotify_client_id = spotify_app[0]
    spotify_client_secret = spotify_app[1]
    #Authentication - without user
    client_credentials_manager = SpotifyClientCredentials(client_id=spotify_client_id, client_secret=spotify_client_secret)
    # spotipy instance with warp_session and spotifyAnon - remove auth_manager to use without SpotifyAnon
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager, requests_session=warp_session, auth_manager=SpotifyAnon())
    
    # get id of link, album or playlist
    link_id = link.split("/")[-1].split("?")[0]

    link_type = get_link_type(link)
    if link_type == "track":
        # extract track id directly from link without api
        track_ids = [link_id]
    elif link_type == "album":
        tracks = sp.album_tracks(link_id)["items"]
        track_ids = [t["id"] for t in tracks]
    elif link_type == "playlist":
        # handle spotify results paginated in 100 items 
        # https://stackoverflow.com/questions/39086287/spotipy-how-to-read-more-than-100-tracks-from-a-playlist
        results = sp.playlist_tracks(link_id)
        tracks = results['items']
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
        track_ids = []
        for t in tracks:
            try:
                if ("track" in t) and (t["track"] is not None) and ("id" in t["track"]) and (t["track"]["id"] is not None):
                    # due to a bug, a small number of tracks in playlists don't have
                    # ["track"]["id"] and cause the program to crash
                    # like 75th track in https://open.spotify.com/playlist/64r1Ry0JIWHboowR4LWp5R
                    # which is https://open.spotify.com/track/46cdw28EXOhDPnD1emDC6T
                    # so we check and make sure this field exists
                    track_ids.append(t["track"]["id"])
            except:
                print("error in getting a track id")
    else:
        return []

    return(track_ids)

def get_track_image(track_link):
    # experimental new multiple spotify app system
    spotify_app = random.choice(spotify_apps_list)
    spotify_client_id = spotify_app[0]
    spotify_client_secret = spotify_app[1]

    #Authentication - without user
    client_credentials_manager = SpotifyClientCredentials(client_id=spotify_client_id, client_secret=spotify_client_secret)
    sp = spotipy.Spotify(client_credentials_manager = client_credentials_manager, requests_session=warp_session)
    
    track_id = track_link.split("/")[-1].split("?")[0]
    track = sp.track(track_id)
    cover_image_url = track['album']['images'][0]['url']
    
    return cover_image_url

# search for a track name in spotify and return their track ids
def search_track_ids(query):
# experimental new multiple spotify app system
    spotify_app = random.choice(spotify_apps_list)
    spotify_client_id = spotify_app[0]
    spotify_client_secret = spotify_app[1]
    #Authentication - without user
    client_credentials_manager = SpotifyClientCredentials(client_id=spotify_client_id, client_secret=spotify_client_secret)
    # spotipy instance with warp_session and spotifyAnon - remove auth_manager to use without SpotifyAnon
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager, requests_session=warp_session, auth_manager=SpotifyAnon())
    
    # Perform a search for tracks using the provided query
    results = sp.search(q=query, type='track', limit=5)
    
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