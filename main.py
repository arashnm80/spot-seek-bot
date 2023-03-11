import telebot
import os
import re
from functions import download, file_list, clear_files
from variables import welcome_message, directory, bot_api, database_channel, spotify_track_link_pattern, spotify_album_link_pattern, spotify_playlist_link_pattern, spotify_correct_link_pattern, db_csv_path, users_csv_path, db_time_column, db_sp_track_column, db_tl_audio_column, ucsv_user_id_column, ucsv_last_time_column
from log import log, log_channel_id
from csv_functions import csv_read, csv_append, csv_search, csv_sort
from spotify import get_link_type, get_track_ids
from mp3 import change_cover_image
import threading # to use lock

# initialize and get ready
bot = telebot.TeleBot(bot_api)
clear_files(directory)

# Create a mutex lock
lock = threading.Lock()

@bot.message_handler(commands = ['start'])
def start_message(message):
    bot.send_message(message.chat.id, welcome_message)
    log("nm80_music_bot log:\n /start command sent")

@bot.message_handler(commands = ['test'])
def start_message(message):
    log("nm80_music_bot log:\n /test command sent")

@bot.message_handler(regexp = spotify_correct_link_pattern)
def get_by_index(message):
    bot.send_message(message.chat.id, "Ok, wait for me to process...")
    # make it one user at a time
    with lock:
        log("nm80_music_bot log:\n correct link pattern")
        bot.send_message(message.chat.id, "starting to download...")
        clear_files(directory)
        matches = get_track_ids(message.text)
        if matches:
            # download every link:
            for track_id in matches:
                link = "https://open.spotify.com/track/" + track_id 
                existed_row = csv_search(db_csv_path, db_sp_track_column, track_id)
                if existed_row:
                    telegram_audio_id = existed_row[db_tl_audio_column]
                    bot.send_audio(message.chat.id, telegram_audio_id)
                else:
                    download(link)
                    # upload to telegram and delete from hard drive:
                    for file in file_list(directory): # we send every possible file in directory to bypass searching for file name
                        change_cover_image(file, "cover.jpg")
                        
                        # first send to database_channel:
                        audio = open(directory + file, 'rb')
                        thumb_image = open(directory + "cover_low.jpg", 'rb')
                        audio_message = bot.send_audio(database_channel, audio, thumb=thumb_image, caption="my channel2")

                        # add file to database
                        csv_append(db_csv_path, track_id, audio_message.audio.file_id)

                        # second send to user:
                        bot.send_audio(message.chat.id, audio_message.audio.file_id, caption="my bot2")

                        # remove file from drive
                        # os.remove(directory + file) # my old method
                        clear_files(directory) # my new method
        else:
            log("No matches found. this line should not happen in normal behavior becuase it is already checked with regex, if happens is a bug.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "this message doesn't match any pattern")
    log("nm80_music_bot log:\n wrong input pattern")

bot.infinity_polling()
