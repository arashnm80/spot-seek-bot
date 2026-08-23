from my_imports import *
from spotify import get_track_image

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
        global current_proxy_index
        global queue_handler_sleep_timer
        log(f"sleep timer: {queue_handler_sleep_timer}")
        time.sleep(queue_handler_sleep_timer)  # small delay between batches for yt-dlp

        # Keep ~/.spotdl and yt-dlp caches. Wiping them forced a 5s secrets timeout
        # to code.thetadev.de on every batch and slowed matching.

        # remove files and folders in directory
        clear_files(directory)

        for track_id in track_ids_list[:]:  # copie de la liste
            # new method based on sqlite3 db
            telegram_audio_id = get_telegram_audio_id(track_id)

            # if item exists in db
            if telegram_audio_id is not None:
                log(f"track {track_id} exists in db now. skip.")
                queue_note("skipped_in_db", track_id=track_id)
                track_ids_list.remove(track_id)

        # if list became empty
        if not track_ids_list:
            log("all tracks already exist in db. skip.")
            return "allTracksExistInDb"

        log(f"current_proxy_index: {current_proxy_index}\n\ntracks to download:\n\n{"\n".join(track_ids_list)}")

        # Kill any existing spotdl processes before starting a new download
        try:
            subprocess.run(['pkill', '-9', '-f', 'spotdl'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log(f"Failed to kill existing spotdl processes: {e}")

        try:       
            print("start downloading tracks via spotdl")

            # experimental - pass spotify api key to spotdl
            # random spotify app from list to avoid rate limiting
            random.seed(time.time())
            spotify_app = random.choice(spotify_apps_list)
            spotify_client_id = spotify_app[0]
            spotify_client_secret = spotify_app[1]

            command = [
                       "proxychains4", "-f", proxychains4_config_file,
                       spotdl_bin,
                    #    "--client-id", spotify_client_id, "--client-secret", spotify_client_secret,
                       "--audio", spotdl_audio_provider,
                       "--lyrics",
                       "--skip-album-art",
                       "--bitrate", "320k",
                    #    "--yt-dlp-args", "--config-location ../yt-dlp.conf",
                    #    no --yt-dlp-args --proxy (double tunnel) and no -f 140; Deno on PATH → bestaudio/251
                       "--output", "{track-id}/",
                       "download"
                       ]
            
            for track_id in track_ids_list:
                command.append(f"https://open.spotify.com/track/{track_id}")
            # download in a subprocess with a timeout (does it in ouput folder)
            print("download command:\n\n", command) # debug
            subprocess.run(
                command,
                cwd=directory,
                env=get_spotdl_download_env(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=300,
            )
        except Exception as e:
            log(bot_name + " error in spotdl download")
            queue_note("spotdl_fail", n=len(track_ids_list), detail="spotdl exception")
            return "errorInSpotdlDownload"

        at_least_one_track_downloaded = False # sometimes jumps to next pack without downloading anything and giving any error

        try:
            print("start downloading cover images")
            # Listing folders in the output directory - each folder name is track_id of one song
            folders = [name for name in os.listdir(directory) if os.path.isdir(os.path.join(directory, name))]
            print("folders (which are track ids):", folders)
            # S3 disabled: bucket deleted (cost). Restore this client + put_object if needed.
            # s3_client = boto3.client(
            #     's3',
            #     endpoint_url=S3_ENDPOINT,
            #     aws_access_key_id=S3_ACCESS_KEY,
            #     aws_secret_access_key=S3_SECRET_KEY
            # )
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
                try:
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
                        queue_note("no_mp3", track_id=track_id, detail="no mp3")
                        continue
                    log(f"current_proxy_index: {current_proxy_index}\n\n🔵 there is a downloaded mp3 file:\n{mp3_file}")
                    # change cover image
                    change_cover_image(mp3_file, "cover.jpg", track_folder_path)
                    # check file size because of telegram 50MB limit
                    audio_path = os.path.join(track_folder_path, mp3_file)
                    audio = open(audio_path, 'rb')
                    file_size = os.fstat(audio.fileno()).st_size
                    if file_size > 50_000_000:
                        log(bot_name + " log:\n🛑 too big mp3 file error")
                        queue_note("too_big", track_id=track_id, detail="too big")
                        audio.close()
                        continue
                    # get track metadata to be shown in telegram
                    track_duration = get_track_duration(audio_path)
                    track_artist = get_artist_name_from_track(audio_path)
                    track_title = get_track_title(audio_path)
                    thumb_image = open(track_folder_path + "cover_low.jpg", 'rb')
                    # send audio to database_channel:
                    audio_message = bot.send_audio(SP11_CHANNEL_ID, audio, thumb=thumb_image, caption=track_id, duration=track_duration, performer=track_artist, title=track_title)
                    # add file to database - new method based on sqlite3 db
                    # add_or_update_track_info(track_id, audio_message.audio.file_id) # before new db functions system of backup
                    add_or_update_track_info(track_id, audio_message.audio.file_id, SP11_CHANNEL_ID, audio_message.message_id, download_method=spotdl_audio_provider) # after new db functions system of backup
                    # S3 disabled (bucket deleted). Was: put_object music/{track_id}.mp3 then update_s3_status(track_id, 1)
                    # try:
                    #     s3_key = f"{track_id}.mp3"
                    #     with open(audio_path, 'rb') as audio_file:
                    #         s3_client.put_object(
                    #             Bucket=S3_BUCKET_NAME,
                    #             Key=s3_key,
                    #             Body=audio_file,
                    #             ContentType='audio/mpeg'
                    #         )
                    #     update_s3_status(track_id, 1)
                    # except Exception as e:
                    #     log(bot_name + f" log:\nS3 upload failed for {track_id} (kept in db/telegram):\n{e}")
                    audio.close()
                    thumb_image.close()
                    at_least_one_track_downloaded = True
                    queue_note("ok", track_id=track_id)
                except Exception as e:
                    log(bot_name + f"\nerror processing track {track_id}:\n" + str(e))
                    queue_note("error", track_id=track_id, detail=str(e)[:80])
                    continue
            # spotdl created no folder → same as no mp3
            folder_set = set(folders)
            for track_id in track_ids_list:
                if track_id not in folder_set:
                    queue_note("no_mp3", track_id=track_id, detail="no folder")
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