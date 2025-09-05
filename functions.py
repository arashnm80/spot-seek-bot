import subprocess
from variables import *
import requests
from log import *
import shutil

def get_single_mp3(directory):
    mp3_files = [f for f in os.listdir(directory) if f.endswith('.mp3')]
    if len(mp3_files) == 1:
        return mp3_files[0]
    elif len(mp3_files) == 0:
        raise FileNotFoundError("no .mp3 file was found.")
    else:
        raise RuntimeError("more than one .mp3 file was found.")

def clear_files(folder_path):
    for name in os.listdir(folder_path):
        if name == ".gitkeep":
            continue  # ne pas toucher à .gitkeep

        path = os.path.join(folder_path, name)
        try:
            if os.path.isfile(path) or os.path.islink(path):
                os.remove(path)
                print(f"Deleted file: {name}")
            elif os.path.isdir(path):
                shutil.rmtree(path)
                print(f"Deleted folder: {name}")
        except Exception as e:
            print(f"Error deleting {name}: {e}")

def check_membership(channel, user):
    # Send a request to the Telegram Bot API
    response = requests.get(f'https://api.telegram.org/bot{bot_api}/getChatMember', params={'chat_id': channel, 'user_id': user})
    
    # Parse the response
    data = response.json()
    if data['ok']:
        member_status = data['result']['status']
        if member_status == 'member' or member_status == 'creator' or member_status == 'administrator':
            print('The user is a member of the channel.')
            return True
        else:
            print('The user is not a member of the channel.')
            return False
    else:
        print('Failed to retrieve chat member information.')
        return False

def try_to_delete_message(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass # ignore errors if user has already deleted the message

# experimental - to see if has effect on spotdl rate limits
def delete_spotdl_cache():
    # Path to the directory
    directory = spotdl_cache_path

    # Check if the directory exists and remove it
    if os.path.exists(directory):
        shutil.rmtree(directory)
        print(f'{directory} has been removed.')
    else:
        print(f'{directory} does not exist.')

def delete_yt_dlp_cache():
    # Path to the directory
    directory = yt_dlp_cache_path

    # Check if the directory exists and remove it
    if os.path.exists(directory):
        shutil.rmtree(directory)
        print(f'{directory} has been removed.')
    else:
        print(f'{directory} does not exist.')

def setup_spotdl_executable():
    # Remove the existing spotdl file if it exists
    if os.path.exists("spotdl"):
        os.remove("spotdl")
        print("Old spotdl file removed.")
    
    # Define the URL for the latest version of spotdl
    url = spotdl_executable_link
    
    # Download spotdl using wget and name the file 'spotdl'
    download_command = ["wget", "-O", "spotdl", url]
    
    # Run the wget command to download spotdl
    subprocess.run(download_command, check=True)
    
    # Give the downloaded file executable permissions
    chmod_command = ["chmod", "+x", "spotdl"]
    
    # Run the chmod command to make the file executable
    subprocess.run(chmod_command, check=True)