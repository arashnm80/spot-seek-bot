from queue_functions import *

if __name__ == "__main__":
    try:
        log("🏁 #queue_handler_started")

        # emperimental - remove old spotdl exe and download it again to see if affects limits
        setup_spotdl_executable()

        # initialize bot
        bot = telebot.TeleBot(bot_api)

        for folder in ["track", "album", "playlist"]:
            folder_path = received_links_folder_path + "/" + folder
            files = list_of_files_in_a_folder(folder_path)
            # file names are user IDs
            for user_id in files:
                file_path = folder_path + "/" + user_id
                tracks = read_list_from_file(file_path)

                consecutive_download = 0
                # as long as items are left in tracks list
                while tracks:
                    # pop first item of the tracks to a variable
                    first_track = tracks.pop(0)

                    # now we handle the first track that we extracted
                    consecutive_download += 1
                    track_handling_result = handle_track_for_user(first_track, user_id, folder)

                    # continue working for the same user a long as
                    # tracks are just being forwarded
                    # limit this to a number like 20 or 50
                    if ((track_handling_result != "forwarded") and (track_handling_result != "skipped")) or (consecutive_download >= queue_handler_max_forwards_in_a_row):
                        break
                    else:
                        # continue handling for the same user but lower the speed due to this problem:
                        # (https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this)
                        time.sleep(0.001) # I increase this if telegram still limits me

                # what to do if user has blocked me or deactivated
                if track_handling_result == "userBlockedMe" or track_handling_result == "deactivatedUser":
                    os.remove(file_path)
                    log(bot_name + " log:\n🗑 deleting user " + user_id + " tracks cause they blocked me or deactivated.")
                    continue # abort rest of code for current user and jump to next user

                if tracks:
                    # write left items in tracks back to file
                    write_list_to_file(tracks, file_path)
                else:
                    # tracks has become empty and we can delete related file
                    os.remove(file_path)
                    # end message to user
                    bot.send_message(user_id, end_message, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        log(bot_name + " log:\n🛑 An error in queue handler: " + str(e) + "\nfor user: " + str(user_id))

    # queue handler should run itself again after a few second
    # the main reason for using this method was that this queue handler threads get bigger and bigger
    # until they flood the system
    # I couldn't find a proper solution so far, so I decided to close this file
    # and re-run it by itself after each cycle  
    try:
        sleep_time = 2
        command = f"sleep {sleep_time} && nohup python3 ./spotseek_queue_handler.py > /dev/null 2>&1 &"
        subprocess.Popen(command, shell=True, close_fds=True)
    except subprocess.CalledProcessError as e:
        log(f"🛑 error in re-running queue handler from itself: {e}")