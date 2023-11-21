from my_imports import *

def list_of_files_in_a_folder(folder_path):
    try:
        file_names = os.listdir(folder_path)
        # Sort the list of file names by creation time
        file_names.sort(key=lambda filename: os.path.getctime(os.path.join(folder_path, filename)))
        return file_names
    except FileNotFoundError:
        print(f"Folder {folder_path} not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

# one item per line
def write_list_to_file(my_list, file_path):
    # Open the file in write mode
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

def handle_track_for_user(track_id, user_id):
    try:
        # create bot instance
        bot = telebot.TeleBot(bot_api)

        # remove junk files from drive
        clear_files(directory)

        # instead of old method we use db file based on first letter of track_id + csv extension
        track_id_first_letter = track_id[0]
        db_csv_path = db_by_letter_folder_path + "/" + track_id_first_letter + ".csv"

        # get row of item in database file or return false if doesn't exist
        existed_row = get_row_list_csv_search(db_csv_path, db_sp_track_column, track_id)

        # if item exists in 
        if existed_row:
            telegram_audio_id = existed_row[db_tl_audio_column]
            bot.send_audio(user_id, telegram_audio_id, caption=bot_username)
            return "forwarded"

        # file doesn't exist in database and should be downloaded
        link = "https://open.spotify.com/track/" + track_id
        download(link)
        # upload to telegram and delete from hard drive:
        # we send every possible file in directory to bypass searching for file name. but we actually know that there is only one file
        for file in file_list(directory):
            change_cover_image(file, "cover.jpg")
            audio = open(directory + file, 'rb')
            # check file size because of telegram 50MB limit
            file_size = os.fstat(audio.fileno()).st_size

            if file_size > 50_000_000:
                too_large_file_error = "Sorry, size of \"{f}\" is more than 50MB and can't be sent".format(f = file)
                bot.send_message(user_id, too_large_file_error)
                return "largeMp3Error"

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
            bot.send_audio(user_id, audio_message.audio.file_id, caption=bot_username)
            # remove files from drive
            clear_files(directory)
            return "downloaded"
        return "noFileSentError"
    except Exception as e:
        log(bot_name + " log:\nAn error in track_handling_result for user " + user_id + " and track " + track_id + ":\n" + str(e))
        return "bad error"