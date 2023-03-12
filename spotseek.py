#!/usr/bin/python3
import telebot
import os
import re
from functions import download, file_list, clear_files
from variables import welcome_message, info_message, directory, bot_api, database_channel, spotify_track_link_pattern, spotify_album_link_pattern, spotify_playlist_link_pattern, spotify_correct_link_pattern, db_csv_path, users_csv_path, db_time_column, db_sp_track_column, db_tl_audio_column, ucsv_user_id_column, ucsv_last_time_column, user_request_wait, bot_name, bot_username
from log import log, log_channel_id
from csv_functions import csv_read, db_csv_append, get_row_list_csv_search, get_row_index_csv_search, csv_sort, allow_user
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
    bot.send_message(message.chat.id, welcome_message, disable_web_page_preview=True)
    log(bot_name + " log:\n /start command sent")

@bot.message_handler(commands = ['info'])
def start_message(message):
    bot.send_message(message.chat.id, info_message, disable_web_page_preview=True)
    log(bot_name + " log:\n /info command sent")

@bot.message_handler(regexp = spotify_correct_link_pattern)
def get_by_index(message):
    bot.send_message(message.chat.id, "Ok, wait for me to process...")
    try:
        # make it one user at a time
        with lock:
            log(bot_name + " log:\n correct link pattern")
            if allow_user(message.chat.id):
                print("+ allow")
                bot.send_message(message.chat.id, "Starting to download...\nIt can be very fast or very long, be patient.")
                clear_files(directory)
                matches = get_track_ids(message.text)
                if matches:
                    # download every link:
                    for track_id in matches:
                        link = "https://open.spotify.com/track/" + track_id 
                        existed_row = get_row_list_csv_search(db_csv_path, db_sp_track_column, track_id)
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
                                audio_message = bot.send_audio(database_channel, audio, thumb=thumb_image, caption=bot_username)
                                # add file to database
                                db_csv_append(db_csv_path, track_id, audio_message.audio.file_id)
                                # second send to user:
                                bot.send_audio(message.chat.id, audio_message.audio.file_id, caption=bot_username)
                                # remove files from drive
                                clear_files(directory)
                    # finish message for user
                    bot.send_message(message.chat.id, "end")
                else:
                    log(bot_name + " log:\nNo matches found. this line should not happen in normal behavior becuase it is already checked with regex, if happens is a bug.")
            else:
                bot.send_message(message.chat.id, "you should wait " + str(user_request_wait) + " seconds between 2 requests")
                print("- allow")
    except Exception as e:
        print("An error occurred: ", e)
        log("An error occurred: " + e)
        bot.send_message(message.chat.id, "Sorry, my process wasn't successful :(")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "this message doesn't look like a supported spotify link.")
    log(bot_name + " log:\n wrong input pattern")

def main():
    bot.infinity_polling()

if __name__ == '__main__':
    main()
