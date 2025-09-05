from variables import *
import sqlite3 # to use sqlite3 database

##############################################################
# new sqlite database system
##############################################################

# Create a SQLite database and table
def create_database(db_name="music.db"):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS track_info (
            spotify_track_id TEXT PRIMARY KEY,
            telegram_audio_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Function to fetch a telegram_audio_id by spotify_track_id
def get_telegram_audio_id(spotify_track_id, db_name="music.db"):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        SELECT telegram_audio_id FROM track_info WHERE spotify_track_id = ?
    ''', (spotify_track_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# Function to add or update data in the database
def add_or_update_track_info(spotify_track_id, telegram_audio_id, db_name="music.db"):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO track_info (spotify_track_id, telegram_audio_id)
        VALUES (?, ?)
    ''', (spotify_track_id, telegram_audio_id))
    conn.commit()
    conn.close()

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