import subprocess
import os

def download(link):
    print("start downloading: " + link)
    command = ['../spotdl', "--bitrate", "320k", link]
    subprocess.run(command, cwd="./output")
    print("end downloading: " + link)

def file_list(directory):
    file_list = []
    for file in os.listdir(directory):
        if file.endswith(".mp3"):
            file_list.append(file)
    return file_list
