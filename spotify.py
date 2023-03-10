import re
from variables import spotify_track_link_pattern, spotify_album_link_pattern, spotify_playlist_link_pattern, spotify_client_id, spotify_client_secret
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

#def get_all_spotify_track_links(text):
#    matches = re.findall(spotify_track_link_pattern, text)
#    return matches

## TO-DO: remove later becuase functionality is embedded to retern_tracks()
#def get_spotify_track_id(track_link):
#    # use regex to extract the track ID from the link
#    match = re.search(spotify_track_id_pattern, track_link)
#    if match:
#        # the song ID is captured in the first group of the regex match
#        spotify_track_id = match.group(1)
#        return spotify_track_id
#    else:
#        return False

def get_track_ids(link):
    #Authentication - without user
    client_credentials_manager = SpotifyClientCredentials(client_id=spotify_client_id, client_secret=spotify_client_secret)
    sp = spotipy.Spotify(client_credentials_manager = client_credentials_manager)
    
    # get id of link, album or playlist
    track_id = link.split("/")[-1].split("?")[0]

    link_type = get_link_type(link)
    if link_type == "track":
        tracks = sp.track(track_id)
        track_ids = [tracks["id"]]
    elif link_type == "album":
        tracks = sp.album_tracks(track_id)["items"]
        track_ids = [t["id"] for t in tracks]
    elif link_type == "playlist":
        tracks = sp.playlist_tracks(track_id)["items"]
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

