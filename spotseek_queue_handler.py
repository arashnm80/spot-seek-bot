from queue_functions import *
from collections import Counter
import time
import os

# Popular-first, then the original one-track-per-user round-robin.
# Re-checked every batch so a new multi-request track pauses singles
# and is downloaded before round-robin continues.


def pending_request_counts():
    """Users waiting for each track that is not in the DB yet."""
    counts = Counter()
    files = list_of_files_in_a_folder(received_links_folder_path) or []
    for user_id in files:
        file_path = received_links_folder_path + "/" + user_id
        try:
            tracks = read_list_from_file(file_path)
        except Exception:
            continue
        for track_id in dict.fromkeys(tracks):
            counts[track_id] += 1
    for track_id in list(counts):
        if get_telegram_audio_id(track_id) is not None:
            del counts[track_id]
    return counts


def popular_track_ids(counts):
    """Unique track ids requested by more than one user, highest count first."""
    return [
        track_id
        for track_id, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if count > 1
    ]


def restore_picked_tracks(picks):
    """Put round-robin picks back at the front of each user file (pause for popular)."""
    for user_id, track_id in reversed(picks):
        file_path = received_links_folder_path + "/" + user_id
        if os.path.exists(file_path):
            tracks = read_list_from_file(file_path)
            if track_id not in tracks:
                tracks.insert(0, track_id)
            write_list_to_file(tracks, file_path)
        else:
            write_list_to_file([track_id], file_path)


def download_round_robin_batch(picks):
    """Download one-per-user picks, or put them back if popular tracks appeared."""
    if popular_track_ids(pending_request_counts()):
        log("⏸ pause round-robin; some tracks now have more than one request")
        restore_picked_tracks(picks)
        return False
    download_tracks([track_id for _user_id, track_id in picks])
    return True


if __name__ == "__main__":
    try:
        # emperimental - remove old spotdl exe and download it again to see if affects limits
        setup_spotdl_executable()
        create_database()
        send_log_channel("queue handler started")
        queue_mode = None

        while True:
            time.sleep(1)  # delay for each complete loop of queue handler

            files = list_of_files_in_a_folder(received_links_folder_path) or []
            log(f"🏁 #queue_handler_started\n📂 {len(files)} files in the folder.")

            counts = pending_request_counts()
            popular_ids = popular_track_ids(counts)

            if popular_ids:
                if queue_mode != "popular":
                    log(
                        "🔥 queue mode: popular-first "
                        f"({len(popular_ids)} track(s) requested by more than one user)"
                    )
                    queue_mode = "popular"
                batch = popular_ids[:simultaneous_downloads]
                log(
                    "🔥 downloading most-requested tracks:\n"
                    + "\n".join(f"{counts[track_id]} users → {track_id}" for track_id in batch)
                )
                download_tracks(batch)
                continue

            if queue_mode != "round_robin":
                log("👤 queue mode: round-robin (one track per user)")
                queue_mode = "round_robin"

            # file names are user IDs — one pending track each, oldest files first
            picks = []
            paused_for_popular = False
            for user_id in files:
                file_path = received_links_folder_path + "/" + user_id
                tracks = read_list_from_file(file_path)

                while tracks:
                    # extract the first track ID from the list
                    track_id = tracks.pop(0)
                    # check if it's a new track or exists in db now
                    telegram_audio_id = get_telegram_audio_id(track_id)
                    if telegram_audio_id is not None:
                        log(f"🤸‍♀️ track {track_id} exists in db now. skip.")
                        queue_note("skipped_in_db")
                        continue
                    else:
                        picks.append((user_id, track_id))
                        break

                # if there are still some tracks left for this user
                # write the remaining tracks back to the file
                if tracks:
                    # todo: it's bug is that if meanwhile new tracks are appended to end of it, they will be overwritten
                    # todo: although it is not going to be very often
                    # write left items in tracks back to file
                    write_list_to_file(tracks, file_path)
                else:
                    # tracks list has become empty and we can delete related user file
                    os.remove(file_path)

                # download if there are enough tracks
                if len(picks) >= simultaneous_downloads:
                    if not download_round_robin_batch(picks):
                        paused_for_popular = True
                        picks = []
                        break
                    picks = []

            if paused_for_popular:
                continue

            # after the loop:
            # if there are not enough tracks but still some left
            if picks:
                download_round_robin_batch(picks)
                # if popular appeared, picks were put back; next loop downloads them first

    except Exception as e:
        log(bot_name + " log:\n🛑 An error in queue handler: " + str(e))
        queue_flush(reason=f"🛑 queue handler stopped:\n{e}")
