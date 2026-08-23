import os
import sys
import time
import html
import logging
import traceback
import requests
from logging.handlers import RotatingFileHandler

from variables import log_bot_url, log_channel_id, queue_log_flush_tracks, queue_log_flush_seconds

# Telegram channel is a short human summary. Full detail goes to logs/*.log.

_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)


def _log_filename():
    argv = " ".join(sys.argv)
    if "spotseek_queue_handler" in argv:
        return "queue_handler.log"
    if "uvicorn" in argv or "spotseek:app" in argv:
        return "bot.log"
    return "spotseek.log"


def _build_logger():
    logger = logging.getLogger("spotseek")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(process)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = RotatingFileHandler(
        os.path.join(_LOG_DIR, _log_filename()),
        maxBytes=10 * 1024 * 1024,
        backupCount=14,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.propagate = False
    return logger


file_logger = _build_logger()


def log(log_message):
    text = str(log_message)
    print(50 * "-", text)
    file_logger.info(text)


def log_exception(log_message, err=None):
    text = str(log_message)
    if err is not None:
        text = f"{text}\n{err}\n{traceback.format_exc()}"
    else:
        text = f"{text}\n{traceback.format_exc()}"
    print(50 * "-", text)
    file_logger.error(text)


def _esc(text):
    return html.escape(str(text), quote=False)


def _plain_to_html(text):
    lines = [_esc(line) if line else "" for line in str(text).split("\n")]
    return "<p>" + "<br>".join(lines) + "</p>"


def _legacy_html(text):
    first, sep, rest = str(text).partition("\n")
    body = f"<b>{_esc(first)}</b>"
    if sep:
        rest = rest if len(rest) <= 3500 else rest[:3500] + "\n…"
        body += f"\n<pre>{_esc(rest)}</pre>"
    return body


def _post_log_api(method, payload, as_json=True):
    url = log_bot_url + method
    for _ in range(3):
        if as_json:
            r = requests.post(url, json=payload, timeout=20)
        else:
            r = requests.post(url, data=payload, timeout=20)
        if r.status_code == 200:
            return r
        if r.status_code == 429:
            wait = 5
            try:
                wait = int(r.json().get("parameters", {}).get("retry_after", wait))
            except Exception:
                pass
            time.sleep(min(wait, 60) + 1)
            continue
        return r
    return r


def send_log_channel(text, html_body=None):
    """One Telegram message to the log channel. Never raises; waits on 429."""
    print(50 * "-", text)
    file_logger.info("telegram: %s", text)
    rich_html = html_body or _plain_to_html(text)
    try:
        rich = _post_log_api(
            "sendRichMessage",
            {"chat_id": log_channel_id, "rich_message": {"html": rich_html}},
        )
        if rich is not None and rich.status_code == 200:
            return
        # Classic sendMessage: no tables/headings. Bold title + expandable-style pre.
        fallback = _post_log_api(
            "sendMessage",
            {
                "chat_id": log_channel_id,
                "text": _legacy_html(text),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        if fallback is not None and fallback.status_code == 200:
            if rich is not None and rich.status_code != 200:
                file_logger.debug(
                    "sendRichMessage unavailable (%s %s); used HTML sendMessage",
                    rich.status_code,
                    (rich.text or "")[:400],
                )
            return
        plain = _post_log_api(
            "sendMessage",
            {"chat_id": log_channel_id, "text": text},
            as_json=False,
        )
        if plain is None or plain.status_code != 200:
            err = plain if plain is not None else rich
            status = err.status_code if err is not None else "?"
            body = err.text if err is not None else ""
            print("Error in registering log:", status, body)
            file_logger.error("telegram log failed: %s %s", status, body)
    except Exception as e:
        print("Error in registering log:", e)
        file_logger.error("telegram log failed: %s", e)


_stats = {
    "ok": 0,
    "no_mp3": 0,
    "too_big": 0,
    "error": 0,
    "spotdl_fail": 0,
    "skipped_in_db": 0,
}
_attempt_samples = []  # (label, times, track_id)
_queue_unique = 0
_queue_waiting = 0
_since = time.time()


def set_queue_depth(unique, waiting):
    """Pending unique tracks and total requests (with repeats) still in the queue."""
    global _queue_unique, _queue_waiting
    _queue_unique = unique
    _queue_waiting = waiting


def queue_depth_label():
    return f"{_queue_waiting} waiting ({_queue_unique} unique)"


def _download_events():
    return (
        _stats["ok"]
        + _stats["no_mp3"]
        + _stats["too_big"]
        + _stats["error"]
        + _stats["spotdl_fail"]
    )


def queue_note(kind, n=1, track_id=None, detail=None, repeats=None):
    """Count a queue event. Telegram is sent only when the batch is full or stale."""
    if kind not in _stats:
        kind = "error"
    _stats[kind] += n
    if track_id and len(_attempt_samples) < 50:
        times = repeats if repeats is not None else 1
        label = detail or kind
        _attempt_samples.append((label, times, track_id))
    attempted = _download_events()
    aged = (time.time() - _since) >= queue_log_flush_seconds
    if attempted >= queue_log_flush_tracks or (
        aged and (attempted > 0 or _stats["skipped_in_db"] > 0)
    ):
        queue_flush()


def _fmt_n(n):
    return f"{int(n):,}"


def _queue_summary_html(minutes, attempted, fail, reason):
    rows = [
        ("Waiting", _fmt_n(_queue_waiting)),
        ("Unique tracks", _fmt_n(_queue_unique)),
        ("Tried", _fmt_n(attempted)),
        ("OK", _fmt_n(_stats["ok"])),
        ("Failed", _fmt_n(fail)),
        ("No mp3", _fmt_n(_stats["no_mp3"])),
        ("Too big", _fmt_n(_stats["too_big"])),
        ("Error", _fmt_n(_stats["error"])),
        ("spotdl", _fmt_n(_stats["spotdl_fail"])),
        ("Already in DB", _fmt_n(_stats["skipped_in_db"])),
    ]
    table_rows = "".join(
        f"<tr><td>{_esc(name)}</td><td><b>{_esc(value)}</b></td></tr>"
        for name, value in rows
    )
    parts = [
        "<h2>Queue handler</h2>",
        f"<p><i>Tried in ~{minutes} min</i></p>",
        "<table>",
        "<tr><th>Metric</th><th>Value</th></tr>",
        table_rows,
        "</table>",
    ]
    if _attempt_samples:
        items = "".join(
            f"<li><code>{_esc(label)}</code> ×{_esc(times)} "
            f"<code>{_esc(track_id)}</code></li>"
            for label, times, track_id in _attempt_samples
        )
        parts.append(
            f"<details><summary>Tracks ({len(_attempt_samples)})</summary>"
            f"<ul>{items}</ul></details>"
        )
    if reason:
        parts.append(f"<blockquote>{_esc(reason)}</blockquote>")
    return "".join(parts)


def queue_flush(reason=None):
    global _since
    attempted = _download_events()
    if attempted == 0 and _stats["skipped_in_db"] == 0 and not reason:
        return
    minutes = max(int((time.time() - _since) / 60), 1)
    fail = attempted - _stats["ok"]
    sample_lines = [
        f"{label}  ×{times}  {track_id}"
        for label, times, track_id in _attempt_samples
    ]
    lines = [
        "queue handler",
        f"queue: {_queue_waiting} waiting ({_queue_unique} unique)",
        f"{attempted} tried in ~{minutes} min  |  ok {_stats['ok']}  |  fail {fail}",
        f"no mp3: {_stats['no_mp3']}  too big: {_stats['too_big']}  error: {_stats['error']}  spotdl: {_stats['spotdl_fail']}",
        f"already in db (skipped): {_stats['skipped_in_db']}",
    ]
    if sample_lines:
        lines.append("tracks:\n" + "\n".join(sample_lines))
    if reason:
        lines.append(reason)
    send_log_channel(
        "\n".join(lines),
        html_body=_queue_summary_html(minutes, attempted, fail, reason),
    )
    for k in _stats:
        _stats[k] = 0
    _attempt_samples.clear()
    _since = time.time()
