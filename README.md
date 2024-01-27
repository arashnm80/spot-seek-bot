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
- set required environment variables, tokens and api keys. you can see them in `variables.py` file.
- download latest spotdl executable file, rename it to `spotdl` put it beside `spotseek.py` file. you can download linux version from https://github.com/spotDL/spotify-downloader/releases with a command like this:
```
wget -O spotdl https://github.com/spotDL/spotify-downloader/releases/download/v4.2.1/spotdl-4.2.1-linux
```
- then make spotdl executable:
```
chmod +x spotdl
```
- install `pip`:
```
apt install python3-pip
```
- install necessary python modules `(os, pandas, telebot, re, threading, csv, spotipy, subprocess, requests, datetime, pydub, mutagen, time)` all at once with:
```
pip install -r requirements.txt
```
- install `ffmpeg` with:
```
apt install ffmpeg
```
- install `warp` and `proxychians` if you want to use `warp_mode` in `variables.py` (if not, just set it as `False`):
  - `warp`: I got it as a side feature by installing [MHSanaei 3x-ui](https://github.com/MHSanaei/3x-ui). You might be able to install it via [fscarmen warp](https://github.com/fscarmen/warp) too.
  - `proxychains` (I've written config based on port 40000 in `proxychains.conf` file):
```
sudo apt-get install proxychains4
```
- run it with spotseek with:
```
nohup python3 spotseek.py > /dev/null 2>&1 &
```
or
```
nohup python3 spotseek.py &
```
- new method for running `spotseek.py`. old method leaves some dangling processes:
```
chmod +x restart_spotseek_py.sh
```
we add it to crontab with:
```
@reboot /root/Storage/spot-seek-bot/restart_spotseek_py.sh
0 */6 * * * /root/Storage/spot-seek-bot/restart_spotseek_py.sh
```
- I might haven't cleared datas in `db.csv`, If you are starting the whole infrastructure by yourself remove everything from it except first row which are the headers. you can keep data in db.csv and ask me to give you permission to database to you won't have to redownload all songs.

## technical info about how this bot works
- When you send a spotify link to the bot it searches through its database and if it's the first time it sees this link it will download it with spotdl but if it has done it before it saves time by using previously downloaded files from database.
- I've set 30 seconds waiting time for 2 requests in a row from 1 user so it won't be spammed
- I've set log channel and database channel for the bot. It stores every downloaded song in database channel and use it as a storage and prints logs from everything to log channel (errors, user messags, ...)
- We use spotify api to get tracks from a valid link so you should sign up in https://developer.spotify.com/ and get your own token.
- All mp3 files are downloaded with high 320k quality.

## status
I've created This bot to download musics by their link from spotify (single track, album or playlist)..

Also if you are a programmer you are welcome to contribute and improve the project or use it for yourself.

There is also a similar bot created by my friend [aliilapro](https://github.com/ALIILAPRO): [Spotdlrobot](https://t.me/Spotdlrobot)

## csv files columns guide
- Note: starting template of each csv should be headers and **one empty new line** after them
### database csv columns
`date and time added` | `spotify track id` | `telegram audio id`
### users csv columns
`unique user id` | `last use date and time`

## TO-DO: bugs to fix & features to add
- [x] ~fix caption so it will be shown for repetitive tracks~
- [x] ~some musics metadata is not shown~
- [x] ~only 1 single user can use the bot and it can't multitask~
- [x] ~searching in database algorithm isn't fast and efficient~
- [x] ~Download playlists with more thatn 100 songs~
- [ ] find a clean way to give access to database to next bot maintainers
- [ ] merge database of all spotify downloaders together
- [x] ~showing message to user when link from other services like deezer is sent.~
- [ ] support searching name of song by user
- [ ] find a way to shorten database (audio IDs are very long)
- [ ] if all track_ids that a user wants already exists bypass normall routine and send all of them to him
- [ ] implement `fcntl.flock`
- [ ] handle blocked by user link
- [ ] manage too threads bug
- [x] ~regex should handle both http and https~

## support and donate
If you find my works useful you can give me energy with coffee☕️:
- https://www.coffeete.ir/arashnm80 (﷼)
- https://www.buymeacoffee.com/Arashnm80 (dollar)
