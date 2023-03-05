import telebot
import os
import re
from functions import download, file_list
from variables import welcome_message, directory, bot_api, database_channel, link_pattern

bot = telebot.TeleBot(bot_api)

@bot.message_handler(commands = ['start'])
def start_message(message):
    bot.send_message(message.chat.id, welcome_message)

@bot.message_handler(regexp = link_pattern)
def get_by_index(message):
    bot.send_message(message.chat.id, "right pattern link pattern")
    matches = re.findall(link_pattern, message.text)
    if matches:
        # Store all matches in a list:
        spotify_links = matches
        print("Spotify links found:", spotify_links)
        # download every link:
        for link in matches:
            download(link)
        # upload to telegram and delete from hard drive:
        for file in file_list(directory):    
            audio = open(directory + file, 'rb')
            bot.send_audio(message.chat.id, audio)
            audio = open(directory + file, 'rb')
            bot.send_audio(database_channel, audio)
#            os.remove(directory + file)
    else:
        print("No matches found. this line should not happen in normal behavior")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "this message doesn't match any pattern")

bot.infinity_polling()
