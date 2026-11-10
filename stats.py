"""Period stats from bot_events. Safe to query for week/month reports."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone

from db_functions import _connect, create_database
from log import file_logger, send_log_channel

_STATS_JSONL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "stats.jsonl")

DL_OK = "dl_ok"
DL_FAIL_KINDS = ("dl_no_mp3", "dl_too_big", "dl_error", "dl_spotdl_fail")


def _sum_kind(conn, kind, since, until):
    row = conn.execute(
        "SELECT COALESCE(SUM(n), 0) FROM bot_events WHERE kind = ? AND ts >= ? AND ts <= ?",
        (kind, since, until),
    ).fetchone()
    return int(row[0] or 0)


def summarize_period(days=7, *, until=None, db_name="music.db"):
    """Return a dict of counts for the last `days` ending at `until` (unix, exclusive)."""
    create_database(db_name)
    until = int(until or time.time())
    since = until - int(days) * 86400
    conn = _connect(db_name)
    kinds = {
        row[0]: int(row[1] or 0)
        for row in conn.execute(
            """
            SELECT kind, COALESCE(SUM(n), 0)
            FROM bot_events
            WHERE ts >= ? AND ts <= ?
            GROUP BY kind
            """,
            (since, until),
        )
    }
    users_active = conn.execute(
        """
        SELECT COUNT(DISTINCT user_id) FROM bot_events
        WHERE ts >= ? AND ts <= ? AND user_id IS NOT NULL
        """,
        (since, until),
    ).fetchone()[0]
    users_new = conn.execute(
        "SELECT COUNT(*) FROM users WHERE first_seen IS NOT NULL AND first_seen >= ? AND first_seen <= ?",
        (since, until),
    ).fetchone()[0]
    users_touch = conn.execute(
        "SELECT COUNT(*) FROM users WHERE last_use IS NOT NULL AND last_use >= ? AND last_use <= ?",
        (since, until),
    ).fetchone()[0]
    conn.close()

    sent = int(kinds.get("track_sent", 0))
    queued = int(kinds.get("track_queued", 0))
    requested = int(kinds.get("tracks_requested", 0))
    dl_ok = int(kinds.get(DL_OK, 0))
    dl_fail = sum(int(kinds.get(k, 0)) for k in DL_FAIL_KINDS)
    dl_try = dl_ok + dl_fail
    req = int(kinds.get("request", 0))
    req_full = int(kinds.get("request_full", 0))
    req_partial = int(kinds.get("request_partial", 0))
    req_none = int(kinds.get("request_none", 0))
    req_outcomes = req_full + req_partial + req_none

    def pct(part, whole):
        if not whole:
            return None
        return round(100.0 * part / whole, 1)

    return {
        "days": days,
        "since": since,
        "until": until,
        "users_active": int(users_active or 0),
        "users_new": int(users_new or 0),
        "users_with_last_use": int(users_touch or 0),
        "starts": int(kinds.get("start", 0)),
        "searches": int(kinds.get("search", 0)),
        "inline_searches": int(kinds.get("inline_search", 0)),
        "requests": req,
        "tracks_requested": requested,
        "tracks_sent": sent,
        "tracks_queued": queued,
        "cache_hit_pct": pct(sent, sent + queued),
        "request_full": req_full,
        "request_partial": req_partial,
        "request_none": req_none,
        "request_full_pct": pct(req_full, req_outcomes),
        "downloads_ok": dl_ok,
        "downloads_fail": dl_fail,
        "downloads_tried": dl_try,
        "download_ok_pct": pct(dl_ok, dl_try),
        "kinds": kinds,
    }


def _fmt_pct(value):
    return "—" if value is None else f"{value}%"


def format_stats_text(summary, title):
    since = datetime.fromtimestamp(summary["since"], tz=timezone.utc).strftime("%Y-%m-%d")
    until = datetime.fromtimestamp(summary["until"] - 1, tz=timezone.utc).strftime("%Y-%m-%d")
    return "\n".join(
        [
            title,
            f"{since} → {until} UTC  ({summary['days']}d)",
            f"users active: {summary['users_active']}  |  new: {summary['users_new']}",
            f"requests: {summary['requests']}  |  full ok {_fmt_pct(summary['request_full_pct'])}  "
            f"(full {summary['request_full']} / partial {summary['request_partial']} / none {summary['request_none']})",
            f"tracks sent: {summary['tracks_sent']}  |  queued: {summary['tracks_queued']}  |  "
            f"cache hit {_fmt_pct(summary['cache_hit_pct'])}",
            f"downloads: {summary['downloads_tried']} tried  |  ok {summary['downloads_ok']}  |  "
            f"fail {summary['downloads_fail']}  |  success {_fmt_pct(summary['download_ok_pct'])}",
            f"searches: {summary['searches']}  |  inline: {summary['inline_searches']}  |  /start: {summary['starts']}",
        ]
    )


def format_stats_html(summary, title):
    since = datetime.fromtimestamp(summary["since"], tz=timezone.utc).strftime("%Y-%m-%d")
    until = datetime.fromtimestamp(summary["until"] - 1, tz=timezone.utc).strftime("%Y-%m-%d")
    rows = [
        ("Active users", summary["users_active"]),
        ("New users", summary["users_new"]),
        ("Requests", summary["requests"]),
        ("Request full-ok", _fmt_pct(summary["request_full_pct"])),
        ("Tracks sent", summary["tracks_sent"]),
        ("Tracks queued", summary["tracks_queued"]),
        ("Cache hit", _fmt_pct(summary["cache_hit_pct"])),
        ("Downloads tried", summary["downloads_tried"]),
        ("Downloads ok", summary["downloads_ok"]),
        ("Download success", _fmt_pct(summary["download_ok_pct"])),
        ("Searches", summary["searches"]),
        ("Inline searches", summary["inline_searches"]),
    ]

    def esc(x):
        return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    table = "".join(
        f"<tr><td>{esc(k)}</td><td><b>{esc(v)}</b></td></tr>" for k, v in rows
    )
    return (
        f"<h2>{esc(title)}</h2>"
        f"<p><i>{esc(since)} → {esc(until)} UTC ({summary['days']}d)</i></p>"
        f"<table><tr><th>Metric</th><th>Value</th></tr>{table}</table>"
    )


def _digest_key(name, db_name="music.db"):
    create_database(db_name)
    conn = _connect(db_name)
    row = conn.execute("SELECT last_key FROM stats_digest WHERE name = ?", (name,)).fetchone()
    conn.close()
    return row[0] if row else None


def _set_digest_key(name, key, db_name="music.db"):
    create_database(db_name)
    conn = _connect(db_name)
    conn.execute(
        """
        INSERT INTO stats_digest (name, last_key) VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET last_key = excluded.last_key
        """,
        (name, key),
    )
    conn.commit()
    conn.close()


def _write_jsonl(summary, title):
    os.makedirs(os.path.dirname(_STATS_JSONL), exist_ok=True)
    line = json.dumps({"title": title, **summary}, ensure_ascii=False)
    with open(_STATS_JSONL, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    file_logger.info("stats: %s", format_stats_text(summary, title).replace("\n", " | "))


def emit_digest(title, days, until=None):
    summary = summarize_period(days, until=until)
    _write_jsonl(summary, title)
    send_log_channel(
        format_stats_text(summary, title),
        html_body=format_stats_html(summary, title),
    )
    return summary


def maybe_emit_period_digests(now=None):
    """Send yesterday's daily and last week's weekly once per period. First run only stamps the key."""
    now = datetime.fromtimestamp(now or time.time(), tz=timezone.utc)
    today = now.strftime("%Y-%m-%d")
    # ISO week 2026-W35
    week_key = now.strftime("%G-W%V")

    last_day = _digest_key("daily")
    if last_day is None:
        _set_digest_key("daily", today)
    elif last_day != today:
        yesterday_end = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        emit_digest("Daily stats", 1, until=int(yesterday_end.timestamp()))
        _set_digest_key("daily", today)

    last_week = _digest_key("weekly")
    if last_week is None:
        _set_digest_key("weekly", week_key)
    elif last_week != week_key:
        # Monday 00:00 UTC of the current week is the end of the previous ISO week.
        weekday = now.weekday()  # Mon=0
        this_monday = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=weekday)
        emit_digest("Weekly stats", 7, until=int(this_monday.timestamp()))
        _set_digest_key("weekly", week_key)
