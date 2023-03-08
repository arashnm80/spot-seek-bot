import telebot
import os
import re
from functions import download, file_list
from variables import welcome_message, directory, bot_api, database_channel, spotify_track_link_pattern, spotify_album_link_pattern, spotify_playlist_link_pattern, spotify_correct_link_pattern
from log import log, log_channel_id
from database import csv_read, csv_append, csv_search, csv_sort
from spotify import get_link_type, get_track_ids

bot = telebot.TeleBot(bot_api)

@bot.message_handler(commands = ['start'])
def start_message(message):
    bot.send_message(message.chat.id, welcome_message)
    log("nm80_music_bot log:\n /start command sent")

@bot.message_handler(commands = ['test'])
def start_message(message):
    log("nm80_music_bot log:\n /test command sent")

@bot.message_handler(regexp = spotify_correct_link_pattern)
def get_by_index(message):
    log("nm80_music_bot log:\n correct link pattern")
    bot.send_message(message.chat.id, "correct link pattern")
    matches = get_track_ids(message.text)
    if matches:
        # download every link:
        for track_id in matches:
            link = "https://open.spotify.com/track/" + track_id 
            existed_row = csv_search(track_id)
            if existed_row:
                telegram_audio_id = existed_row[2]
                bot.send_audio(message.chat.id, telegram_audio_id)
            else:
                download(link)
                # upload to telegram and delete from hard drive:
                for file in file_list(directory): # we send every possible file in directory to bypass searching for file name
                    # first send to database_channel:
                    audio = open(directory + file, 'rb')
                    audio_message = bot.send_audio(database_channel, audio)
                    # add file to database
                    csv_append(track_id, audio_message.audio.file_id)
                    # second send to user:
                    bot.send_audio(message.chat.id, audio_message.audio.file_id)
                    # remove file from drive
                    os.remove(directory + file)
    else:
        log("No matches found. this line should not happen in normal behavior becuase it is already checked with regex, if happens is a bug.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "this message doesn't match any pattern")
    log("nm80_music_bot log:\n wrong input pattern")

bot.infinity_polling()
