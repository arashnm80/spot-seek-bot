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
- download spotdl executable file, rename it to `spotdl` put it beside `spotseek.py` file
- install necessary python modules `(os, pandas, telebot, re, threading, csv, spotipy, subprocess, requests, datetime)` and `ffmpeg` software
- run it with `nohup python3 spotseek.py > /dev/null 2>&1 &`

## status
This is currently the beta version of the bot and it's under test. If you found a bug or had any feedbacks I'll be glad to hear from you. Also if you are a programmer you are welcome to improve the project or use it for yourself.

## csv files columns guide
### database csv columns
`date and time added` | `spotify track id` | `telegram audio id`
### users csv columns
`unique user id` | `last use date and time`

## known bugs and problems so for that should be fixed later
- some musics duration or size is not shown
- only 1 single user can use the bot and it can't multitask
- downloading all songs of an artist is not available
- searching in database algorithm isn't fast and efficient
- caption is not always visible

## support and donate
If you find my works useful you can give me energy with coffee☕️:
- https://www.coffeete.ir/arashnm80 (﷼)
- https://www.buymeacoffee.com/Arashnm80 (dollar)
