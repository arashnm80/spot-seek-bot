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

# env variables
bot_api = os.environ["NM80_MUSIC_BOT_API"]
database_channel = os.environ["NM80_MUSIC_DATABASE_ID"]

# spotify song link regex pattern
link_pattern = r'https:\/\/open\.spotify\.com\/track\/[a-zA-Z0-9]+'

# log chanel
log_bot_url = "https://api.telegram.org/bot" + os.environ['NM80_LOG_BOT_API'] + "/"
log_channel_id = os.environ['LOG_CHANNEL_ID']
