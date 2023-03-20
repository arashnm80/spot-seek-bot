import re
from variables import spotify_track_link_pattern, spotify_album_link_pattern, spotify_playlist_link_pattern, spotify_client_id, spotify_client_secret, welcome_message
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

def get_link_type(text):
    if re.match(spotify_track_link_pattern, text):
        return "track"
    elif re.match(spotify_album_link_pattern, text):
        return "album"
    elif re.match(spotify_playlist_link_pattern, text):
        return "playlist"
    else:
        return False

def get_valid_spotify_links(text):
    regexes = [spotify_track_link_pattern, spotify_album_link_pattern, spotify_playlist_link_pattern]
    # Create a compiled regular expression object
    # by joining the regex patterns with the OR operator |
    regex_combined = re.compile("|".join(regexes))
    # Find all matches and store them in a list
    all_matches = [match.group() for match in regex_combined.finditer(text)]
    return all_matches

def get_track_ids(link):
    #Authentication - without user
    client_credentials_manager = SpotifyClientCredentials(client_id=spotify_client_id, client_secret=spotify_client_secret)
    sp = spotipy.Spotify(client_credentials_manager = client_credentials_manager)
    
    # get id of link, album or playlist
    link_id = link.split("/")[-1].split("?")[0]

    link_type = get_link_type(link)
    if link_type == "track":
        tracks = sp.track(link_id)
        track_ids = [tracks["id"]]
    elif link_type == "album":
        tracks = sp.album_tracks(link_id)["items"]
        track_ids = [t["id"] for t in tracks]
    elif link_type == "playlist":
        # handle spotify results paginated in 100 items - https://stackoverflow.com/questions/39086287/spotipy-how-to-read-more-than-100-tracks-from-a-playlist
        results = sp.playlist_tracks(link_id)
        tracks = results['items']
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
        track_ids = [t["track"]["id"] for t in tracks]
    else:
        return []

    return(track_ids)

def get_track_image(track_link):
    #Authentication - without user
    client_credentials_manager = SpotifyClientCredentials(client_id=spotify_client_id, client_secret=spotify_client_secret)
    sp = spotipy.Spotify(client_credentials_manager = client_credentials_manager)
    
    track_id = track_link.split("/")[-1].split("?")[0]
    track = sp.track(track_id)
    cover_image_url = track['album']['images'][0]['url']
    
    return cover_image_url

