import os
import subprocess
from mutagen.mp3 import MP3 # duration, artist, title


def is_usable_cover(path):
    """True if path looks like a real JPEG/PNG/WebP, not an empty wget error page."""
    if not os.path.isfile(path) or os.path.getsize(path) < 100:
        return False
    with open(path, "rb") as fh:
        head = fh.read(12)
    if head.startswith(b"\xff\xd8") or head.startswith(b"\x89PNG"):
        return True
    return len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP"


def change_cover_image(input_mp3, input_image, folder_path):
    output_file = 'output.mp3'
    low_size_image = "cover_low.jpg"
    image_path = os.path.join(folder_path, input_image)
    if not is_usable_cover(image_path):
        raise RuntimeError(f"missing or invalid cover image: {input_image}")

    # reduce image size to 320 * 320
    sized = subprocess.run(
        ["ffmpeg", "-y", "-i", input_image, "-vf", "scale=320:-1",
         "-loglevel", "error", low_size_image],
        cwd=folder_path,
        timeout=300,
    )
    if sized.returncode != 0 or not is_usable_cover(os.path.join(folder_path, low_size_image)):
        raise RuntimeError("ffmpeg failed to create cover thumbnail")
    print("image size reduced to 320*320 successfully")

    # add image cover to song
    embedded = subprocess.run(
        [
            "ffmpeg", "-y", "-i", input_mp3, "-i", input_image,
            "-map", "0:0", "-map", "1:0", "-c", "copy", "-id3v2_version", "3",
            "-metadata:s:v", "title=Album cover",
            "-metadata:s:v", "comment=Cover (front)",
            "-loglevel", "error", output_file,
        ],
        cwd=folder_path,
        timeout=300,
    )
    output_path = os.path.join(folder_path, output_file)
    if embedded.returncode != 0 or not os.path.isfile(output_path) or os.path.getsize(output_path) < 1000:
        raise RuntimeError("ffmpeg failed to embed cover into mp3")
    print("image set for to song cover")

    os.replace(output_path, os.path.join(folder_path, input_mp3))
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
