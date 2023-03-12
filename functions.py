import subprocess
import os
from variables import directory
from spotify import get_track_image

def download(track_link):
    # download track
    print("start downloading: " + track_link)
    command = ['../spotdl', "--bitrate", "320k", track_link]
    subprocess.run(command, cwd=directory, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("end downloading: " + track_link)

    # download cover image
    image_url = get_track_image(track_link)
    print("start downloading cover image: " + image_url)
    subprocess.run(f"wget -O cover.jpg -o /dev/null \"{image_url}\"", shell=True, cwd=directory)
    print("end downloading cover image: " + image_url)

def file_list(directory):
    file_list = []
    for file in os.listdir(directory):
        if file.endswith(".mp3"):
            file_list.append(file)
    return file_list

def clear_files(folder_path):
    directory = folder_path
    # note: there is a .gitkeep file in output folder

    for filename in os.listdir(directory):
        if filename != ".gitkeep":
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Deleted {filename}")
            except Exception as e:
                print(f"Error deleting {filename}: {e}")

