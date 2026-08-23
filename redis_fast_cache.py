import os
import sqlite3
from typing import Optional, Tuple

try:
    import redis  # Requires: pip install redis
except ImportError as import_error:  # pragma: no cover
    raise SystemExit(
        "The 'redis' package is required. Install with: pip install redis"
    ) from import_error


# Module-level cached Redis client (lazy-initialized)
_redis_client: Optional["redis.Redis"] = None


def _get_redis_client() -> "redis.Redis":
    """
    Create or return a cached Redis client.

    Config priority:
    - REDIS_URL (e.g. redis://localhost:6379/0)
    - REDIS_HOST, REDIS_PORT, REDIS_DB (defaults: localhost, 6379, 0)
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        _redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
    else:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db_index = int(os.getenv("REDIS_DB", "0"))
        _redis_client = redis.Redis(host=host, port=port, db=db_index, decode_responses=True)

    return _redis_client


def _sqlite_lookup_telegram_audio_id(spotify_track_id: str, db_name: str = "music.db") -> Optional[str]:
    """
    Read-through fallback: query SQLite for a single spotify_track_id.

    Returns the telegram_audio_id if found, otherwise None.
    """
    conn = sqlite3.connect(db_name)
    try:
        c = conn.cursor()
        c.execute(
            """
            SELECT telegram_audio_id
            FROM track_info
            WHERE spotify_track_id = ?
            """,
            (spotify_track_id,),
        )
        row = c.fetchone()
        return row[0] if row and row[0] is not None else None
    finally:
        conn.close()


def _make_cache_key(spotify_track_id: str) -> str:
    """Build a simple Redis key for the track lookup."""
    return f"track:telegram_audio_id:{spotify_track_id}"


def get_telegram_audio_id_cached(spotify_track_id: str, db_name: str = "music.db") -> Optional[str]:
    """
    Fast read for telegram_audio_id using Redis, with SQLite fallback.

    - Reads the value from Redis using a simple string key per track.
    - If the key is missing (cache miss) or Redis is unavailable, falls back to SQLite.
    - On successful SQLite read, writes the value back to Redis for future hits.

    This function mirrors the signature of your existing getter and can be
    used as a drop-in replacement in read paths.
    """
    key = _make_cache_key(spotify_track_id)

    # 1) Try Redis first (fast path)
    try:
        r = _get_redis_client()
        cached = r.get(key)
        if cached is not None:
            return cached  # decode_responses=True already returns str
    except Exception:
        # Redis unavailable: gracefully fall back to SQLite
        pass

    # 2) Fallback to SQLite
    result = _sqlite_lookup_telegram_audio_id(spotify_track_id, db_name=db_name)

    # 3) Populate cache on hit (best-effort; ignore Redis errors)
    if result is not None:
        try:
            r = _get_redis_client()
            r.set(key, result)
        except Exception:
            pass

    return result


def warmup_cache_from_sqlite(db_name: str = "music.db", batch_size: int = 1000) -> Tuple[int, int]:
    """
    Bulk-load all (spotify_track_id, telegram_audio_id) pairs from SQLite into Redis.

    - Uses a Redis pipeline for efficient batched writes.
    - Skips rows where telegram_audio_id is NULL.

    Returns (rows_scanned, rows_cached).
    """
    # Ensure Redis is reachable before scanning SQLite
    try:
        r = _get_redis_client()
        r.ping()
    except Exception as exc:
        raise SystemExit(
            "Redis is not reachable. Start Redis or set REDIS_URL, then retry warmup.\n"
            f"Details: {exc}"
        ) from exc

    # Open SQLite and scan rows
    conn = sqlite3.connect(db_name)
    rows_scanned = 0
    rows_cached = 0
    try:
        c = conn.cursor()
        c.execute(
            """
            SELECT spotify_track_id, telegram_audio_id
            FROM track_info
            WHERE telegram_audio_id IS NOT NULL
            """
        )

        pipe = r.pipeline(transaction=False)

        while True:
            batch = c.fetchmany(batch_size)
            if not batch:
                break

            for spotify_track_id, telegram_audio_id in batch:
                rows_scanned += 1
                if telegram_audio_id is None:
                    continue
                key = _make_cache_key(spotify_track_id)
                pipe.set(key, telegram_audio_id)
                rows_cached += 1

            pipe.execute()

        return rows_scanned, rows_cached
    finally:
        conn.close()


def _parse_int(value: Optional[str], default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


if __name__ == "__main__":
    # Minimal CLI for convenience:
    #   - Pre-warm Redis from SQLite:   python redis_fast_cache.py warmup [DB_PATH] [BATCH_SIZE]
    #   - Single lookup test:           python redis_fast_cache.py get <SPOTIFY_TRACK_ID> [DB_PATH]
    import sys

    args = sys.argv[1:]
    if not args:
        print(
            "Usage:\n"
            "  warmup [DB_PATH] [BATCH_SIZE]  -> Preload Redis from SQLite\n"
            "  get <SPOTIFY_TRACK_ID> [DB_PATH] -> Lookup a single id via cache\n"
        )
        raise SystemExit(1)

    cmd = args[0]
    if cmd == "warmup":
        db_path = args[1] if len(args) >= 2 else "music.db"
        batch_size = _parse_int(args[2], 1000) if len(args) >= 3 else 1000
        scanned, cached = warmup_cache_from_sqlite(db_name=db_path, batch_size=batch_size)
        print(f"Scanned {scanned} rows; cached {cached} rows into Redis.")
    elif cmd == "get":
        if len(args) < 2:
            print("Usage: get <SPOTIFY_TRACK_ID> [DB_PATH]")
            raise SystemExit(1)
        track_id = args[1]
        db_path = args[2] if len(args) >= 3 else "music.db"
        value = get_telegram_audio_id_cached(track_id, db_name=db_path)
        print(value if value is not None else "<not found>")
    else:
        print(f"Unknown command: {cmd}")
        raise SystemExit(1)


