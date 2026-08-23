import time
import requests

from variables import log_bot_url, log_channel_id, queue_log_flush_tracks, queue_log_flush_seconds

# log() stays print-only. Per-event Telegram messages used to 429 the log channel.
# QueueHandler sends batched summaries via send_log_channel / queue_note.


def log(log_message):
    print(50 * "-", log_message)


def send_log_channel(text):
    """One Telegram message to the log channel. Never raises; waits on 429."""
    print(50 * "-", text)
    try:
        payload = {"chat_id": log_channel_id, "text": text}
        for _ in range(3):
            r = requests.post(log_bot_url + "sendMessage", data=payload, timeout=20)
            if r.status_code == 200:
                return
            if r.status_code == 429:
                wait = 5
                try:
                    wait = int(r.json().get("parameters", {}).get("retry_after", wait))
                except Exception:
                    pass
                time.sleep(min(wait, 60) + 1)
                continue
            print("Error in registering log:", r.status_code, r.text)
            return
    except Exception as e:
        print("Error in registering log:", e)


_stats = {
    "ok": 0,
    "no_mp3": 0,
    "too_big": 0,
    "error": 0,
    "spotdl_fail": 0,
    "skipped_in_db": 0,
}
_fail_samples = []
_since = time.time()


def _download_events():
    return (
        _stats["ok"]
        + _stats["no_mp3"]
        + _stats["too_big"]
        + _stats["error"]
        + _stats["spotdl_fail"]
    )


def queue_note(kind, n=1, track_id=None, detail=None):
    """Count a queue event. Telegram is sent only when the batch is full or stale."""
    if kind not in _stats:
        kind = "error"
    _stats[kind] += n
    if track_id and kind != "ok" and kind != "skipped_in_db" and len(_fail_samples) < 8:
        label = detail or kind
        _fail_samples.append(f"{track_id} ({label})")
    attempted = _download_events()
    aged = (time.time() - _since) >= queue_log_flush_seconds
    if attempted >= queue_log_flush_tracks or (
        aged and (attempted > 0 or _stats["skipped_in_db"] > 0)
    ):
        queue_flush()


def queue_flush(reason=None):
    global _since
    attempted = _download_events()
    if attempted == 0 and _stats["skipped_in_db"] == 0 and not reason:
        return
    minutes = max(int((time.time() - _since) / 60), 1)
    lines = [
        "QueueHandler",
        f"{attempted} tried in ~{minutes} min  |  ok {_stats['ok']}  |  fail {attempted - _stats['ok']}",
        f"no mp3: {_stats['no_mp3']}  too big: {_stats['too_big']}  error: {_stats['error']}  spotdl: {_stats['spotdl_fail']}",
        f"already in db (skipped): {_stats['skipped_in_db']}",
    ]
    if _fail_samples:
        lines.append("examples:\n" + "\n".join(_fail_samples))
    if reason:
        lines.append(reason)
    send_log_channel("\n".join(lines))
    for k in _stats:
        _stats[k] = 0
    _fail_samples.clear()
    _since = time.time()
