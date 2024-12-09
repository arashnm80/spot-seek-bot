# telegram spotify downloader bot: [@SpotSeekBot](https://t.me/SpotSeekBot)

## how to use as the client
Send bot a link from spotify and it'll download it for you.
  - It can be a track link like this:
https://open.spotify.com/track/734dz1YaFITwawPpM25fSt
  - Or an album like this:
https://open.spotify.com/album/0Lg1uZvI312TPqxNWShFXL
  - Or a playlist like this:
https://open.spotify.com/playlist/37i9dQZF1DWX4UlFW6EJPs

## how to deploy as the developer (I'm writing this guide for ubuntu)
- general pre-install updates in ubuntu:
```
$ sudo apt update
$ sudo apt upgrade
$ sudo apt-get update
$ sudo apt-get upgrade
```
- clone the repo
- set required environment variables in a file like `/etc/environment/` (affects on reboot):
  - `SPOT_SEEK_BOT_API` - main api key of telegram bot
  - `MUSIC_DATABASE_ID` - private music database channel which bot is its admin
  - `LOG_CHANNEL_ID` - private log channel which bot is its admin
- set required variables in `variables.py` file:
  - `promote_channel_username` - set to a channel that bot promotes and is its admin (begining with `@`)
  - `warp_mode` - set to `False` if you don't have warp socks proxy
  - `spotify_apps_list` - a list of spotify app ids and secrets, obtainable from [developer.spotify.com](https://developer.spotify.com/)
- install `pip`:
```
apt install python3-pip
```
- install necessary python modules (or read the requrements modules and install them one by one):
```
pip install -r requirements.txt
```
- install `ffmpeg` with:
```
apt install ffmpeg
```
- install `warp` and `proxychians` if you want to use `warp_mode` in `variables.py` (if not, just set it as `False`):
  - `warp`: I got it as a side feature by installing [MHSanaei 3x-ui](https://github.com/MHSanaei/3x-ui). You might be able to install it via [fscarmen warp](https://github.com/fscarmen/warp) too.
  - `proxychains` (I've written config based on port 40000 in `proxychains.conf` file): `sudo apt-get install proxychains4`
- make scripts that run the bot executable:
```
chmod +x restart_spotseek.sh restart_spotseek_queue_handler.sh
```
add this text to crontab (change with the path you've cloned repository):
```
# spotseek
## run main scripts on reboot
@reboot /root/Storage/spot-seek-bot/restart_spotseek.sh
@reboot /root/Storage/spot-seek-bot/restart_spotseek_queue_handler.sh
## temp solution to reset every hour to free up memory
0 * * * * /root/Storage/spot-seek-bot/restart_spotseek.sh
```
- reboot once to affect

## technical info about how this bot works
- When you send a spotify link to the bot it searches through its database and if it's the first time it sees this link it will download it with spotdl but if it has done it before it saves time by using previously downloaded files from database.
- I've set 30 seconds waiting time for 2 requests in a row from 1 user so it won't be spammed
- I've set log channel and database channel for the bot. It stores every downloaded song in database channel and use it as a storage and prints logs from everything to log channel (errors, user messags, ...)
- We use spotify api to get tracks from a valid link so you should sign up in https://developer.spotify.com/ and get your own token.
- All mp3 files are downloaded with high 320k quality.

## csv files columns guide
- Note: starting template of each csv should be headers and **one empty new line** after them
### database csv columns
`date and time added` | `spotify track id` | `telegram audio id`
### users csv columns
`unique user id` | `last use date and time`

## TO-DO: ideas & bugs to fix & features to add
- [x] ~fix caption so it will be shown for repetitive tracks~
- [x] ~some musics metadata is not shown~
- [ ] bot should send available tracks to users while new one is being downloaded with spotdl to use best of time.
- [ ] higher priority for first time users
- [x] ~only 1 single user can use the bot and it can't multitask~
- [ ] use a library like telethon for big mp3 files more than 50MB
- [x] ~searching in database algorithm isn't fast and efficient~
- [x] ~Download playlists with more thatn 100 songs~
- [ ] find a clean way to give access to database to next bot maintainers
- [ ] merge database of all spotify downloaders together
- [x] ~showing message to user when link from other services like deezer is sent.~
- [ ] support searching name of song by user
- [ ] find a way to shorten database (audio IDs are very long)
- [x] if all track_ids that a user wants already exists bypass normall routine and send all of them to him
- [x] ~test `portalocker` funcion from `db_csv_append` separately~
- [x] handle blocked by user link
- [ ] manage too threads bug
- [x] ~regex should handle both http and https~
- [x] make `restart_spotseek.sh` work without reboot too
- [ ] restarting queue handler doesn't stop previous spotdl download so there might be an excessive mp3 file that might lead to creating wrong track
- [ ] add gif tutorial for bot in the start
- [ ] check out `zotify` capabilities
- [ ] lyrics
- [ ] send picture and info of link
- [ ] private playlist answer
- [ ] more features for premium users
- [ ] read track data without api key in similar way to https://spotify.detta.dev/

## disclaimer
This project is for personal learning, do not use it for illegal purposes. Artists can send their copyright claims to the developer.

## support and donate
### Give me energy with coffee:
- [BuyMeACoffee](https://www.buymeacoffee.com/Arashnm80) (🇺🇸 $)
- [Coffeete](https://www.coffeete.ir/Arashnm80) (🇮🇷 ريال)
### Continuous monthly support:
- [Patreon](https://www.patreon.com/Arashnm80) (🇺🇸 $)
- [HamiBash](https://hamibash.com/Arashnm80) (🇮🇷 ريال)