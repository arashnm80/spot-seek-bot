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
- download spotdl executable file, rename it to `spotdl` put it beside `spotseek.py` file
- install necessary python modules `(os, pandas, telebot, re, threading, csv, spotipy, subprocess, requests, datetime)` and `ffmpeg` software
  - `ffmpeg`: `apt install ffmpeg`
  - `telebot`: `pip install telebot`
  - `spotipy`: `pip install spotipy`
  - `pandas`: `pip install pandas`
- run it with `nohup python3 spotseek.py > /dev/null 2>&1 &` or `nohup python3 spotseek.py &`
- I didn't cleared my data in `db.csv`, If you are starting the whole infrastructure by yourself remove everything from it except first row which are the headers

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

## known bugs and problems so for that could be fixed later
- some musics duration or size is not shown
- only 1 single user can use the bot and it can't multitask
- downloading all songs of an artist is not available
- searching in database algorithm isn't fast and efficient
- caption is not always visible

## support and donate
If you find my works useful you can give me energy with coffee☕️:
- https://www.coffeete.ir/arashnm80 (﷼)
- https://www.buymeacoffee.com/Arashnm80 (dollar)
