from queue_functions import *

if __name__ == "__main__":
    try:
        log("queue handler started")

        # initialize bot
        bot = telebot.TeleBot(bot_api)

        # if any user left to process, queue_handler_should_run will be set to True again
        queue_handler_should_run = False

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
                    track_handling_result = handle_track_for_user(first_track, user_id)

                    # continue working for the same user a long as
                    # tracks are just being forwarded
                    # limit this to a number like 20 or 50
                    if track_handling_result != "forwarded" or consecutive_download >= 20:
                        break
                    else:
                        # continue handling for the same user but lower the speed due to this problem:
                        # (https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this)
                        time.sleep(0.01) # I increase this if telegram still limits me

                if tracks:
                    # write left items in tracks back to file
                    write_list_to_file(tracks, file_path)
                    # queue handler job has not ended yet
                    queue_handler_should_run = True
                else:
                    # tracks has become empty and we can delete related file
                    os.remove(file_path)
                    # end message to user
                    bot.send_message(user_id, end_message, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        log(bot_name + " log:\nAn error in queue handler: " + str(e) + "\nfor user: " + str(user_id))

    # queue handler should run itself again after a few second
    # the main reason for using this method was that this queue handler threads get bigger and bigger
    # until they flood the system
    # I couldn't find a proper solution so far, so I decided to close this file
    # and re-run it by itself after each cycle
    if queue_handler_should_run:
        sleep_time = 2 # run again after a short time
    else:
        sleep_time = 20 # no tracks left to download, wait more
    
    try:
        command = f"sleep {sleep_time} && nohup python3 ./spotseek_queue_handler.py &"
        subprocess.Popen(command, shell=True, close_fds=True)
    except subprocess.CalledProcessError as e:
        log(f"error in re-running queue handler from itself: {e}")