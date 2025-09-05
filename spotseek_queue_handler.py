from queue_functions import *
import time

if __name__ == "__main__":
    try:
        # emperimental - remove old spotdl exe and download it again to see if affects limits
        setup_spotdl_executable()

        while True:
            time.sleep(5)  # delay for each complete loop of queue handler

            files = list_of_files_in_a_folder(received_links_folder_path)
            download_list = []
            log(f"🏁 #queue_handler_started\n📂 {len(files)} files in the folder.")
            # file names are user IDs
            for user_id in files:
                file_path = received_links_folder_path + "/" + user_id
                tracks = read_list_from_file(file_path)

                while tracks:
                    # extract the first track ID from the list
                    track_id = tracks.pop(0)
                    # check if it's a new track or exists in db now
                    telegram_audio_id = get_telegram_audio_id(track_id)
                    if telegram_audio_id is not None:
                        log(f"🤸‍♀️ track {track_id} exists in db now. skip.")
                        continue
                    else:
                        download_list.append(track_id)
                        break

                # if there are still some tracks left for this user
                # write the remaining tracks back to the file
                if tracks:
                    # todo: it's bug is that if meanwhile new tracks are appended to end of it, they will be overwritten
                    # todo: although it is not going to be very often
                    # write left items in tracks back to file
                    write_list_to_file(tracks, file_path)
                else:
                    # tracks list has become empty and we can delete related user file
                    os.remove(file_path)

                # download if there are enough tracks
                if len(download_list) >= simultaneous_downloads:
                    download_tracks(download_list)
                    # empty to download list again
                    download_list = []

            # after the loop:
            # if there are not enough tracks but still some left
            if download_list:
                # download the rest of them
                download_tracks(download_list)
                # empty to download list again
                download_list = []

    except Exception as e:
        log(bot_name + " log:\n🛑 An error in queue handler: " + str(e) + "\nfor user: " + str(user_id))