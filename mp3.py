import subprocess
from variables import directory
from pydub import AudioSegment # to get song duration
from mutagen.mp3 import MP3 # to get artist name

def change_cover_image(input_mp3, input_image):
    output_file = 'output.mp3'
    low_size_image = "cover_low.jpg"

    # reduce image size to 320 * 320
    image_size_command = f"ffmpeg -i \"{input_image}\" -vf \"scale=320:-1\" -loglevel quiet \"{low_size_image}\""
    subprocess.run(image_size_command, shell=True, cwd=directory)
    print("image size reduced to 320*320 successfully")
    
    # add image cover to song
    add_cover_command = f"ffmpeg -i \"{input_mp3}\" -i \"{input_image}\" -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title='Album cover' -metadata:s:v comment='Cover (front)' -loglevel quiet \"{output_file}\""
    subprocess.run(add_cover_command, shell=True, cwd=directory)
    print("image set for to song cover")

    # delete old mp3 and rename new one to it
    subprocess.run(f"rm \"{input_mp3}\"", shell=True, cwd=directory)
    subprocess.run(f"mv \"{output_file}\" \"{input_mp3}\"", shell=True, cwd=directory)
    print("new mp3 replaced old one")

def get_track_duration(file): # note: this function is not optimized and crashes on large files
    audio_file = AudioSegment.from_file(file)
    duration_in_ms = len(audio_file)
    duration_in_sec = int(duration_in_ms / 1000)
    return duration_in_sec

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
