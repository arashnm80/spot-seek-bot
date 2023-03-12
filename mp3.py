import subprocess
from variables import directory

def change_cover_image(input_mp3, input_image):
    output_file = 'output.mp3'
    low_size_image = "cover_low.jpg"

    # reduce image size to 320 * 320
    image_size_command = f"ffmpeg -i \"{input_image}\" -vf \"scale=320:-1\" -loglevel quiet \"{low_size_image}\""
    subprocess.run(image_size_command, shell=True, cwd=directory)
    
    # add image cover to song
    add_cover_command = f"ffmpeg -i \"{input_mp3}\" -i \"{low_size_image}\" -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title='Album cover' -metadata:s:v comment='Cover (front)' -loglevel quiet \"{output_file}\""
    subprocess.run(add_cover_command, shell=True, cwd=directory)

    # delete old mp3 and rename new one to it
    subprocess.run(f"rm \"{input_mp3}\"", shell=True, cwd=directory)
    subprocess.run(f"mv \"{output_file}\" \"{input_mp3}\"", shell=True, cwd=directory)

