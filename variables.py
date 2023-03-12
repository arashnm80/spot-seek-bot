import os

# bot name
bot_name = "Spot Seek Bot"
bot_username = "@SpotSeekBot"

# message for /start command
welcome_message = '''Welcome to @SpotSeekBot

Send me a link from spotify and I'll download it for you.
It can be a track link like this:
https://open.spotify.com/track/734dz1YaFITwawPpM25fSt
Or an album like this:
https://open.spotify.com/album/0Lg1uZvI312TPqxNWShFXL
Or a playlist like this:
https://open.spotify.com/playlist/37i9dQZF1DWX4UlFW6EJPs

This is currently the beta version of the bot and it's under test. I you found a bug or had any feedbacks I'll be glad to hear from you. \
You can contact me at: @Arashnm80

This bot whole open source is available in github and all interested programmers are welcome to contribute and improve it:
https://github.com/arashnm80/spot-seek-bot

You can find out more about me and my works through my channel:
@Arashnm80_Channel

If you find my works helpful you can give me energy with coffee☕️:
coffeete.ir/arashnm80 (﷼)
buymeacoffee.com/Arashnm80 (dollar)'''

# message for /info command
info_message = '''Here are known bugs and problems so for that should be fixed later:

- some musics duration or size is not shown
- only 1 single user can use the bot and it can't multitask
- downloading all songs of an artist is not available
- searching in database algorithm isn't fast and efficient
- caption is not always visible'''

# download directory
directory = "./output/"

# csv files path
db_csv_path = "./csv_files/db.csv"
users_csv_path = "./csv_files/users.csv"

# env variables
bot_api = os.environ["SPOT_SEEK_BOT_API"]
database_channel = os.environ["MUSIC_DATABASE_ID"]

# spotify regex patterns
spotify_track_link_pattern = r'https:\/\/open\.spotify\.com\/track\/[a-zA-Z0-9]+'
spotify_album_link_pattern = r'https:\/\/open\.spotify\.com\/album\/[a-zA-Z0-9]+'
spotify_playlist_link_pattern = r'https:\/\/open\.spotify\.com\/playlist\/[a-zA-Z0-9]+'
spotify_correct_link_pattern = spotify_track_link_pattern + "|" + spotify_album_link_pattern + "|" + spotify_playlist_link_pattern
#spotify_track_id_pattern = r"spotify\.com\/track\/(\w+)(?:\?.*)?$"
#spotify_album_id_pattern = r"spotify\.com\/album\/(\w+)(?:\?.*)?$"
#spotify_playlist_id_pattern = r"spotify\.com\/playlist\/(\w+)(?:\?.*)?$"

# log chanel
log_bot_url = "https://api.telegram.org/bot" + bot_api + "/"
log_channel_id = os.environ['LOG_CHANNEL_ID']

# spotify
spotify_client_id = os.environ["SPOTIFY_TEST_APP_CLIENT_ID"]
spotify_client_secret = os.environ["SPOTIFY_TEST_APP_CLIENT_SECRET"]

# database csv columns
db_time_column = 0
db_sp_track_column = 1
db_tl_audio_column = 2

# users csv columns
ucsv_user_id_column = 0
ucsv_last_time_column = 1

# data and time format in csv files
datetime_format = "%Y/%m/%d-%H:%M:%S"

# necessary time in seconds for user to wait between 2 requests
user_request_wait = 30
