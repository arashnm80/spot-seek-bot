from my_imports import *
from db_functions import *
from spotify import get_track_image
from functions import *
import random

def list_of_files_in_a_folder(folder_path):
    try:
        file_names = os.listdir(folder_path)
        # Filter out '.gitkeep'
        file_names = [name for name in file_names if name != '.gitkeep']
        # Sort the list of file names by creation time
        file_names.sort(key=lambda filename: os.path.getctime(os.path.join(folder_path, filename)))
        return file_names
    except FileNotFoundError:
        print(f"Folder {folder_path} not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

# One item per line, add without duplicates
def append_list_to_file(my_list, file_path):
    # Lire les lignes existantes (sans les sauts de ligne)
    try:
        with open(file_path, 'r') as file:
            existing_items = set(line.strip() for line in file)
    except FileNotFoundError:
        existing_items = set()

    # Ouvrir en mode ajout uniquement les éléments non existants
    with open(file_path, 'a') as file:
        for item in my_list:
            if item not in existing_items:
                file.write(item + '\n')

# write list to file, overwriting the file if it exists
def write_list_to_file(my_list, file_path):
    # creates it if it doesn't exist
    with open(file_path, 'w') as file:
        for item in my_list:
            file.write(item + '\n')

# one item per line
def read_list_from_file(file_path):
    # Initialize an empty list to store the lines
    lines = []
    # Open the file in read mode
    with open(file_path, 'r') as file:
        for line in file:
            # Use rstrip() to remove the newline character
            line = line.rstrip()
            lines.append(line)
    return lines


def download_tracks(track_ids_list):
    try:
        global queue_handler_sleep_timer
        log(f"sleep timer: {queue_handler_sleep_timer}")
        time.sleep(queue_handler_sleep_timer)  # dynamic delay for yt-dlp

        global current_proxy_index
    
        # # fixme
        # # experimental - to see if has effect on spotdl rate limits - debug
        # delete_spotdl_cache()
        # # experimental again - yt-dlp cache
        # delete_yt_dlp_cache()

        # remove files and folders in directory
        clear_files(directory)

        for track_id in track_ids_list[:]:  # copie de la liste
            # new method based on sqlite3 db
            telegram_audio_id = get_telegram_audio_id(track_id)

            # if item exists in db
            if telegram_audio_id is not None:
                log(f"track {track_id} exists in db now. skip.")
                track_ids_list.remove(track_id)

        # if list became empty
        if not track_ids_list:
            log("all tracks already exist in db. skip.")
            return "allTracksExistInDb"




        # debug
        current_proxy = socks_proxies[current_proxy_index]

        log(f"current_proxy_index: {current_proxy_index}\n\ntracks to download:\n\n{"\n".join(track_ids_list)}")

        # Kill any existing spotdl processes before starting a new download
        try:
            subprocess.run(['pkill', '-9', '-f', 'spotdl'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log(f"Failed to kill existing spotdl processes: {e}")

        try:       
            print("start downloading tracks via spotdl")
            # download with proxychains and warp
            # command = ['proxychains4', '-f', proxychains4_config_file, '../spotdl', "--bitrate", "320k", "--output", "{track-id}/", "download"]
            
            # experimental - pass spotify api key to spotdl
            # random spotify app from list to avoid rate limiting
            random.seed(time.time())
            spotify_app = random.choice(spotify_apps_list)
            print(spotify_app) # debug
            spotify_client_id = spotify_app[0]
            spotify_client_secret = spotify_app[1]

            command = [
                    #    "proxychains4", "-f", proxychains4_config_file,
                       "../spotdl",
                    #    "--client-id", spotify_client_id, "--client-secret", spotify_client_secret,
                       "--bitrate", "320k",
                    #    "--yt-dlp-args", "--config-location ../yt-dlp.conf",
                       "--yt-dlp-args", f"--proxy {current_proxy}", #fixme credentials
                       "--output", "{track-id}/",
                       "download"
                       ]
            
            for track_id in track_ids_list:
                command.append(f"https://open.spotify.com/track/{track_id}")
            
            print("download command:", " ".join(command)) # debug
            # download in a subprocess with a timeout (does it in ouput folder)
            subprocess.run(command, cwd=directory, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
        except Exception as e:
            log(bot_name + " error in spotdl download")
            return "errorInSpotdlDownload"

        at_least_one_track_downloaded = False # sometimes jumps to next pack without downloading anything and giving any error

        try:
            print("start downloading cover images")
            # Listing folders in the output directory - each folder name is track_id of one song
            folders = [name for name in os.listdir(directory) if os.path.isdir(os.path.join(directory, name))]
            print("folders (which are track ids):", folders)
            for track_id in folders:
                # check if folder name is in the track_ids_list
                # opposite of that should never happen
                # but look likes it happens rarely - maybe is a problem from spotdl side
                if track_id not in track_ids_list:
                    log(f"folder {track_id} is wrong and doesn't exist in track_ids_list")
                    return "unmatchedFolderWithTrackIdsList"
                print("track_id based on folder:", track_id)
                track_folder_path = f"{directory}{track_id}/"
                print("track folder path:", track_folder_path)
                # download cover image
                image_url = get_track_image(track_id)
                print("downloading image from url:", image_url)
                # todo: make this subprocess secure later by turning shell False and using list
                subprocess.run(f"wget -O cover.jpg -o /dev/null \"{image_url}\"", shell=True, cwd=track_folder_path, timeout=300)
                # get mp3 file name from folder
                try:
                    mp3_file = get_single_mp3(track_folder_path)
                except Exception as e:
                    log(bot_name + f" log:\n\ncurrent_proxy_index: {current_proxy_index}\nsleep_timer: {queue_handler_sleep_timer}\n\n🛑 error in get_single_mp3() for track:\n" + track_id +"\n\nerror:\n" + str(e))
                    continue
                log(f"current_proxy_index: {current_proxy_index}\n\n🔵 there is a downloaded mp3 file:\n{mp3_file}")
                # change cover image
                change_cover_image(mp3_file, "cover.jpg", track_folder_path)
                # check file size because of telegram 50MB limit
                audio = open(track_folder_path + mp3_file, 'rb')
                file_size = os.fstat(audio.fileno()).st_size
                if file_size > 50_000_000:
                    log(bot_name + " log:\n🛑 too big mp3 file error")
                    continue
                # get track metadata to be shown in telegram
                track_duration = get_track_duration(track_folder_path + mp3_file)
                track_artist = get_artist_name_from_track(track_folder_path + mp3_file)
                track_title = get_track_title(track_folder_path + mp3_file)
                thumb_image = open(track_folder_path + "cover_low.jpg", 'rb')
                # send audio to database_channel:
                audio_message = bot.send_audio(database_channel, audio, thumb=thumb_image, caption=bot_username, duration=track_duration, performer=track_artist, title=track_title)
                # add file to database - new method based on sqlite3 db
                add_or_update_track_info(track_id, audio_message.audio.file_id)
                
                at_least_one_track_downloaded = True
        except Exception as e:
            log(bot_name + "\nerror in processing downloaded tracks:\n" + str(e))
            return "errorInProcessingDownloadedTracks"

        # if at_least_one_track_downloaded and queue_handler_sleep_timer > 3:
        #     queue_handler_sleep_timer -= 0 # 1
        # elif (not at_least_one_track_downloaded) and queue_handler_sleep_timer <= 595:
        #     queue_handler_sleep_timer += 0 # 5
        if not at_least_one_track_downloaded:
            current_proxy_index = (current_proxy_index + 1) % len(socks_proxies)
            log(f"current proxy changed to index: {current_proxy_index}")


        return "successfulDownload✅"

    except Exception as e:
        log(bot_name + " log:\n🛑 An error in download_tracks():\n" + str(e))
        return "downloadTracksError"