from queue_functions import *
import time

# Popular-first, then one-track-per-user round-robin.
# Queue lives in sqlite (download_queue). Re-checked every batch so a new
# multi-request track pauses singles and is downloaded before round-robin continues.


def popular_track_ids(counts):
    """Unique track ids requested by more than one user, highest count first."""
    return [
        track_id
        for track_id, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if count > 1
    ]


def download_round_robin_batch(picks, request_counts):
    """Download one-per-user picks, or skip this batch if popular tracks appeared."""
    if popular_track_ids(pending_request_counts()):
        log("⏸ pause round-robin; some tracks now have more than one request")
        return False
    download_tracks(
        [track_id for _user_id, track_id in picks],
        request_counts=request_counts,
    )
    return True


if __name__ == "__main__":
    try:
        # emperimental - remove old spotdl exe and download it again to see if affects limits
        setup_spotdl_executable()
        create_database()
        leftover = migrate_received_links_files_into_db()
        if leftover.get("files"):
            log(
                "imported leftover text queues: "
                f"{leftover['files']} files, {leftover['rows_added']} new rows"
            )
        send_log_channel(
            "queue handler started",
            html_body="<h2>Queue handler</h2><p>Started.</p>",
        )
        queue_mode = None

        while True:
            time.sleep(1)  # delay for each complete loop of queue handler

            counts = pending_request_counts()
            waiting = sum(counts.values())
            unique = len(counts)
            users_waiting = pending_queue_user_count()
            set_queue_depth(unique, waiting)
            log(
                f"🏁 #queue_handler_started\n"
                f"📂 {users_waiting} users  |  queue: {waiting} waiting ({unique} unique)"
            )

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
                    f"queue: {waiting} waiting ({unique} unique)\n"
                    + "\n".join(f"×{counts[track_id]}  {track_id}" for track_id in batch)
                )
                download_tracks(batch, request_counts=counts)
                continue

            if queue_mode != "round_robin":
                log("👤 queue mode: round-robin (one track per user)")
                queue_mode = "round_robin"

            picks = []
            paused_for_popular = False
            for user_id, track_id in next_round_robin_picks():
                picks.append((user_id, track_id))
                if len(picks) >= simultaneous_downloads:
                    if not download_round_robin_batch(picks, counts):
                        paused_for_popular = True
                        picks = []
                        break
                    picks = []

            if paused_for_popular:
                continue

            if picks:
                download_round_robin_batch(picks, counts)

    except Exception as e:
        log(bot_name + " log:\n🛑 An error in queue handler: " + str(e))
        queue_flush(reason=f"🛑 queue handler stopped:\n{e}")
