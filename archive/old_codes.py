# Check the membership status and stop continuing if user is not a member
'''
is_member = check_membership(promote_channel_username, message.chat.id)
if is_member:
    log(bot_name + " log:\nuser " + str(message.chat.id) + " is member of channel.")
else:
    log(bot_name + " log:\nuser " + str(message.chat.id) + " is not member of channel.")
    
    # Send message with join button to user
    keyboard = types.InlineKeyboardMarkup()
    channel_button = types.InlineKeyboardButton(text='Join', url=promote_channel_link)
    keyboard.add(channel_button)
    bot.send_message(message.chat.id,
                     not_subscribed_to_channel_message,
                     parse_mode="Markdown",
                     disable_web_page_preview=True,
                     reply_markup=keyboard)

    return # stops going any further
'''

# check last time the user used this bot and decide to let him use it or not
'''
if not allow_user(message.chat.id):
    bot.send_message(message.chat.id, "you should wait " + str(user_request_wait) + " seconds between requests")
    log(bot_name + " log:\n⏰user " + str(message.chat.id) + " isn't allowed to use the bot")
    return
'''

# old body of spotseek.py
'''
at_least_one_track_downloaded = False
download every link:
for track_id in matches:
    time.sleep(0.5) # wait a little to alleviate telegram bot limit
    # (https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this)
    link = "https://open.spotify.com/track/" + track_id 
    track_id_first_letter = track_id[0]
    # instead of old method we use db file based on first letter of track_id + csv extension
    db_csv_path = db_by_letter_folder_path + "/" + track_id_first_letter + ".csv"
    existed_row = get_row_list_csv_search(db_csv_path, db_sp_track_column, track_id)
    if existed_row:
        telegram_audio_id = existed_row[db_tl_audio_column]
        bot.send_audio(message.chat.id, telegram_audio_id, caption=bot_username)
        at_least_one_track_downloaded = True
    else:
        download(link)
        # upload to telegram and delete from hard drive:
        # we send every possible file in directory to bypass searching for file name
        for file in file_list(directory):
            change_cover_image(file, "cover.jpg")
            audio = open(directory + file, 'rb')
            # check file size because of telegram 50MB limit
            file_size = os.fstat(audio.fileno()).st_size

            if file_size > 50_000_000:
                too_large_file_error = "Sorry, size of \"{f}\" is more than 50MB and can't be sent".format(f = file)
                bot.send_message(message.chat.id, too_large_file_error)
            else:
                # get track metadata to be shown in telegram
                track_duration = get_track_duration(directory + file)
                track_artist = get_artist_name_from_track(directory + file)
                track_title = get_track_title(directory + file)
                thumb_image = open(directory + "cover_low.jpg", 'rb')
                # first send to database_channel:
                audio_message = bot.send_audio(database_channel, audio, thumb=thumb_image, caption=bot_username, duration=track_duration, performer=track_artist, title=track_title)
                # add file to database
                db_csv_append(db_csv_path, track_id, audio_message.audio.file_id)
                # second send to user:
                bot.send_audio(message.chat.id, audio_message.audio.file_id, caption=bot_username)
                # user should get success message in the end
                at_least_one_track_downloaded = True
            
            # remove files from drive
            clear_files(directory)


# show ending message for user, success or failure
if at_least_one_track_downloaded:
    bot.send_message(message.chat.id, end_message, parse_mode="Markdown", disable_web_page_preview=True)
else:
    bot.send_message(message.chat.id, unsuccessful_process_message, parse_mode="Markdown")

else:
    log(bot_name + abnormal_behavior_message)
    bot.send_message(message.chat.id, unsuccessful_process_message, parse_mode="Markdown")
'''

# status.txt as a flag for checking if queue handler is running or not
'''
# Function to write 0 or 1 to the file. 1 means queue_handler is running and 0 means it's stopped
def write_queue_handler_status(number):
    if number not in (0, 1):
        raise ValueError("Number must be either 0 or 1")
    with open("status.txt", "w") as file:
        file.write(str(number))

# Function to read the number from the file. 1 means queue_handler is running and 0 means it's stopped
def read_queue_handler_status():
    with open("status.txt", "r") as file:
        content = file.read()
        if content.strip() not in ('0', '1'):
            raise ValueError("File contains an invalid value")
        return int(content)
'''

# run queue handler from spotseek.py
'''
# run queue handler again if it has stopped
if read_queue_handler_status() == 0:
    # Run the spotseek_queue_handler.py in a separate process
    try:
        # subprocess.run(["python3", "./spotseek_queue_handler.py"], check=True)
        subprocess.Popen(["python3", "./spotseek_queue_handler.py"])
    except subprocess.CalledProcessError as e:
        print(f"Error running the spotseek_queue_handler from spotseek.py script: {e}")
'''

# create a lock for a piece of code to prevent 2 instances running at the same time
'''
# Create a mutex lock
lock = threading.Lock()

with lock:
    pass # do sth here
'''