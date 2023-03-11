import os

# message for /start command
welcome_message = '''welcome to nm80 music bot\n
send me a song link from spotify, for example:
https://open.spotify.com/track/734dz1YaFITwawPpM25fSt\n
this is the beta test version and currently it's 1 feature with a million bugs and changes to go, \
so test it and give me feedbacks and help me to improve it.
me: @Arashnm80'''

# download directory
directory = "./output/"

# csv files path
db_csv_path = "./csv_files/db.csv"
users_csv_path = "./csv_files/users.csv"

# env variables
bot_api = os.environ["NM80_MUSIC_BOT_API"]
database_channel = os.environ["NM80_MUSIC_DATABASE_ID"]

# spotify regex patterns
spotify_track_link_pattern = r'https:\/\/open\.spotify\.com\/track\/[a-zA-Z0-9]+'
spotify_album_link_pattern = r'https:\/\/open\.spotify\.com\/album\/[a-zA-Z0-9]+'
spotify_playlist_link_pattern = r'https:\/\/open\.spotify\.com\/playlist\/[a-zA-Z0-9]+'
spotify_correct_link_pattern = spotify_track_link_pattern + "|" + spotify_album_link_pattern + "|" + spotify_playlist_link_pattern
#spotify_track_id_pattern = r"spotify\.com\/track\/(\w+)(?:\?.*)?$"
#spotify_album_id_pattern = r"spotify\.com\/album\/(\w+)(?:\?.*)?$"
#spotify_playlist_id_pattern = r"spotify\.com\/playlist\/(\w+)(?:\?.*)?$"

# log chanel
log_bot_url = "https://api.telegram.org/bot" + os.environ['NM80_LOG_BOT_API'] + "/"
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
