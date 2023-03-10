import subprocess
from variables import directory

def change_cover_image(input_mp3, input_image):
    output_file = 'output.mp3'
    
    # add image cover to song
    ffmpeg_command = f"ffmpeg -i \"{input_mp3}\" -i \"{input_image}\" -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title='Album cover' -metadata:s:v comment='Cover (front)' \"{output_file}\""
    subprocess.run(ffmpeg_command, shell=True, cwd=directory)

    # delete old file and rename new one to it
    subprocess.run(f"rm \"{input_mp3}\"", shell=True, cwd=directory)
    subprocess.run(f"mv \"{output_file}\" \"{input_mp3}\"", shell=True, cwd=directory)
