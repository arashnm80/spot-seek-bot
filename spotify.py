import re
from variables import spotify_song_link_pattern, spotify_song_id_pattern

def valid_song_link(text):
    return bool(re.match(spotify_song_link_pattern, text))

def get_all_song_links(text):
    matches = re.findall(spotify_song_link_pattern, text)
    return matches

def get_song_id(song_link):
    # use regex to extract the song ID from the link
    match = re.search(spotify_song_id_pattern, song_link)
    if match:
        # the song ID is captured in the first group of the regex match
        song_id = match.group(1)
        print(song_id)
    else:
        print("No match found")

#######################################################################################
"""
x = input("enter: ")
print(get_all_song_links(x))
y = [2]
if y:
    print("ok")
"""
