from variables import *
import sqlite3 # to use sqlite3 database
import json
import time

def _ensure_column(cursor, table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    if column not in [row[1] for row in cursor.fetchall()]:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def create_database(db_name="music.db"):
    """
    Create a SQLite database and the required tables if they do not exist.
    """
    conn = sqlite3.connect(db_name)
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
    
    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            language_code TEXT,
            is_premium INTEGER DEFAULT 0,
            last_use INTEGER
        )
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
    Add or update user information in the database.
    If user doesn't exist, creates a new row. If exists, updates the information.
    """
    import time
    if last_use is None:
        last_use = int(time.time())  # Current unix timestamp
    
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO users (id, username, language_code, is_premium, last_use)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, language_code, int(is_premium), last_use))
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
    Returns tuple (id, username, language_code, is_premium, last_use) or None if not found.
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        SELECT id, username, language_code, is_premium, last_use FROM users WHERE id = ?
    ''', (user_id,))
    result = c.fetchone()
    conn.close()
    return result


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