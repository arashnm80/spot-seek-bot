# telegram spotify downloader bot: [@SpotSeekBot](https://t.me/SpotSeekBot)

## how to use as the client
Send bot a link from spotify and it'll download it for you.
  - It can be a track link like this:
https://open.spotify.com/track/734dz1YaFITwawPpM25fSt
  - Or an album like this:
https://open.spotify.com/album/0Lg1uZvI312TPqxNWShFXL
  - Or a playlist like this:
https://open.spotify.com/playlist/37i9dQZF1DWX4UlFW6EJPs

## how to deploy as the developer
- install python and pip `apt install python3-pip`
- clone the repo
- set required environment variables, tokens and api keys. you can see them in `variables.py` file.
- download spotdl executable file, rename it to `spotdl` put it beside `spotseek.py` file. you can download linux version from https://github.com/spotDL/spotify-downloader/releases with a command like this:
```
wget -O spotdl https://github.com/spotDL/spotify-downloader/releases/download/v4.1.3/spotdl-4.1.3-linux
```
- then make spotdl executable:
```
chmod +x spotdl
```
- install necessary python modules `(os, pandas, telebot, re, threading, csv, spotipy, subprocess, requests, datetime, pydub, mutagen, time)` and `ffmpeg` software
  - `ffmpeg`: `apt install ffmpeg`
  - `telebot`: `pip install telebot`
  - `spotipy`: `pip install spotipy`
  - `pandas`: `pip install pandas`
  - `pydub`: `pip install pydub`
  - `mutagen`: `pip install mutagen`
- run it with `nohup python3 spotseek.py > /dev/null 2>&1 &` or `nohup python3 spotseek.py &`
- I might haven't cleared datas in `db.csv`, If you are starting the whole infrastructure by yourself remove everything from it except first row which are the headers

## technical info about how this bot works
- When you send a spotify link to the bot it searches through its database and if it's the first time it sees this link it will download it with spotdl but if it has done it before it saves time by using previously downloaded files from database.
- I've set 30 seconds waiting time for 2 requests in a row from 1 user so it won't be spammed
- I've set log channel and database channel for the bot. It stores every downloaded song in database channel and use it as a storage and prints logs from everything to log channel (errors, user messags, ...)
- We use spotify api to get tracks from a valid link so you should sign up in https://developer.spotify.com/ and get your own token.

## status
I've created This bot to download musics by their link from spotify (single track, album or playlist). It is the first beta test version and there are many bugs to fix and features to add. If you used it I'll be happy to hear about bugs or any other feedbacks.

Also if you are a programmer you are welcome to contribute and improve the project or use it for yourself.

This bot is not a new idea and many others have done this before, So I'm not sure how much it is worth to spend time on. It depends on many factors like my time, server costs and your feedbacks, so for now let's look at it just as a fun weekend project.😉✌️

Here are some similar telegram bots by others:
- [Spotdlrobot](https://t.me/Spotdlrobot) (by Iranian programmer, [aliilapro](https://github.com/ALIILAPRO))
- [DeezerMusicBot](https://t.me/DeezerMusicBot)
- [RegaSpotify_Bot](https://t.me/RegaSpotify_Bot)
- [MusicsHunterbot](https://t.me/MusicsHunterbot)

## csv files columns guide
### database csv columns
`date and time added` | `spotify track id` | `telegram audio id`
### users csv columns
`unique user id` | `last use date and time`

## TO-DO: bugs to fix & features to add
- [x] ~fix caption so it will be shown for repetitive tracks~
- [x] ~some musics metadata is not shown~
- [ ] only 1 single user can use the bot and it can't multitask
- [ ] downloading all songs of an artist is not available
- [ ] searching in database algorithm isn't fast and efficient
- [x] ~Bot only downloads first 100 tracks of playlist~

## support and donate
If you find my works useful you can give me energy with coffee☕️:
- https://www.coffeete.ir/arashnm80 (﷼)
- https://www.buymeacoffee.com/Arashnm80 (dollar)
