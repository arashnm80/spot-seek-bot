from my_imports import *
from queue_functions import *


def _tg_button_text(text, limit=64):
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _search_caption(query, kind, result_count):
    noun = "tracks" if kind == "track" else "albums"
    if result_count:
        return f'Search: {query}\n\nRelated {noun}:'
    return (
        f"Search: {query}\n\n"
        f"No matching {noun}. Try the other tab, or send a Spotify link."
    )


def _search_results_markup(kind, items):
    markup = types.InlineKeyboardMarkup()
    tracks_label = "🎵 Tracks ✓" if kind == "track" else "🎵 Tracks"
    albums_label = "💿 Albums ✓" if kind == "album" else "💿 Albums"
    markup.row(
        types.InlineKeyboardButton(text=tracks_label, callback_data="sm_t"),
        types.InlineKeyboardButton(text=albums_label, callback_data="sm_a"),
    )
    prefix = "track_" if kind == "track" else "album_"
    for item in items:
        label = f"{item.get('artist') or ''} - {item.get('name') or ''}".strip(" -")
        markup.add(
            types.InlineKeyboardButton(
                text=_tg_button_text(label),
                callback_data=f"{prefix}{item['id']}",
            )
        )
    return markup


async def fulfill_track_ids(
    bot,
    chat_id,
    matches,
    *,
    user_id,
    is_premium=False,
    language_code=None,
    reply_to_message_id=None,
):
    """Send cached audio in packs of 10, enqueue the rest, then an end summary."""
    pending = list(matches)
    tracks_to_download = []
    total_tracks = len(pending)
    available_tracks = 0
    media_group = []
    while pending:
        track_id = pending.pop(0)
        telegram_audio_id = get_telegram_audio_id(track_id)
        if telegram_audio_id is not None:
            media_group.append(types.InputMediaAudio(media=telegram_audio_id, caption=bot_username))
            available_tracks += 1
        else:
            tracks_to_download.append(track_id)
            track_link = f"https://open.spotify.com/track/{track_id}"
            await do_with_retry(
                bot.send_message,
                chat_id,
                f"track [{track_id}]({track_link}) is not available yet, try again for it later.",
                disable_notification=True,
                parse_mode="Markdown",
            )
            await asyncio.sleep(1)

        if len(media_group) == 10 or (len(media_group) > 0 and not pending):
            if len(media_group) == 1:
                await do_with_retry(
                    bot.send_audio,
                    chat_id,
                    media_group[0].media,
                    caption=bot_username,
                    disable_notification=True,
                )
                print(f"single audio sent to user {chat_id}")
            else:
                await do_with_retry(
                    bot.send_media_group,
                    chat_id,
                    media_group,
                    disable_notification=True,
                )
                print(f"media group sent to user {chat_id}")
            media_group = []
            await asyncio.sleep(1)

    if tracks_to_download:
        enqueue_tracks(chat_id, tracks_to_download)

    if available_tracks == 0:
        end_message = "end💔."
        record_request_outcome(user_id, False)
    elif available_tracks < total_tracks:
        end_message = f"{available_tracks} of {total_tracks} done✅."
        record_request_outcome(user_id, False)
    else:
        end_message = successfull_end_message
        record_request_outcome(user_id, True)
    kwargs = {}
    if reply_to_message_id is not None:
        kwargs["reply_parameters"] = ReplyParameters(message_id=reply_to_message_id)
    await bot.send_message(chat_id, end_message, **kwargs)


def register_handlers(bot):
    '''
    register all bot handlers
    '''
    # defined commands
    @bot.message_handler(commands = ['start'])
    async def start_message_handler(message):
        await bot.send_message(message.chat.id, welcome_message)
        add_or_update_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.language_code,
            message.from_user.is_premium if message.from_user.is_premium is not None else False,
        )
        log(bot_name + " log:\n📥 /start command sent from user: " + str(message.chat.id))

    @bot.message_handler(commands = ['info'])
    async def info_message_handler(message):
        await bot.send_message(message.chat.id, info_message)
        log(bot_name + " log:\n📥 /info command sent from user: " + str(message.chat.id))

    @bot.message_handler(commands = ['privacy'])
    async def privacy_message_handler(message):
        await bot.send_message(message.chat.id, privacy_message)
        log(bot_name + " log:\n📥 /privacy command sent from user: " + str(message.chat.id))

    # wrong defined patterns such as deezer, youtube, ...
    @bot.message_handler(regexp = deezer_link_pattern)
    async def deezer_link_handler(message):
        await bot.send_message(message.chat.id, deezer_link_message)
        log(bot_name + " log:\n🔗❌ deezer link sent from user: " + str(message.chat.id))

    @bot.message_handler(regexp = soundcloud_link_pattern)
    async def soundcloud_link_handler(message):
        await bot.send_message(message.chat.id, soundcloud_link_message)
        log(bot_name + " log:\n🔗❌ soundcloud link sent from user: " + str(message.chat.id))

    @bot.message_handler(regexp = youtube_link_pattern)
    async def youtube_link_handler(message):
        await bot.send_message(message.chat.id, youtube_link_message)
        log(bot_name + " log:\n🔗❌ youtube link sent from user: " + str(message.chat.id))

    @bot.message_handler(regexp = instagram_link_pattern)
    async def instagram_link_handler(message):
        await bot.send_message(message.chat.id, instagram_link_message)
        log(bot_name + " log:\n🔗❌ instagram link sent from user: " + str(message.chat.id))

    @bot.message_handler(regexp = spotify_episode_link_pattern)
    async def spotify_episode_link_handler(message):
        await bot.send_message(message.chat.id, spotify_episode_link_message)
        log(bot_name + " log:\n🔗❌ episode link sent from user: " + str(message.chat.id))

    @bot.message_handler(regexp = spotify_artist_link_pattern)
    async def spotify_artist_link_handler(message):
        await bot.send_message(message.chat.id, spotify_artist_link_message)
        log(bot_name + " log:\n🔗❌ artist link sent from user: " + str(message.chat.id))

    @bot.message_handler(regexp = spotify_user_link_pattern)
    async def spotify_user_link_handler(message):
        await bot.send_message(message.chat.id, spotify_user_link_message)
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
        add_or_update_user(
            inline_query.from_user.id,
            inline_query.from_user.username,
            inline_query.from_user.language_code,
            inline_query.from_user.is_premium if inline_query.from_user.is_premium is not None else False,
        )
        # Wait briefly to see if the user keeps typing
        await asyncio.sleep(1)
        # If user typed something new during the wait, skip this request
        if last_queries.get(inline_query.from_user.id) != inline_query.query:
            return

        # search and find tracks from spotify. then check our local db
        try:
            tracks = search_track_ids(inline_query.query, require_in_db=True)
        except Exception as e:
            log_exception("error in inline search", e)
            await bot.answer_inline_query(inline_query.id, [])
            return

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
            # Update user information in database
            user_id = message.from_user.id
            username = message.from_user.username
            language_code = message.from_user.language_code
            is_premium = message.from_user.is_premium if message.from_user.is_premium is not None else False
            add_or_update_user(user_id, username, language_code, is_premium)
            
            beginning_log_text = (
                f"{bot_name} log:\n\n"
                f"🔗✅ correct link pattern.\n\n"
                f"user: {message.chat.id}\n\n"
                f"chat type: {message.chat.type}\n\n"
                f"contents:\n{message.text}"
            )
            
            # # fixme - temporary disabled to lower requests load
            # # give user a '👍' reaction
            # reaction = [ReactionTypeEmoji(emoji='👍')]
            # await bot.set_message_reaction(message.chat.id, message.message_id, reaction)

            # New users can try the bot freely. After a streak of fully
            # successful requests, require joining the promo channel.
            if user_should_join_channel(user_id):
                chat_member = await bot.get_chat_member(promote_channel_username, message.chat.id)
                allowed_types = (
                    telebot.types.ChatMemberOwner,
                    telebot.types.ChatMemberAdministrator,
                    telebot.types.ChatMemberMember
                )
                if isinstance(chat_member, allowed_types):
                    log(beginning_log_text + "\n\n👥member of channel: ✅")
                else:
                    log(
                        beginning_log_text
                        + f"\n\n👥member of channel: ❌ (streak {get_consecutive_successes(user_id)})"
                    )
                    keyboard = types.InlineKeyboardMarkup()
                    channel_button = types.InlineKeyboardButton(text='Join', url=promote_channel_link)
                    keyboard.add(channel_button)
                    await bot.send_message(
                        message.chat.id,
                        not_subscribed_to_channel_message,
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                        reply_markup=keyboard
                    )
                    return
            else:
                log(
                    beginning_log_text
                    + f"\n\n👥join gate skipped (streak {get_consecutive_successes(user_id)}"
                    + f"/{promote_channel_join_after_successes})"
                )

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

            print(f"1️⃣ before get_track_ids from spotify {first_link}")
            matches = get_track_ids(first_link)
            print(f"2️⃣ after get_track_ids from spotify {first_link}")
            
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

            await fulfill_track_ids(
                bot,
                message.chat.id,
                matches,
                user_id=user_id,
                is_premium=is_premium,
                language_code=message.from_user.language_code,
                reply_to_message_id=message.message_id,
            )
            return

        except Exception as e:
            log(bot_name + " log:\n🛑 A general error occurred: " + str(e))
            print(traceback.format_exc())
            try: # I added this try & except block to check if I can solve the unclosed spotseek.py processes
                await bot.send_message(message.chat.id, unsuccessful_process_message)
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
        log(
            f"{bot_name} log:\n"
            f"🔍 search query from user: {message.chat.id}\n"
            f"chat type: {message.chat.type}\n"
            f"contents: {message.text}"
        )
        try:
            add_or_update_user(
                message.from_user.id,
                message.from_user.username,
                message.from_user.language_code,
                message.from_user.is_premium if message.from_user.is_premium is not None else False,
            )
            query = message.text
            results = search_spotify_items(query, kind="track")
            sent = await bot.send_message(
                message.chat.id,
                _search_caption(query, "track", len(results)),
                reply_markup=_search_results_markup("track", results),
            )
            last_chat_searches[(sent.chat.id, sent.message_id)] = query
        except Exception as e:
            log_exception("error in handle_search", e)
            try:
                await bot.send_message(message.chat.id, unsuccessful_process_message)
            except Exception:
                return

    @bot.callback_query_handler(func=lambda call: call.data in ("sm_t", "sm_a"))
    async def handle_search_mode(call):
        kind = "album" if call.data == "sm_a" else "track"
        query = last_chat_searches.get((call.message.chat.id, call.message.message_id))
        if not query:
            await bot.answer_callback_query(call.id, "Search again — this result is too old.")
            return
        try:
            results = search_spotify_items(query, kind=kind)
            await bot.edit_message_text(
                _search_caption(query, kind, len(results)),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_search_results_markup(kind, results),
            )
            await bot.answer_callback_query(call.id)
        except Exception as e:
            if "message is not modified" in str(e).lower():
                await bot.answer_callback_query(call.id)
                return
            log_exception("error in search mode switch", e)
            await bot.answer_callback_query(call.id, "Search failed. Try again.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("album_"))
    async def handle_album_selection(call):
        album_id = call.data.split("_", 1)[1]
        await bot.answer_callback_query(call.id, "Opening album…")
        try:
            matches = get_track_ids(f"https://open.spotify.com/album/{album_id}")
        except Exception as e:
            log_exception("error fetching album from search", e)
            await bot.send_message(call.message.chat.id, unsuccessful_process_message)
            return
        if not matches:
            await bot.send_message(call.message.chat.id, "sorry I couldn't extract tracks from that album.")
            return
        if len(matches) > 1000:
            await bot.send_message(call.message.chat.id, more_than_1000_tracks_message)
            return
        user = call.from_user
        is_premium = user.is_premium if user.is_premium is not None else False
        try:
            await fulfill_track_ids(
                bot,
                call.message.chat.id,
                matches,
                user_id=user.id,
                is_premium=is_premium,
                language_code=user.language_code,
            )
        except Exception as e:
            log_exception("error delivering album from search", e)
            await bot.send_message(call.message.chat.id, unsuccessful_process_message)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("track_"))
    async def handle_track_selection(call):
        track_id = call.data.split("_", 1)[1]
        telegram_audio_id = get_telegram_audio_id(track_id)
        if telegram_audio_id is None:
            enqueue_tracks(call.message.chat.id, [track_id])
            await bot.answer_callback_query(call.id, "Not in the library yet. I'll download it — send the Spotify link again later.")
            await bot.send_message(
                call.message.chat.id,
                f"track [{track_id}](https://open.spotify.com/track/{track_id}) is not available yet, try again for it later.",
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
            return
        await bot.send_audio(call.message.chat.id, telegram_audio_id, caption=bot_username)
        await bot.answer_callback_query(call.id)
        await bot.send_message(call.message.chat.id, successfull_end_message)

    # any other thing received by bot
    @bot.message_handler(func=lambda message: True)
    async def all_other_forms_of_messages(message):
        log(
            f"{bot_name} log:\n"
            f"❌wrong link pattern from user: {message.chat.id}\n"
            f"chat type: {message.chat.type}\n"
            f"with contents of:\n{message.text}"
        )
        await bot.reply_to(message, wrong_link_message, disable_web_page_preview=True)