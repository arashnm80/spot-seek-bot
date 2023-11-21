#!/usr/bin/python3

from queue_functions import *
from my_imports import *

# initialize and get ready
bot = telebot.TeleBot(bot_api)

# defined commands
@bot.message_handler(commands = ['start'])
def start_message_handler(message):
    bot.send_message(message.chat.id, welcome_message, disable_web_page_preview=True)
    log(bot_name + " log:\n/start command sent from user: " + str(message.chat.id))

@bot.message_handler(commands = ['info'])
def info_message_handler(message):
    bot.send_message(message.chat.id, info_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n/info command sent from user: " + str(message.chat.id))

# wrong defined patterns such as deezer, youtube, ...
@bot.message_handler(regexp = deezer_link_pattern)
def deezer_link_handler(message):
    bot.send_message(message.chat.id, deezer_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\ndeezer link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = soundcloud_link_pattern)
def soundcloud_link_handler(message):
    bot.send_message(message.chat.id, soundcloud_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\nsoundcloud link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = youtube_link_pattern)
def youtube_link_handler(message):
    bot.send_message(message.chat.id, youtube_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\nyoutube link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = spotify_episode_link_pattern)
def spotify_episode_link_handler(message):
    bot.send_message(message.chat.id, spotify_episode_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\nepisode link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = spotify_artist_link_pattern)
def spotify_artist_link_handler(message):
    bot.send_message(message.chat.id, spotify_artist_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\nartist link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = spotify_user_link_pattern)
def spotify_user_link_handler(message):
    bot.send_message(message.chat.id, spotify_user_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\nuser link sent from user: " + str(message.chat.id))


# correct pattern
@bot.message_handler(regexp = spotify_correct_link_pattern)
def handle_correct_spotify_link(message):
    guide_message_1 = bot.send_message(message.chat.id, "Ok, be patient and wait...")
    log(bot_name + " log:\ncorrect link pattern from user: " + str(message.chat.id) + " with contents of:\n" + message.text)
    try:
        # Check the membership status and stop continuing if user is not a member
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

            try_to_delete_message(message.chat.id, guide_message_1.message_id)
            return

        valid_spotify_links_in_user_text = get_valid_spotify_links(message.text)

        # if user sends multiple links combined with normal text we only extract and
        # analyze first one so the bot won't be spammed
        first_link = valid_spotify_links_in_user_text[0]

        # if the link is shortened convert "spotify.link" to "open.spotify.com"
        if get_link_type(first_link) == "shortened":
            log(bot_name + " log:\nshortened link sent from user: " + str(message.chat.id))
            first_link = get_redirect_link(first_link)
            
        link_type = get_link_type(first_link)
        if link_type not in ["track", "album", "playlist"]:
            try_to_delete_message(message.chat.id, guide_message_1.message_id)
            bot.send_message(message.chat.id, "Looks like this link is wrong, expired or not supported. Try another.")
            log(bot_name + " log:\nerror in handling short link.")
            return
        
        matches = get_track_ids(first_link)
        
        # more than 1000 tracks
        if len(matches) > 1000:
            try_to_delete_message(message.chat.id, guide_message_1.message_id)
            bot.send_message(message.chat.id, more_than_1000_tracks_message)
            log(bot_name + " log:\nPlaylist more than 1000 tracks from user: " + str(message.chat.id))
            return

        # no tracks
        if not matches:
            try_to_delete_message(message.chat.id, guide_message_1.message_id)
            bot.send_message(message.chat.id, "sorry I couldn't extract tracks from link.")
            log(bot_name + " log:\nZero tracks error from user: " + str(message.chat.id))
            return

        # check if user already has sth for download in queue
        for folder in ["track", "album", "playlist"]:
            folder_path = received_links_folder_path + "/" + folder
            files = list_of_files_in_a_folder(folder_path)
            if str(message.chat.id) in files:
                try_to_delete_message(message.chat.id, guide_message_1.message_id)
                bot.send_message(message.chat.id, sth_to_download_message, parse_mode="Markdown", disable_web_page_preview=True)
                log(bot_name + " log:\nalready sth to download\nuser: " + str(message.chat.id))
                return

        # everything is fine. add user tracks to queue
        write_list_to_file(matches, received_links_folder_path + "/" + link_type + "/" + str(message.chat.id))

    except Exception as e:
        try_to_delete_message(message.chat.id, guide_message_1.message_id)
        bot.send_message(message.chat.id, unsuccessful_process_message, parse_mode="Markdown")
        log(bot_name + " log:\nA general error occurred: " + str(e))

# any other thing received by bot
@bot.message_handler(func=lambda message: True)
def all_other_forms_of_messages(message):
    bot.reply_to(message, wrong_link_message, disable_web_page_preview=True)
    log(bot_name + " log:\n❌wrong link pattern from user: " + str(message.chat.id) + " with contents of:\n" + message.text)

def main():
    bot.infinity_polling()

if __name__ == '__main__':
    main()
