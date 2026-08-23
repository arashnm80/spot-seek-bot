import os
import requests
import json

from dotenv import load_dotenv

# Load repo-root .env (not cwd: queue handler may run from output/).
# override=False so existing process env / /etc/environment still wins.
_repo_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_repo_dir, ".env"), override=False)

import telebot
from telebot.async_telebot import AsyncTeleBot

# env variables
bot_api = os.environ["SPOT_SEEK_BOT_API"]
database_channel = os.environ["MUSIC_DATABASE_ID"]

# initialize bot (2 instances for sync and async mode)
bot = telebot.TeleBot(bot_api)
async_bot = AsyncTeleBot(bot_api, parse_mode="Markdown", disable_web_page_preview=True)

# bot name
bot_name = "Spot Seek Bot"
bot_username = "@SpotSeekBot"

# todo: isn't best practice and can be optimized later.
# to keep track of last query and debounce fast changes while user is still typing
last_queries = {}
# chat search results message -> original query (Tracks/Albums toggle)
last_chat_searches = {}

# message for /start command
welcome_message = '''Hi😃👋

You can search for a song or album by typing its name. for example try this:
`Adele - Someone Like You`
Then switch between Tracks and Albums on the results.


Or you can send me a spotify link like these👇
♪ track
https://open.spotify.com/track/734dz1YaFITwawPpM25fSt
🎵 album
https://open.spotify.com/album/0Lg1uZvI312TPqxNWShFXL
🎶 playlist
https://open.spotify.com/playlist/3ceLS7hutXrwz03g0c11gW


You can also search for songs in other chats, groups or channels by using the inline mode of the bot. for example type this in some other chat:
`@SpotSeekBot Adele - Someone Like You`

(In inline mode you write bot's username and type a song name after a space)
'''

# message for /info command
info_message = '''This bot's whole open source is available in my github and all interested programmers are welcome to contribute and improve it.

Developer's telegram channel:
[https://t.me/Arashnm80_Channel](https://t.me/Arashnm80_Channel)

Note: albums are downloaded faster than playlists and tracks are downloaded faster than albums.

You can support and motivate me to buy more servers for faster download by:
• Giving a star in [github](https://github.com/arashnm80/spot-seek-bot)⭐🙂
• Or subscribing to [my youtube](https://www.youtube.com/@Arashnm80)🔥❤️'''

# message for /privacy command
privacy_message = '''• This bot doesn't gather any info from the users
• Artists can send their copyright claims to the developer
• Bot's open source is available in github for educational purposes'''

# errors and wrong link patterns from user
deezer_link_message = '''This bot is for downloading from spotify but you sent a deezer link.
Send the link of your track/album/playlist from spotify'''
soundcloud_link_message = '''This bot is for downloading from spotify but you sent a soundcloud link.
Send the link of your track/album/playlist from spotify'''
youtube_link_message = '''This bot is for downloading from spotify but you sent a youtube link.
Send the link of your track/album/playlist from spotify'''
instagram_link_message = '''This bot is for downloading from spotify but you sent an instagram link.
Send the link of your track/album/playlist from spotify

Or use my [instagram downloader](https://t.me/Best_Instagram_downloader_bot) for this link.'''
spotify_episode_link_message = '''You can't send podcast episode links.
Send the link of your track/album/playlist from spotify'''
spotify_artist_link_message = '''You can't send artist links.
Send the link of your track/album/playlist from spotify'''
spotify_user_link_message = '''You can't send user links.
Send the link of your track/album/playlist from spotify'''


# successfull_end_message = '''Me:\n[Youtube](https://www.youtube.com/@Arashnm80) • [𝕏](https://x.com/Arashnm80) • [Github](https://github.com/arashnm80)'''
# successfull_end_message = '''end✅\n\nbot username might change. check @Arashnm80\\_Channel for the latest news.'''
successfull_end_message = '''end✅\nsponsor: @DiamondAccountStore'''

# successfull_end_message = '''If you liked the bot you can support me by giving a star [here](https://github.com/arashnm80/spot-seek-bot)⭐ (it's free)

# You can also check out my *Instagram Downloader* too: @Best\_Instagram\_downloader\_bot'''

# # replaced with promotion ad
# successfull_end_message = "end.\n\n💰 You’re not broke — you’re just paying wrong. Why spend $10–$15 monthly on Spotify & YouTube when others get the same premium for as low as $5/month or $20/year? Join 👉 @pinocelchannel 💡"

sth_to_download_message = '''You already have some link to download, wait for me to finish it.

Don't worry, this is not a bug. Sometimes more than 1000 users are sending links at the same time so it might take a while for me to download all of them.'''

wrong_link_message = '''This is not a correct spotify link.

You should send a track link like:
https://open.spotify.com/track/734dz1YaFITwawPpM25fSt

Or an album link like:
https://open.spotify.com/album/0Lg1uZvI312TPqxNWShFXL

Or a playlist link like:
https://open.spotify.com/playlist/3ceLS7hutXrwz03g0c11gW'''

starpal_promotion_msg = \
'''⭐️خرید ستاره تلگرام بدون احراز هویت و در کمتر از ۲ دقیقه!  👈  starpal.ir'''

# download directory
directory = "./output/"

# number of simultaneous downloads
simultaneous_downloads = 1

# timer to balance yt-dlp limit
queue_handler_sleep_timer = 5

# Album/playlist track-id cache so repeat links skip Spotify.
# Playlists: owners can add/remove tracks; until TTL expires we may serve the old list.
# Not a big deal — just remember new/removed songs can lag by up to playlist_cache_ttl.
album_cache_ttl_seconds = 90 * 24 * 3600
playlist_cache_ttl_seconds = 7 * 24 * 3600
# Search keywords: skip Spotify until TTL if we already stored the hit list.
search_cache_ttl_seconds = 30 * 24 * 3600

# Telegram log channel: one summary per this many download attempts, or this many seconds.
queue_log_flush_tracks = 50
queue_log_flush_seconds = 900

# paths
received_links_folder_path = "./received_links"

# spotify regex patterns
spotify_shortened_link_pattern = r'https?:\/\/spotify\.link\/[A-Za-z0-9]+'
spotify_track_link_pattern = r'https?:\/\/open\.spotify\.com\/(intl-[a-zA-Z]{2}\/)?track\/[a-zA-Z0-9]+'
spotify_album_link_pattern = r'https?:\/\/open\.spotify\.com\/(intl-[a-zA-Z]{2}\/)?album\/[a-zA-Z0-9]+'
spotify_playlist_link_pattern = r'https?:\/\/open\.spotify\.com\/(intl-[a-zA-Z]{2}\/)?playlist\/[a-zA-Z0-9]+'
spotify_correct_link_pattern = spotify_track_link_pattern + "|" + spotify_album_link_pattern + "|" + spotify_playlist_link_pattern + "|" + spotify_shortened_link_pattern
deezer_link_pattern = r'https?:\/\/(?:www\.)?deezer\.com\/(?:\w{2}\/)?(?:\w+\/)?(?:track|album|artist|playlist)\/\d+'
soundcloud_link_pattern = r"(?:https?://)?(?:www\.)?soundcloud\.com/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_]+)"
youtube_link_pattern = r"(?:(?:https?:)?//)?(?:www\.)?(?:(?:youtube\.com/(?:watch\?.*v=|embed/|v/)|youtu.be/))([\w-]{11})"
instagram_link_pattern = r'(?:https?://www\.)?instagram\.com\S*?/(p|reel)/([a-zA-Z0-9_-]{11})/?'
spotify_episode_link_pattern = r'https?:\/\/open\.spotify\.com\/(intl-[a-zA-Z]{2}\/)?episode\/[a-zA-Z0-9]+'
spotify_artist_link_pattern = r'https?:\/\/open\.spotify\.com\/(intl-[a-zA-Z]{2}\/)?artist\/[a-zA-Z0-9]+'
spotify_user_link_pattern = r'https?:\/\/open\.spotify\.com\/(intl-[a-zA-Z]{2}\/)?user\/[a-zA-Z0-9]+'

# log chanel
log_bot_url = "https://api.telegram.org/bot" + bot_api + "/"
log_channel_id = os.environ['LOG_CHANNEL_ID']

# specify to use warp or not
warp_mode = True

# warp socks proxy
warp_proxies = os.environ["WARP_PROXIES"]
warp_proxies = json.loads(warp_proxies)
warp_session = requests.Session()
warp_session.proxies.update(warp_proxies)

# proxychains
proxychains4_config_file = "/etc/proxychains4.conf" # from x-ui panel
# proxychains4_config_file = "/etc/proxychains4-oblivion-warp.conf" # from bepass-org

# promote channel
promote_channel_username = "@Arashnm80_Channel"
promote_channel_link = f"https://t.me/{promote_channel_username.lstrip('@')}"
# Ask to join the promo channel only after this many fully successful
# link requests in a row (all tracks already in the database and sent).
promote_channel_join_after_successes = 5
not_subscribed_to_channel_message = '''Your link is correct✅.
Join to get access to database, then send your link again.'''

# spotify app - new gen (multiple apps to bypass limits)
# template: a list of [spotify_client_id, spotify_client_secret]
# start with only a single app and add to them as users count grows
spotify_apps_list = os.environ["SPOTIFY_APPS_LIST"]
spotify_apps_list = json.loads(spotify_apps_list)

# How the bot talks to Spotify for metadata (track/album/search/cover + playlist ids).
# "official" — Web API client credentials (current). Playlist *contents* use SpotipyFree /
#   api-partner because official GET /playlists/{id}/tracks is 403 by design (2026).
# "anon" — previous SpotifyAnon web-player token path (official first, then Anon fallback).
spotify_auth_mode = "official"

# How spotdl finds a YouTube file. Stored on new rows as track_info.download_method.
# Older rows stay NULL (unknown / pre-tag). "youtube" = ytsearch, not YouTube Music.
spotdl_audio_provider = "youtube"

# spotdl — in-repo pip venv (not /root/Temp, not GitHub ELF).
# Proven 2026-08-20: spotdl 4.5.2 + yt-dlp 2026.08.19+ (see requirements-spotdl.txt).
spotdl_cache_path = "/root/.spotdl"
spotdl_venv_dir = os.path.join(_repo_dir, ".venv")
spotdl_bin = os.path.join(spotdl_venv_dir, "bin", "spotdl")
spotdl_requirements_file = os.path.join(_repo_dir, "requirements-spotdl.txt")
# ELF bootstrap retired: frozen 4.4.3/4.5.2 403 even with -f 140. Unused.
# spotdl_executable_link = "https://github.com/spotDL/spotify-downloader/releases/download/v4.4.3/spotdl-4.4.3-linux"
spotdl_executable_link = None
system_deno_dir = "/root/.deno/bin"

# yt-dlp
yt_dlp_cache_path = "/root/.cache/yt-dlp"

# necessary time in seconds for user to wait between 2 requests
user_request_wait = 30

unsuccessful_process_message = '''Sorry, my process wasn't sucessful :(

But you can try another link or use the bot again after some time, it might help.'''

abnormal_behavior_message = " log:\nNo matches found.\
this line should not happen in normal behavior\
becuase it is already checked with regex, if happens is a bug."

more_than_1000_tracks_message = "Bot can't download playlists more than 1000 tracks at the moment.\
This feature will be added later."

# errors messages
user_blocked_me_error = "A request to the Telegram API was unsuccessful. Error code: 403. Description: Forbidden: bot was blocked by the user"

deactivated_user_error = "A request to the Telegram API was unsuccessful. Error code: 403. Description: Forbidden: user is deactivated"

# Liste de messages de remerciement à reconnaître
thank_you_keywords = [
    'thank you',
    'thanks',
    'thank',
    'merci',
    'tnx',
    'thx',
    '❤️',
    '♥',
    '🙏',
    'ممنون'
    'مرسی'
    'تشکر'
]


# list of socks5 proxies in this format:
# "socks5://username:password@ip:port"
socks_proxies = json.loads(os.environ["SOCKS_PROXIES"])
current_proxy_index = 0
current_proxy = socks_proxies[current_proxy_index]


# Storage layout (Telegram hides messages past ~1M per channel; catalog is ~2.2M):
# - MUSIC_DATABASE_ID: original single DB channel (no longer written to).
# - CHANNEL_IDS sp1–sp10: archive from backup.py (batches of 10, round-robin). ~220k each.
# - SP11: current inbox for new queue downloads. When it nears 1M, add SP12 by hand.
# Users are served from sqlite telegram_audio_id, not by browsing a channel.
# S3 (hel1 object storage) was used during that backup, then deleted (cost). Do not upload.
CHANNEL_IDS = json.loads(os.environ["CHANNEL_IDS"])
SP11_CHANNEL_ID = int(os.environ["SP11_CHANNEL_ID"])

# S3 — unused. Bucket deleted (cost). Keep credentials/code; do not put_object.
S3_ENDPOINT = os.environ["S3_ENDPOINT"]
S3_ACCESS_KEY = os.environ["S3_ACCESS_KEY"]
S3_SECRET_KEY = os.environ["S3_SECRET_KEY"]
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]

# sftp configuration - for backup
sftp_host = os.environ["SFTP_HOST"]
sftp_port = int(os.environ.get("SFTP_PORT", "23"))
sftp_username = os.environ["SFTP_USERNAME"]
sftp_password = os.environ["SFTP_PASSWORD"]

# webhook
WEBHOOK_HOST = "https://spotseek.arashnm80.ir"  # your domain
# WEBHOOK_PATH = f"/bot{bot_api}"  # unique path (avoid collisions)
WEBHOOK_PATH = f"/bot"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBHOOK_SECRET_TOKEN = os.environ["WEBHOOK_SECRET_TOKEN"]
