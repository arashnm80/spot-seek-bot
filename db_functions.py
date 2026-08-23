from variables import *
import sqlite3 # to use sqlite3 database
import json
import time
import os
from collections import Counter


def _connect(db_name="music.db"):
    conn = sqlite3.connect(db_name, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _ensure_column(cursor, table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    if column not in [row[1] for row in cursor.fetchall()]:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def create_database(db_name="music.db"):
    """
    Create a SQLite database and the required tables if they do not exist.
    """
    conn = _connect(db_name)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS track_info (
            spotify_track_id TEXT PRIMARY KEY,
            telegram_audio_id TEXT,
            telegram_channel_id INTEGER,
            message_id INTEGER,
            s3_status INTEGER DEFAULT 0,
            download_method TEXT
        )
    ''')
    _ensure_column(c, "track_info", "download_method", "TEXT")

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            language_code TEXT,
            is_premium INTEGER DEFAULT 0,
            last_use INTEGER,
            first_seen INTEGER
        )
    ''')
    _ensure_column(c, "users", "first_seen", "INTEGER")
    _ensure_column(c, "users", "consecutive_successes", "INTEGER DEFAULT 0")
    c.execute('''
        UPDATE users SET first_seen = COALESCE(first_seen, last_use)
        WHERE first_seen IS NULL
    ''')
    c.execute('''
        UPDATE users SET consecutive_successes = 0
        WHERE consecutive_successes IS NULL
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS collection_cache (
            collection_type TEXT NOT NULL,
            collection_id TEXT NOT NULL,
            track_ids TEXT NOT NULL,
            fetched_at INTEGER NOT NULL,
            PRIMARY KEY (collection_type, collection_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS download_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            spotify_track_id TEXT NOT NULL,
            first_requested_at INTEGER NOT NULL,
            UNIQUE(user_id, spotify_track_id)
        )
    ''')
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_download_queue_track ON download_queue(spotify_track_id)"
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_download_queue_user_time ON download_queue(user_id, first_requested_at)"
    )
    c.execute('''
        CREATE TABLE IF NOT EXISTS search_cache (
            query_key TEXT PRIMARY KEY,
            results TEXT NOT NULL,
            fetched_at INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_telegram_audio_id(spotify_track_id, db_name="music.db"):
    """
    Fetch the telegram_audio_id by spotify_track_id.
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        SELECT telegram_audio_id FROM track_info WHERE spotify_track_id = ?
    ''', (spotify_track_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_telegram_channel_id(spotify_track_id, db_name="music.db"):
    """
    Fetch the telegram_channel_id by spotify_track_id.
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        SELECT telegram_channel_id FROM track_info WHERE spotify_track_id = ?
    ''', (spotify_track_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def add_or_update_track_info(spotify_track_id, telegram_audio_id, telegram_channel_id, message_id, download_method=None, db_name="music.db"):
    """
    Add or update a track's info in the database.
    download_method is stored for new downloads (e.g. "youtube"). Backup updates
    that omit it keep the existing value. Older rows stay NULL.
    """
    create_database(db_name)
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        INSERT INTO track_info (
            spotify_track_id, telegram_audio_id, telegram_channel_id, message_id, s3_status, download_method
        )
        VALUES (?, ?, ?, ?, 0, ?)
        ON CONFLICT(spotify_track_id) DO UPDATE SET
            telegram_audio_id = excluded.telegram_audio_id,
            telegram_channel_id = excluded.telegram_channel_id,
            message_id = excluded.message_id,
            s3_status = 0,
            download_method = COALESCE(excluded.download_method, track_info.download_method)
    ''', (spotify_track_id, telegram_audio_id, telegram_channel_id, message_id, download_method))
    conn.commit()
    conn.close()


def get_download_method(spotify_track_id, db_name="music.db"):
    """
    Fetch how this track was matched/downloaded (e.g. "youtube"), or None if unknown.
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        SELECT download_method FROM track_info WHERE spotify_track_id = ?
    ''', (spotify_track_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def delete_track(spotify_track_id, db_name="music.db"):
    """
    Delete an entry from the track_info table by its spotify_track_id if it exists.
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        DELETE FROM track_info WHERE spotify_track_id = ?
    ''', (spotify_track_id,))
    conn.commit()
    conn.close()

def update_s3_status(spotify_track_id, s3_status, db_name="music.db"):
    """
    Update the s3_status for a specific track by its spotify_track_id.
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        UPDATE track_info SET s3_status = ? WHERE spotify_track_id = ?
    ''', (int(s3_status), spotify_track_id))
    conn.commit()
    conn.close()

def get_all_tracks_for_backup(start_index=0, db_name="music.db"):
    """
    Get all tracks from database starting from a specific index.
    Returns list of tuples (index, spotify_track_id, telegram_audio_id)
    where index is the row number (0-based) for resume functionality.
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        SELECT spotify_track_id, telegram_audio_id FROM track_info 
        WHERE telegram_audio_id IS NOT NULL AND s3_status = 0 AND (telegram_channel_id IS NULL OR telegram_channel_id != ?)
        ORDER BY spotify_track_id
    ''', (SP11_CHANNEL_ID,))
    results = c.fetchall()
    conn.close()
    
    # Add index to each result and filter from start_index
    indexed_results = [(i, row[0], row[1]) for i, row in enumerate(results) if i >= start_index]
    return indexed_results

def get_total_tracks_count(db_name="music.db"):
    """
    Get total count of tracks that need backup (s3_status = 0).
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        SELECT COUNT(*) FROM track_info 
        WHERE telegram_audio_id IS NOT NULL AND s3_status = 0
    ''')
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def get_start_index_by_letters(first_letters, db_name="music.db"):
    """
    Calculate start index based on first letters of track_id.
    Returns the index of the first track starting with those letters,
    or the index of the first track that comes after alphabetically if no exact match.
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        SELECT spotify_track_id FROM track_info 
        WHERE telegram_audio_id IS NOT NULL AND s3_status = 0 AND (telegram_channel_id IS NULL OR telegram_channel_id != ?)
        ORDER BY spotify_track_id
    ''', (SP11_CHANNEL_ID,))
    results = c.fetchall()
    conn.close()
    
    # Find the first track that starts with the given letters or comes after
    for i, (track_id,) in enumerate(results):
        if track_id >= first_letters:
            return i
    
    # If no track found, return the total count (end of list)
    return len(results)

def add_or_update_user(user_id, username=None, language_code=None, is_premium=False, last_use=None, db_name="music.db"):
    """
    Remember this Telegram user for the queue and for later outreach.
    Inserts on first sight; later calls refresh profile fields without wiping them.
    """
    create_database(db_name)
    if last_use is None:
        last_use = int(time.time())
    if is_premium is None:
        is_premium = False

    conn = _connect(db_name)
    c = conn.cursor()
    c.execute(
        '''
        INSERT INTO users (id, username, language_code, is_premium, last_use, first_seen)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            username = COALESCE(excluded.username, users.username),
            language_code = COALESCE(excluded.language_code, users.language_code),
            is_premium = excluded.is_premium,
            last_use = excluded.last_use
        ''',
        (int(user_id), username, language_code, int(is_premium), last_use, last_use),
    )
    conn.commit()
    conn.close()

def delete_user(user_id, db_name="music.db"):
    """
    Delete a user from the users table by user_id if it exists.
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        DELETE FROM users WHERE id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

def get_user_info(user_id, db_name="music.db"):
    """
    Get user information by user_id.
    Returns tuple (id, username, language_code, is_premium, last_use, first_seen) or None if not found.
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        SELECT id, username, language_code, is_premium, last_use, first_seen FROM users WHERE id = ?
    ''', (user_id,))
    result = c.fetchone()
    conn.close()
    return result


def get_consecutive_successes(user_id, db_name="music.db"):
    create_database(db_name)
    conn = _connect(db_name)
    c = conn.cursor()
    c.execute("SELECT consecutive_successes FROM users WHERE id = ?", (int(user_id),))
    row = c.fetchone()
    conn.close()
    if not row or row[0] is None:
        return 0
    return int(row[0])


def record_request_outcome(user_id, success, db_name="music.db"):
    """Full success = every track in that link was already available and sent."""
    create_database(db_name)
    conn = _connect(db_name)
    c = conn.cursor()
    if success:
        c.execute(
            '''
            UPDATE users
            SET consecutive_successes = COALESCE(consecutive_successes, 0) + 1
            WHERE id = ?
            ''',
            (int(user_id),),
        )
    else:
        c.execute(
            "UPDATE users SET consecutive_successes = 0 WHERE id = ?",
            (int(user_id),),
        )
    conn.commit()
    conn.close()


def user_should_join_channel(user_id, db_name="music.db"):
    """True after a streak of fully successful link requests (new users stay ungated)."""
    return get_consecutive_successes(user_id, db_name) >= promote_channel_join_after_successes


def get_cached_collection_track_ids(collection_type, collection_id, db_name="music.db"):
    """
    Return (track_ids, age_seconds) if this album/playlist is in cache, else None.
    """
    create_database(db_name)
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(
        '''
        SELECT track_ids, fetched_at FROM collection_cache
        WHERE collection_type = ? AND collection_id = ?
        ''',
        (collection_type, collection_id),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    track_ids = json.loads(row[0])
    age = int(time.time()) - int(row[1])
    return track_ids, age


def save_cached_collection_track_ids(collection_type, collection_id, track_ids, db_name="music.db"):
    create_database(db_name)
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(
        '''
        INSERT INTO collection_cache (collection_type, collection_id, track_ids, fetched_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(collection_type, collection_id) DO UPDATE SET
            track_ids = excluded.track_ids,
            fetched_at = excluded.fetched_at
        ''',
        (collection_type, collection_id, json.dumps(track_ids), int(time.time())),
    )
    conn.commit()
    conn.close()


def normalize_search_query(query):
    return " ".join((query or "").lower().split())


def get_cached_search_results(query_key, db_name="music.db"):
    """Return (results, age_seconds) if this search keyword is cached, else None."""
    if not query_key:
        return None
    create_database(db_name)
    conn = _connect(db_name)
    c = conn.cursor()
    c.execute(
        "SELECT results, fetched_at FROM search_cache WHERE query_key = ?",
        (query_key,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    results = json.loads(row[0])
    age = int(time.time()) - int(row[1])
    return results, age


def save_cached_search_results(query_key, results, db_name="music.db"):
    if not query_key or not results:
        return
    create_database(db_name)
    conn = _connect(db_name)
    c = conn.cursor()
    c.execute(
        '''
        INSERT INTO search_cache (query_key, results, fetched_at)
        VALUES (?, ?, ?)
        ON CONFLICT(query_key) DO UPDATE SET
            results = excluded.results,
            fetched_at = excluded.fetched_at
        ''',
        (query_key, json.dumps(results, ensure_ascii=False), int(time.time())),
    )
    conn.commit()
    conn.close()


def enqueue_tracks(user_id, track_ids, requested_at=None, db_name="music.db"):
    """Add tracks for this chat/user. Keeps the original first_requested_at on duplicates."""
    create_database(db_name)
    if not track_ids:
        return 0
    requested_at = int(time.time()) if requested_at is None else int(requested_at)
    user_id = int(user_id)
    conn = _connect(db_name)
    c = conn.cursor()
    c.execute(
        '''
        INSERT INTO users (id, last_use, first_seen, is_premium)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(id) DO UPDATE SET last_use = excluded.last_use
        ''',
        (user_id, requested_at, requested_at),
    )
    added = 0
    for track_id in track_ids:
        if not track_id:
            continue
        c.execute(
            '''
            INSERT OR IGNORE INTO download_queue (user_id, spotify_track_id, first_requested_at)
            VALUES (?, ?, ?)
            ''',
            (user_id, track_id, requested_at),
        )
        added += c.rowcount
    conn.commit()
    conn.close()
    return added


def pending_request_counts(db_name="music.db"):
    """Users waiting for each track that is not in track_info yet."""
    create_database(db_name)
    conn = _connect(db_name)
    c = conn.cursor()
    c.execute(
        '''
        SELECT q.spotify_track_id, COUNT(*)
        FROM download_queue q
        LEFT JOIN track_info t ON t.spotify_track_id = q.spotify_track_id
        WHERE t.telegram_audio_id IS NULL
        GROUP BY q.spotify_track_id
        '''
    )
    counts = Counter(dict(c.fetchall()))
    conn.close()
    return counts


def pending_queue_user_count(db_name="music.db"):
    create_database(db_name)
    conn = _connect(db_name)
    c = conn.cursor()
    c.execute(
        '''
        SELECT COUNT(DISTINCT q.user_id)
        FROM download_queue q
        LEFT JOIN track_info t ON t.spotify_track_id = q.spotify_track_id
        WHERE t.telegram_audio_id IS NULL
        '''
    )
    n = c.fetchone()[0]
    conn.close()
    return n


def next_round_robin_picks(db_name="music.db"):
    """One pending track per user, oldest waiting users first."""
    create_database(db_name)
    conn = _connect(db_name)
    c = conn.cursor()
    c.execute(
        '''
        WITH pending AS (
            SELECT q.id, q.user_id, q.spotify_track_id, q.first_requested_at
            FROM download_queue q
            LEFT JOIN track_info t ON t.spotify_track_id = q.spotify_track_id
            WHERE t.telegram_audio_id IS NULL
        ),
        first_per_user AS (
            SELECT user_id, spotify_track_id, first_requested_at, id,
                   ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY id) AS rn
            FROM pending
        )
        SELECT user_id, spotify_track_id
        FROM first_per_user
        WHERE rn = 1
        ORDER BY first_requested_at, id
        '''
    )
    rows = [(str(user_id), track_id) for user_id, track_id in c.fetchall()]
    conn.close()
    return rows


def remove_track_from_all_queues(track_id, db_name="music.db"):
    """Drop a track from every user queue (after success or a failed download try)."""
    create_database(db_name)
    conn = _connect(db_name)
    c = conn.cursor()
    c.execute("DELETE FROM download_queue WHERE spotify_track_id = ?", (track_id,))
    n = c.rowcount
    conn.commit()
    conn.close()
    return n


def restore_queue_picks(picks, db_name="music.db"):
    """Put round-robin picks back if popular tracks appeared before download."""
    for user_id, track_id in reversed(picks):
        enqueue_tracks(user_id, [track_id], db_name=db_name)


def migrate_received_links_files_into_db(folder_path=None, db_name="music.db"):
    """
    Import legacy per-user text queues into download_queue.
    Does not delete source files; caller may move the folder after verifying counts.
    first_requested_at is the user file ctime (best timestamp those files had).
    """
    create_database(db_name)
    folder_path = folder_path or received_links_folder_path
    if not os.path.isdir(folder_path):
        return {"files": 0, "rows_added": 0, "source_pairs": 0}

    names = [
        name
        for name in os.listdir(folder_path)
        if name != ".gitkeep" and os.path.isfile(os.path.join(folder_path, name))
    ]
    conn = _connect(db_name)
    c = conn.cursor()
    source_pairs = 0
    rows_added = 0
    files_ok = 0
    for name in names:
        try:
            user_id = int(name)
        except ValueError:
            continue
        file_path = os.path.join(folder_path, name)
        try:
            with open(file_path, "r") as handle:
                tracks = [line.strip() for line in handle if line.strip()]
        except Exception:
            continue
        seen = set()
        ordered = []
        for track_id in tracks:
            if track_id not in seen:
                seen.add(track_id)
                ordered.append(track_id)
        source_pairs += len(ordered)
        first_at = int(os.path.getctime(file_path))
        c.execute(
            '''
            INSERT INTO users (id, last_use, first_seen, is_premium)
            VALUES (?, ?, ?, 0)
            ON CONFLICT(id) DO UPDATE SET
                first_seen = COALESCE(users.first_seen, excluded.first_seen)
            ''',
            (user_id, first_at, first_at),
        )
        for track_id in ordered:
            c.execute(
                '''
                INSERT OR IGNORE INTO download_queue (user_id, spotify_track_id, first_requested_at)
                VALUES (?, ?, ?)
                ''',
                (user_id, track_id, first_at),
            )
            rows_added += c.rowcount
        files_ok += 1
        if files_ok % 500 == 0:
            conn.commit()
    conn.commit()
    conn.close()
    return {"files": files_ok, "rows_added": rows_added, "source_pairs": source_pairs}