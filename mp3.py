import subprocess
from variables import directory
from mutagen.mp3 import MP3 # duration, artist, title

def change_cover_image(input_mp3, input_image, folder_path):
    output_file = 'output.mp3'
    low_size_image = "cover_low.jpg"

    # reduce image size to 320 * 320
    image_size_command = f"ffmpeg -i \"{input_image}\" -vf \"scale=320:-1\" -loglevel quiet \"{low_size_image}\""
    subprocess.run(image_size_command, shell=True, cwd=folder_path, timeout=300)
    print("image size reduced to 320*320 successfully")
    
    # add image cover to song
    add_cover_command = f"ffmpeg -i \"{input_mp3}\" -i \"{input_image}\" -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title='Album cover' -metadata:s:v comment='Cover (front)' -loglevel quiet \"{output_file}\""
    subprocess.run(add_cover_command, shell=True, cwd=folder_path, timeout=300)
    print("image set for to song cover")

    # delete old mp3 and rename new one to it
    subprocess.run(f"rm \"{input_mp3}\"", shell=True, cwd=folder_path, timeout=300)
    subprocess.run(f"mv \"{output_file}\" \"{input_mp3}\"", shell=True, cwd=folder_path, timeout=300)
    print("new mp3 replaced old one")

def get_track_duration(file):
    audio = MP3(file)
    return int(audio.info.length)

def get_artist_name_from_track(file):
    audio = MP3(file)
    artist = audio["TPE1"].text[0]
    return artist

def get_track_title(file):
    audio = MP3(file)
    title = audio.get("TIT2")
    if title:
        track_title = title.text[0]
        return track_title
    else:
        return "No Track Name Error"
