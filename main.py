import telebot
import os
import re
from functions import download, file_list
from variables import welcome_message, directory, bot_api, database_channel, spotify_song_link_pattern
from log import log, log_channel_id
from database import csv_read, csv_append, csv_search, csv_sort
from spotify import valid_song_link, get_all_song_links, get_song_id

bot = telebot.TeleBot(bot_api)

@bot.message_handler(commands = ['start'])
def start_message(message):
    bot.send_message(message.chat.id, welcome_message)
    log("nm80_music_bot started")

@bot.message_handler(commands = ['test'])
def start_message(message):
    log("nm80_music_bot test command sent")
#    bot.send_audio(message.chat.id, "CQACAgQAAx0Eb86Z0AADDWQE4hXtYcotomw3GYXJJjV27ZqAAAIwDwACT3AoUI_7sKDsPte7LgQ")

@bot.message_handler(regexp = spotify_song_link_pattern)
def get_by_index(message):
    bot.send_message(message.chat.id, "right spotify_song_link_pattern")
    matches = get_all_song_links(message.text)
    if matches:
        # download every link:
        for link in matches:
            download(link)
        # upload to telegram and delete from hard drive:
        for file in file_list(directory):
            # first send to database_channel:
            audio = open(directory + file, 'rb')
            audio_message = bot.send_audio(database_channel, audio)
            # second send to user:
            bot.send_audio(message.chat.id, audio_message.audio.file_id)
#            os.remove(directory + file)
    else:
        log("No matches found. this line should not happen in normal behavior")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "this message doesn't match any pattern")

bot.infinity_polling()
