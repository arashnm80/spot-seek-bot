from queue_functions import *
from my_imports import *
from db_functions import *
from telebot.types import InlineQueryResultCachedAudio, ReactionTypeEmoji

import traceback
import asyncio
import re

# todo: isn't best practice and can be optimized later.
# to keep track of last query and deboune fast changes while user is still typing
last_queries = {}

# Change bot initialization to use AsyncTeleBot
bot = async_bot

# defined commands
@bot.message_handler(commands = ['start'])
async def start_message_handler(message):
    await bot.send_message(message.chat.id, welcome_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n📥 /start command sent from user: " + str(message.chat.id))

@bot.message_handler(commands = ['info'])
async def info_message_handler(message):
    await bot.send_message(message.chat.id, info_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n📥 /info command sent from user: " + str(message.chat.id))

@bot.message_handler(commands = ['privacy'])
async def privacy_message_handler(message):
    await bot.send_message(message.chat.id, privacy_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n📥 /privacy command sent from user: " + str(message.chat.id))

# wrong defined patterns such as deezer, youtube, ...
@bot.message_handler(regexp = deezer_link_pattern)
async def deezer_link_handler(message):
    await bot.send_message(message.chat.id, deezer_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗❌ deezer link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = soundcloud_link_pattern)
async def soundcloud_link_handler(message):
    await bot.send_message(message.chat.id, soundcloud_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗❌ soundcloud link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = youtube_link_pattern)
async def youtube_link_handler(message):
    await bot.send_message(message.chat.id, youtube_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗❌ youtube link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = instagram_link_pattern)
async def instagram_link_handler(message):
    await bot.send_message(message.chat.id, instagram_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗❌ instagram link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = spotify_episode_link_pattern)
async def spotify_episode_link_handler(message):
    await bot.send_message(message.chat.id, spotify_episode_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗❌ episode link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = spotify_artist_link_pattern)
async def spotify_artist_link_handler(message):
    await bot.send_message(message.chat.id, spotify_artist_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗❌ artist link sent from user: " + str(message.chat.id))

@bot.message_handler(regexp = spotify_user_link_pattern)
async def spotify_user_link_handler(message):
    await bot.send_message(message.chat.id, spotify_user_link_message, parse_mode="Markdown", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗❌ user link sent from user: " + str(message.chat.id))

# thank you message from user
@bot.message_handler(func=lambda message: message.text and message.text.lower().strip() in thank_you_keywords)
async def thank_you_message_handler(message):
    # give user a '❤️' reaction
    reaction = [ReactionTypeEmoji(emoji='❤️')]
    await bot.set_message_reaction(message.chat.id, message.message_id, reaction, is_big=True)

@bot.inline_handler(lambda query: True)
async def query_text(inline_query):
    # check that query is not empty
    if not inline_query.query:
        return
    
    # Store the current query
    last_queries[inline_query.from_user.id] = inline_query.query
    # Wait briefly to see if the user keeps typing
    await asyncio.sleep(0.6)
    # If user typed something new during the wait, skip this request
    if last_queries.get(inline_query.from_user.id) != inline_query.query:
        return

    # search and find tracks from spotify. then check our local db
    tracks = search_track_ids(inline_query.query)

    results = [
        InlineQueryResultCachedAudio(
            id=track["id"],
            audio_file_id=track['telegram_audio_id'],
            caption="@SpotSeekBot"
        )
        for track in tracks
    ]

    # fixme: why this log line doesn't work (it prints though)
    log(bot_name + " log:\n\n🔍 inline query from user:\n" + str(inline_query.from_user.id) + "\n\nchat type:\n" + str(inline_query.chat_type) + "\n\nquery:\n" + inline_query.query)
    
    # Send the results back to Telegram
    await bot.answer_inline_query(inline_query.id, results)

# correct pattern
@bot.message_handler(regexp = spotify_correct_link_pattern)
async def handle_correct_spotify_link(message):
    try:      
        beginning_log_text = (bot_name + " log:\n\n🔗✅ correct link pattern from user:\n" + str(message.chat.id) + "\n\ncontents:\n" + message.text)
        
        # # fixme - temporary disabled to lower requests load
        # # give user a '👍' reaction
        # reaction = [ReactionTypeEmoji(emoji='👍')]
        # await bot.set_message_reaction(message.chat.id, message.message_id, reaction)

        # Check the membership status and stop continuing if user is not a member
        is_member = check_membership(promote_channel_username, message.chat.id)

        if is_member:
            log(beginning_log_text + "\n\n👥member of channel: ✅")
        else:
            log(beginning_log_text + "\n\n👥member of channel: ❌")
            
            # Send message with join button to user
            keyboard = types.InlineKeyboardMarkup()
            channel_button = types.InlineKeyboardButton(text='Join', url=promote_channel_link)
            keyboard.add(channel_button)
            await bot.send_message(message.chat.id,
                            not_subscribed_to_channel_message,
                            parse_mode="Markdown",
                            disable_web_page_preview=True,
                            reply_markup=keyboard)

            return

        valid_spotify_links_in_user_text = get_valid_spotify_links(message.text)

        # if user sends multiple links combined with normal text we only extract and
        # analyze first one so the bot won't be spammed
        first_link = valid_spotify_links_in_user_text[0]

        # if the link is shortened convert "spotify.link" to "open.spotify.com"
        if get_link_type(first_link) == "shortened":
            log(bot_name + " log:\n🔗🩳 shortened link sent from user: " + str(message.chat.id))
            first_link = get_redirect_link(first_link)

        link_type = get_link_type(first_link)
        if link_type not in ["track", "album", "playlist"]:
            await bot.send_message(message.chat.id, "Looks like this link is wrong, expired or not supported. Try another.")
            log(bot_name + " log:\n🛑 error in handling short link.")
            return

        matches = get_track_ids(first_link)
        
        # more than 1000 tracks
        if len(matches) > 1000:
            await bot.send_message(message.chat.id, more_than_1000_tracks_message)
            log(bot_name + " log:\n1️⃣0️⃣0️⃣0️⃣ Playlist more than 1000 tracks from user: " + str(message.chat.id))
            return

        # no tracks
        if not matches:
            await bot.send_message(message.chat.id, "sorry I couldn't extract tracks from link.")
            log(bot_name + " log:\n0️⃣ Zero tracks error from user: " + str(message.chat.id))
            return

        # if files are already in database bypass the queue handler system (can be optimized later. currently there are duplicate codes in handler and here)
        tracks_to_download = []
        total_tracks = len(matches)
        available_tracks = 0
        media_group = []
        while matches:
            track_id = matches.pop(0) # remove the track from list and store it in track_id
            telegram_audio_id = get_telegram_audio_id(track_id)
            if telegram_audio_id is not None:
                media_group.append(types.InputMediaAudio(media=telegram_audio_id, caption=bot_username))
                available_tracks += 1
            else:
                tracks_to_download.append(track_id)
            # send media group if they become 10 or they are remaining for last pack
            if len(media_group) == 10 or (len(media_group) > 0 and not matches):
                if len(media_group) == 1: # there is only one track
                    await bot.send_audio(message.chat.id, media_group[0].media, caption=bot_username, disable_notification=True)
                else: # there are at least 2 tracks
                    await bot.send_media_group(message.chat.id, media_group, disable_notification=True)
                media_group = [] # empty the media group
                await asyncio.sleep(5)

        # add unavailable tracks to queue (if there are any)
        if tracks_to_download:
            append_list_to_file(tracks_to_download, received_links_folder_path + "/" + str(message.chat.id))

        # no tracks left for queue handler
        if not matches:
            if available_tracks == 0 and total_tracks == 1:
                end_message = f"Sorry, this track is not available in my database at the moment.\nI'll try to download it as soon as possible.\nBut you are welcome to try me with other spotify links❤️."
            elif available_tracks == 0:
                end_message = f"Sorry, none of these tracks were available in my database.\nI'll try to download them as soon as possible.\nBut you are welcome to try me with other spotify links❤️."
            elif available_tracks < total_tracks:
                end_message = f"{available_tracks} of {total_tracks} tracks were available in my database.\nI'll try to download the rest as soon as possible.\nYou are welcome to try me with other spotify links❤️."
            else:
                end_message = successfull_end_message
                # starpal promotion
                if message.from_user.language_code == "fa":
                    end_message = starpal_promotion_msg
                    log(f"{bot_username} log:\n\nuser: {message.chat.id}\n\n⭐️ starpal promotion for iranian user")
            await bot.send_message(message.chat.id, end_message, parse_mode="Markdown", disable_web_page_preview=True)
            return

    except Exception as e:
        log(bot_name + " log:\n🛑 A general error occurred: " + str(e))
        print(traceback.format_exc())
        try: # I added this try & except block to check if I can solve the unclosed spotseek.py processes
            await bot.send_message(message.chat.id, unsuccessful_process_message, parse_mode="Markdown")
        except:
            return

# Update the handler for any received link not caught by previous handlers
@bot.message_handler(func=lambda message: re.search(r'https?://(?:www\.)?\S+', message.text) is not None)
async def handle_uncaught_links(message):
    await bot.send_message(message.chat.id, "This link wasn't recognized by the bot. Please ensure it's a valid Spotify link.", disable_web_page_preview=True)
    log(bot_name + " log:\n🔗 Unrecognized link from user: " + str(message.chat.id) + " with contents of:\n" + message.text)

# search for user queries | less than 100 characters
@bot.message_handler(func=lambda m: m.text and len(m.text.strip()) <= 100)
async def handle_search(message):
    log(bot_name + " log:\n🔍 search query from user: " + str(message.chat.id) + " with contents of:\n" + message.text)
    try:
        query = message.text
        results = search_track_ids(query)

        if not results:
            await bot.send_message(message.chat.id, "No tracks found for your search.")
            return

        # create inline buttons
        markup = types.InlineKeyboardMarkup()
        for track in results:
            btn = types.InlineKeyboardButton(
                text=f"{track['artist']} - {track['name']}", 
                callback_data=f"track_{track['id']}"
            )
            markup.add(btn)
        
        await bot.send_message(message.chat.id, "Related tracks for your search:", reply_markup=markup)
    except Exception as e:
        log("error in handle_search: " + str(e))

@bot.callback_query_handler(func=lambda call: call.data.startswith("track_"))
async def handle_track_selection(call):
    track_id = call.data.split("_")[1]
    telegram_audio_id = get_telegram_audio_id(track_id)
    await bot.send_audio(call.message.chat.id, telegram_audio_id, caption=bot_username)
    await bot.answer_callback_query(call.id)

# any other thing received by bot
@bot.message_handler(func=lambda message: True)
async def all_other_forms_of_messages(message):
    await bot.reply_to(message, wrong_link_message, disable_web_page_preview=True)
    log(bot_name + " log:\n❌wrong link pattern from user: " + str(message.chat.id) + " with contents of:\n" + message.text)

def main():
    asyncio.run(bot.infinity_polling())

if __name__ == '__main__':
    main()
