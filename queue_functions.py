from my_imports import *
from spotify import get_track_image
import json
import socket

_PROXY_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "proxy_attempts.jsonl")
_STATS_CACHE = (0.0, {})
_EXPLORE_RATE = 0.3


def _exit_country(kind, port):
    if kind == "masque":
        return masque_port_countries.get(port, "??")
    return psiphon_port_countries.get(port, "??")


def _exit_label(kind, port):
    return f"{kind} {_exit_country(kind, port)} :{port}"


def _append_proxy_event(row):
    """One JSON line per attempt so country success can be grepped later."""
    os.makedirs(os.path.dirname(_PROXY_LOG), exist_ok=True)
    row = dict(row)
    row.setdefault("ts", int(time.time()))
    with open(_PROXY_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    global _STATS_CACHE
    _STATS_CACHE = (0.0, {})


def _listening_ports(ports):
    live = []
    for port in ports:
        try:
            with socket.create_connection(("127.0.0.1", port), 0.4):
                live.append(port)
        except OSError:
            continue
    return live


def _listening_psiphon_ports():
    return _listening_ports(psiphon_socks_ports)


def _recent_port_stats(window_s=48 * 3600):
    """First-try ok/fail per port from jsonl. Cached 60s so the loop can learn."""
    global _STATS_CACHE
    now = time.time()
    if now - _STATS_CACHE[0] < 60:
        return _STATS_CACHE[1]
    stats = {}
    cutoff = int(now) - window_s
    try:
        with open(_PROXY_LOG, encoding="utf-8") as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("ts", 0) < cutoff or row.get("attempt") != 1:
                    continue
                port = row.get("port")
                if not port:
                    continue
                ok, fail = stats.get(port, (0, 0))
                if row.get("ok"):
                    ok += 1
                else:
                    fail += 1
                stats[port] = (ok, fail)
    except OSError:
        stats = {}
    _STATS_CACHE = (now, stats)
    return stats


def _score_port(port, stats):
    ok, fail = stats.get(port, (0, 0))
    n = ok + fail
    # Few first-tries: below a proven ~40% exit so ES is not displaced by zeros,
    # above a burned exit so explore-mode can still promote a recovering country.
    if n < 8:
        return 0.25
    return ok / n


def _ranked_ports(live, n, stats, explore=_EXPLORE_RATE):
    if not live or n <= 0:
        return []
    ports = list(live)
    if random.random() < explore:
        random.shuffle(ports)
    else:
        random.shuffle(ports)
        ports.sort(key=lambda p: -_score_port(p, stats))
    return ports[:n]


def _exits_to_try():
    """Psiphon first (scored + explore), then MASQUE. Never the VPS IP."""
    stats = _recent_port_stats()
    psiphon = _ranked_ports(
        _listening_ports(psiphon_socks_ports), psiphon_try_limit, stats
    )
    masque = _ranked_ports(
        _listening_ports(masque_socks_ports), masque_try_limit, stats, explore=0.5
    )
    return [("psiphon", p) for p in psiphon] + [("masque", p) for p in masque]


def _detail_for(track_id, used_proxy, tried_proxy):
    if track_id in used_proxy:
        return _exit_label(*used_proxy[track_id])
    labels = tried_proxy.get(track_id) or []
    if labels:
        return "failed after " + ", ".join(labels)
    return "no live proxy"


def _proxychains_conf(port):
    path = os.path.join("/tmp", f"spotseek-exit-{port}.conf")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(
            "strict_chain\n"
            "proxy_dns\n"
            "[ProxyList]\n"
            f"socks5 127.0.0.1 {port}\n"
        )
    return path


def _folder_has_mp3(folder):
    if not os.path.isdir(folder):
        return False
    return any(name.lower().endswith(".mp3") for name in os.listdir(folder))

def list_of_files_in_a_folder(folder_path):
    try:
        file_names = os.listdir(folder_path)
        # Filter out '.gitkeep'
        file_names = [name for name in file_names if name != '.gitkeep']
        # Sort the list of file names by creation time
        file_names.sort(key=lambda filename: os.path.getctime(os.path.join(folder_path, filename)))
        return file_names
    except FileNotFoundError:
        print(f"Folder {folder_path} not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

# One item per line, add without duplicates
def append_list_to_file(my_list, file_path):
    # Lire les lignes existantes (sans les sauts de ligne)
    try:
        with open(file_path, 'r') as file:
            existing_items = set(line.strip() for line in file)
    except FileNotFoundError:
        existing_items = set()

    # Ouvrir en mode ajout uniquement les éléments non existants
    with open(file_path, 'a') as file:
        for item in my_list:
            if item not in existing_items:
                file.write(item + '\n')

# write list to file, overwriting the file if it exists
def write_list_to_file(my_list, file_path):
    # creates it if it doesn't exist
    with open(file_path, 'w') as file:
        for item in my_list:
            file.write(item + '\n')

# one item per line
def read_list_from_file(file_path):
    # Initialize an empty list to store the lines
    lines = []
    # Open the file in read mode
    with open(file_path, 'r') as file:
        for line in file:
            # Use rstrip() to remove the newline character
            line = line.rstrip()
            lines.append(line)
    return lines


def download_tracks(track_ids_list, request_counts=None):
    try:
        global current_proxy_index
        global queue_handler_sleep_timer
        request_counts = request_counts or {}
        used_proxy = {}
        tried_proxy = {}

        def repeats_of(track_id):
            return request_counts.get(track_id, 1)

        def note(kind, track_id=None, n=1, detail=None):
            times = repeats_of(track_id) if track_id else None
            queue_note(kind, n=n, track_id=track_id, detail=detail, repeats=times)
            record_event(f"dl_{kind}", track_id=track_id, n=n)
            if track_id and kind in ("ok", "no_mp3", "too_big", "error", "spotdl_fail", "skipped_in_db"):
                dropped = remove_track_from_all_queues(track_id)
                if kind != "ok" and kind != "skipped_in_db":
                    log(f"dropped {track_id} from {dropped} queue rows after {kind}")

        log(
            f"sleep timer: {queue_handler_sleep_timer}\n"
            f"queue: {queue_depth_label()}"
        )
        time.sleep(queue_handler_sleep_timer)  # small delay between batches for yt-dlp

        # Keep ~/.spotdl and yt-dlp caches. Wiping them forced a 5s secrets timeout
        # to code.thetadev.de on every batch and slowed matching.

        # remove files and folders in directory
        clear_files(directory)

        for track_id in track_ids_list[:]:  # copie de la liste
            # new method based on sqlite3 db
            telegram_audio_id = get_telegram_audio_id(track_id)

            # if item exists in db
            if telegram_audio_id is not None:
                log(f"track {track_id} ×{repeats_of(track_id)} exists in db now. skip. | queue: {queue_depth_label()}")
                note("skipped_in_db", track_id=track_id)
                track_ids_list.remove(track_id)

        # if list became empty
        if not track_ids_list:
            log("all tracks already exist in db. skip.")
            return "allTracksExistInDb"

        track_lines = "\n".join(
            f"×{repeats_of(track_id)}  {track_id}" for track_id in track_ids_list
        )
        log(f"current_proxy_index: {current_proxy_index}\n\nqueue: {queue_depth_label()}\n\ntracks to download:\n\n{track_lines}")

        # Kill any existing spotdl processes before starting a new download
        try:
            subprocess.run(['pkill', '-9', '-f', 'spotdl'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log(f"Failed to kill existing spotdl processes: {e}")

        try:       
            print("start downloading tracks via spotdl")

            # experimental - pass spotify api key to spotdl
            # random spotify app from list to avoid rate limiting
            random.seed(time.time())
            spotify_app = random.choice(spotify_apps_list)
            spotify_client_id = spotify_app[0]
            spotify_client_secret = spotify_app[1]

            # One local SOCKS per attempt so this VPS IP is never the client.
            # Rank by first-try success, explore other countries ~30% of the time.
            if not _exits_to_try():
                raise RuntimeError("no local SOCKS listening (refusing VPS IP)")
            for track_id in track_ids_list:
                track_folder = os.path.join(directory, track_id)
                tries = _exits_to_try()
                log(
                    f"proxy tries for {track_id}: "
                    + ", ".join(_exit_label(k, p) for k, p in tries)
                )
                tried_proxy[track_id] = []
                for attempt, (kind, port) in enumerate(tries, 1):
                    conf = _proxychains_conf(port)
                    command = [
                        "proxychains4",
                        "-f",
                        conf,
                        spotdl_bin,
                        "--audio",
                        spotdl_audio_provider,
                        "--lyrics",
                        "--skip-album-art",
                        "--bitrate",
                        "320k",
                        "--output",
                        "{track-id}/",
                        "download",
                        f"https://open.spotify.com/track/{track_id}",
                    ]
                    label = _exit_label(kind, port)
                    tried_proxy[track_id].append(label)
                    log(f"trying {label} for {track_id} ({attempt}/{len(tries)})")
                    print("download command:\n\n", command)
                    started = time.monotonic()
                    subprocess.run(
                        command,
                        cwd=directory,
                        env=get_spotdl_download_env(),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=300,
                    )
                    elapsed = round(time.monotonic() - started, 1)
                    ok = _folder_has_mp3(track_folder)
                    _append_proxy_event(
                        {
                            "track_id": track_id,
                            "kind": kind,
                            "port": port,
                            "country": _exit_country(kind, port),
                            "proxy": f"socks5://127.0.0.1:{port}",
                            "ok": ok,
                            "elapsed_s": elapsed,
                            "attempt": attempt,
                            "tries": len(tries),
                        }
                    )
                    if ok:
                        used_proxy[track_id] = (kind, port)
                        log(f"ok {label} for {track_id} in {elapsed}s")
                        break
                    log(f"fail {label} for {track_id} in {elapsed}s")
                else:
                    tried = ", ".join(tried_proxy[track_id])
                    log(f"spotdl no mp3 for {track_id} after {tried}")
        except Exception as e:
            log(bot_name + " error in spotdl download")
            for track_id in track_ids_list:
                note("spotdl_fail", track_id=track_id, detail="spotdl exception")
            return "errorInSpotdlDownload"

        at_least_one_track_downloaded = False # sometimes jumps to next pack without downloading anything and giving any error

        try:
            print("start downloading cover images")
            # Listing folders in the output directory - each folder name is track_id of one song
            folders = [name for name in os.listdir(directory) if os.path.isdir(os.path.join(directory, name))]
            print("folders (which are track ids):", folders)
            # S3 disabled: bucket deleted (cost). Restore this client + put_object if needed.
            # s3_client = boto3.client(
            #     's3',
            #     endpoint_url=S3_ENDPOINT,
            #     aws_access_key_id=S3_ACCESS_KEY,
            #     aws_secret_access_key=S3_SECRET_KEY
            # )
            for track_id in folders:
                # check if folder name is in the track_ids_list
                # opposite of that should never happen
                # but look likes it happens rarely - maybe is a problem from spotdl side
                if track_id not in track_ids_list:
                    log(f"folder {track_id} is wrong and doesn't exist in track_ids_list")
                    return "unmatchedFolderWithTrackIdsList"
                print("track_id based on folder:", track_id)
                track_folder_path = f"{directory}{track_id}/"
                print("track folder path:", track_folder_path)
                try:
                    # download cover image
                    image_url = get_track_image(track_id)
                    print("downloading image from url:", image_url)
                    cover_exit = used_proxy.get(track_id)
                    if not cover_exit:
                        leftover = _listening_psiphon_ports() or _listening_ports(masque_socks_ports)
                        cover_exit = (
                            ("psiphon" if leftover[0] in psiphon_socks_ports else "masque", leftover[0])
                            if leftover
                            else None
                        )
                    if cover_exit:
                        cover_kind, cover_port = cover_exit
                        log(f"cover wget via {_exit_label(cover_kind, cover_port)} for {track_id}")
                        cover_cmd = [
                            "proxychains4",
                            "-f",
                            _proxychains_conf(cover_port),
                            "wget",
                            "-O",
                            "cover.jpg",
                            "-o",
                            "/dev/null",
                            image_url,
                        ]
                        cover_run = subprocess.run(
                            cover_cmd,
                            cwd=track_folder_path,
                            timeout=300,
                        )
                        if cover_run.returncode != 0:
                            raise RuntimeError(
                                f"cover wget failed (code {cover_run.returncode})"
                            )
                    else:
                        raise RuntimeError("cover wget skipped: no live proxy")
                    cover_path = os.path.join(track_folder_path, "cover.jpg")
                    if not is_usable_cover(cover_path):
                        raise RuntimeError("cover file missing or not an image")
                    # get mp3 file name from folder
                    try:
                        mp3_file = get_single_mp3(track_folder_path)
                    except Exception as e:
                        proxy_txt = _detail_for(track_id, used_proxy, tried_proxy)
                        log(bot_name + f" log:\n\nproxy: {proxy_txt}\nsleep_timer: {queue_handler_sleep_timer}\n\n🛑 error in get_single_mp3() for track:\n" + track_id + f" ×{repeats_of(track_id)}\n\nerror:\n" + str(e) + f"\nqueue: {queue_depth_label()}")
                        note("no_mp3", track_id=track_id, detail=proxy_txt)
                        continue
                    proxy_txt = _detail_for(track_id, used_proxy, tried_proxy)
                    log(f"proxy: {proxy_txt}\n\n🔵 downloaded ×{repeats_of(track_id)}  {track_id}\n{mp3_file}\nqueue: {queue_depth_label()}")
                    # change cover image
                    change_cover_image(mp3_file, "cover.jpg", track_folder_path)
                    # check file size because of telegram 50MB limit
                    audio_path = os.path.join(track_folder_path, mp3_file)
                    audio = open(audio_path, 'rb')
                    file_size = os.fstat(audio.fileno()).st_size
                    if file_size > 50_000_000:
                        log(bot_name + f" log:\n🛑 too big mp3 file error ×{repeats_of(track_id)}  {track_id}\nproxy: {proxy_txt}\nqueue: {queue_depth_label()}")
                        note("too_big", track_id=track_id, detail=proxy_txt)
                        audio.close()
                        continue
                    # get track metadata to be shown in telegram
                    track_duration = get_track_duration(audio_path)
                    track_artist = get_artist_name_from_track(audio_path)
                    track_title = get_track_title(audio_path)
                    thumb_path = os.path.join(track_folder_path, "cover_low.jpg")
                    if not is_usable_cover(thumb_path):
                        raise RuntimeError("cover thumbnail missing after embed")
                    thumb_image = open(thumb_path, 'rb')
                    # send audio to database_channel:
                    audio_message = bot.send_audio(SP11_CHANNEL_ID, audio, thumb=thumb_image, caption=track_id, duration=track_duration, performer=track_artist, title=track_title)
                    # add file to database - new method based on sqlite3 db
                    # add_or_update_track_info(track_id, audio_message.audio.file_id) # before new db functions system of backup
                    add_or_update_track_info(track_id, audio_message.audio.file_id, SP11_CHANNEL_ID, audio_message.message_id, download_method=spotdl_audio_provider) # after new db functions system of backup
                    # S3 disabled (bucket deleted). Was: put_object music/{track_id}.mp3 then update_s3_status(track_id, 1)
                    # try:
                    #     s3_key = f"{track_id}.mp3"
                    #     with open(audio_path, 'rb') as audio_file:
                    #         s3_client.put_object(
                    #             Bucket=S3_BUCKET_NAME,
                    #             Key=s3_key,
                    #             Body=audio_file,
                    #             ContentType='audio/mpeg'
                    #         )
                    #     update_s3_status(track_id, 1)
                    # except Exception as e:
                    #     log(bot_name + f" log:\nS3 upload failed for {track_id} (kept in db/telegram):\n{e}")
                    audio.close()
                    thumb_image.close()
                    at_least_one_track_downloaded = True
                    note("ok", track_id=track_id, detail=proxy_txt)
                except Exception as e:
                    log(bot_name + f"\nerror processing track {track_id} ×{repeats_of(track_id)}:\n" + str(e) + f"\nqueue: {queue_depth_label()}")
                    note("error", track_id=track_id, detail=str(e)[:80])
                    continue
            # spotdl created no folder → same as no mp3
            folder_set = set(folders)
            for track_id in track_ids_list:
                if track_id not in folder_set:
                    log(
                        f"no folder for {track_id} ×{repeats_of(track_id)} "
                        f"| queue: {queue_depth_label()}"
                    )
                    note(
                        "no_mp3",
                        track_id=track_id,
                        detail=_detail_for(track_id, used_proxy, tried_proxy),
                    )
        except Exception as e:
            log(bot_name + "\nerror in processing downloaded tracks:\n" + str(e))
            return "errorInProcessingDownloadedTracks"

        # if at_least_one_track_downloaded and queue_handler_sleep_timer > 3:
        #     queue_handler_sleep_timer -= 0 # 1
        # elif (not at_least_one_track_downloaded) and queue_handler_sleep_timer <= 595:
        #     queue_handler_sleep_timer += 0 # 5
        if not at_least_one_track_downloaded:
            current_proxy_index = (current_proxy_index + 1) % len(socks_proxies)
            log(f"current proxy changed to index: {current_proxy_index}")


        return "successfulDownload✅"

    except Exception as e:
        log(bot_name + " log:\n🛑 An error in download_tracks():\n" + str(e))
        return "downloadTracksError"