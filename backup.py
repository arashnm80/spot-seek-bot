# run the script with:
# nohup python3 backup.py > backup_nohup.log 2>&1 &

from my_imports import * # imports db_functions too

import asyncio
import os
from telethon import TelegramClient
import requests
import json
from datetime import datetime
from urllib.parse import urlparse
import boto3
from io import BytesIO
import logging

# Logging configuration
# Only log to file, not to stdout/stderr to avoid mixing with print() outputs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.environ["SPOT_SEEK_BOT_API"]
API_ID = os.environ.get('DEVELOPER_TELEGRAM_APP_API_ID')
API_HASH = os.environ.get('DEVELOPER_TELEGRAM_APP_API_HASH')
PHONE_NUMBER = os.environ.get('DEVELOPER_TELEGRAM_PHONE_NUMBER')

# Configuration for resume functionality
# To resume from a specific point, change START_INDEX to the last processed index + 1
# Example: if the script stopped at index 150, set START_INDEX = 151
# Check the logs for "index:XXX" to find where to resume
START_INDEX = 7748  # Change this to resume from a specific index

# warp socks proxy
warp_proxies = os.environ["WARP_PROXIES"]
warp_proxies = json.loads(warp_proxies)
# parse it and convert to a tuple to be used by telethon or other libraries
warp_proxy = urlparse(warp_proxies['http'])
warp_proxy = (
    warp_proxy.scheme.replace('h', ''),  # 'socks5h' → 'socks5'
    warp_proxy.hostname,
    warp_proxy.port,
    bool(warp_proxy.username and warp_proxy.password),
    warp_proxy.username,
    warp_proxy.password
)

class TelegramDownloader:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.channel_ids = list(CHANNEL_IDS.values())  # Convert to list for rotation
        self.current_channel_index = 0  # Track current channel for rotation
        self.client = None
        self.s3_client = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY
        )
        self.session = requests.Session()  # Add reusable session
    
    def get_next_channel_id(self):
        """Get next channel ID in rotation and update index"""
        channel_id = self.channel_ids[self.current_channel_index]
        self.current_channel_index = (self.current_channel_index + 1) % len(self.channel_ids)
        return channel_id
        
    async def init_client(self):
        """Initialise le client Telethon"""
        self.client = TelegramClient('developer_account', API_ID, API_HASH, proxy=warp_proxy)
        await self.client.start(phone=PHONE_NUMBER)
        print("Client Telethon initialisé")
    
    def send_media_group_to_channel(self, tracks_batch, channel_id):
        """Envoie un groupe de fichiers audio dans le canal via l'API bot"""
        url = f'https://api.telegram.org/bot{self.bot_token}/sendMediaGroup'
        
        # Prepare media group with audio files and captions
        media = []
        for track_data in tracks_batch:
            db_index, track_id, audio_id = track_data
            media.append({
                'type': 'audio',
                'media': audio_id,
                'caption': track_id
            })
        
        data = {
            'chat_id': channel_id,
            'media': json.dumps(media)
        }
        
        # Try sending with current session, handle connection errors
        for attempt in range(2):  # Max 2 attempts
            try:
                print(f"before sendMediaGroup post request for {len(tracks_batch)} files")
                response = self.session.post(url, data=data, timeout=60)  # Increased timeout for groups
                print("after sendMediaGroup post request")
                
                if response.status_code == 200:
                    result = response.json()
                    if result['ok']:
                        messages = result['result']
                        print(f"Groupe de {len(messages)} fichiers envoyé dans le canal {channel_id}")
                        
                        # Return list of (message_id, sent_audio_id, track_id) tuples
                        sent_data = []
                        for i, message in enumerate(messages):
                            message_id = message['message_id']
                            sent_audio_id = message['audio']['file_id']
                            original_track_id = tracks_batch[i][1]  # track_id from original batch
                            message_caption = message.get('caption', '')
                            
                            # Safety check: verify track_id matches caption
                            if message_caption != original_track_id:
                                print(f"⚠️ WARNING: Track ID mismatch! Expected: {original_track_id}, Caption: {message_caption}")
                                print(f"   Skipping this file for safety")
                                continue
                            
                            # Check if audio_id changed
                            original_audio_id = tracks_batch[i][2]
                            if sent_audio_id != original_audio_id:
                                print(f"⚠️ Audio ID changed: {original_audio_id[:15]}... → {sent_audio_id[:15]}...")
                            else:
                                print(f"✓ Audio ID unchanged: {sent_audio_id[:15]}...")
                            
                            sent_data.append((message_id, sent_audio_id, original_track_id))
                        
                        return sent_data
                    else:
                        print(f"Erreur lors de l'envoi du groupe: {result['description']}")
                        return None
                else:
                    print(f"Erreur HTTP: {response.status_code}")
                    return None
                    
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                print(f"Erreur de connexion (tentative {attempt + 1}/2): {e}")
                if attempt == 0:  # Only retry once
                    print("Rétablissement de la session...")
                    self.session.close()
                    self.session = requests.Session()  # Create new session
                else:
                    print(f"Échec définitif pour le groupe après 2 tentatives")
                    return None
        
        return None
    
    async def upload_media_group_to_s3(self, sent_data, channel_id):
        """Télécharge un groupe de fichiers audio du canal et les upload vers S3"""
        uploaded_files = []
        
        try:
            # Get all message IDs from the sent data
            message_ids = [data[0] for data in sent_data]
            
            # Récupère tous les messages du groupe en une seule fois
            messages = await self.client.get_messages(channel_id, ids=message_ids)
            
            if not messages:
                print(f"Messages {message_ids} non trouvés dans le canal {channel_id}")
                return uploaded_files
            
            # Process each message in the group
            for i, message in enumerate(messages):
                message_id, sent_audio_id, track_id = sent_data[i]
                
                # Safety check: verify track_id matches message caption
                message_caption = getattr(message, 'text', '') or getattr(message, 'caption', '')
                if message_caption != track_id:
                    print(f"⚠️ WARNING: Track ID mismatch in download! Expected: {track_id}, Caption: {message_caption}")
                    print(f"   Skipping download for safety")
                    continue
                
                # Vérifie si le message contient un fichier audio
                if message.audio:
                    # Utilise le track_id comme nom de fichier
                    s3_key = f"{track_id}.mp3"
                    
                    print(f"Upload vers S3 en cours: {s3_key}")
                    
                    # Télécharge le fichier en mémoire
                    audio_bytes = BytesIO()
                    await self.client.download_media(message.audio, audio_bytes)
                    audio_bytes.seek(0)
                    
                    # Upload vers S3
                    self.s3_client.put_object(
                        Bucket=S3_BUCKET_NAME,
                        Key=s3_key,
                        Body=audio_bytes.getvalue(),
                        ContentType='audio/mpeg'
                    )
                    
                    print(f"Fichier uploadé vers S3: s3://{S3_BUCKET_NAME}/{s3_key}")
                    uploaded_files.append((s3_key, track_id))
                else:
                    print(f"Le message {message_id} ne contient pas de fichier audio")
                    
        except Exception as e:
            print(f"Erreur lors de l'upload du groupe: {e}")
            
        return uploaded_files
    
    async def process_tracks_from_db(self, start_index=0, delay=0.01, batch_size=10):
        """Process tracks from database in batches starting from a specific index"""
        uploaded_files = []
        
        # Get tracks from database starting from start_index
        tracks_data = get_all_tracks_for_backup(start_index)
        total_tracks = get_total_tracks_count()
        
        if not tracks_data:
            print("Aucun track à traiter trouvé dans la base de données.")
            logger.info("No tracks to process found in database")
            return uploaded_files
        
        print(f"Traitement de {len(tracks_data)} tracks à partir de l'index {start_index}/{total_tracks} par groupes de {batch_size}")
        logger.info(f"Processing {len(tracks_data)} tracks starting from index {start_index}/{total_tracks} in batches of {batch_size}")
        
        # Process tracks in batches
        for i in range(0, len(tracks_data), batch_size):
            batch = tracks_data[i:i + batch_size]
            batch_start_index = batch[0][0]  # db_index of first track in batch
            batch_end_index = batch[-1][0]   # db_index of last track in batch
            
            print(f"\n=== Traitement du lot {i//batch_size + 1}: indices {batch_start_index}-{batch_end_index} ({len(batch)} fichiers) ===")
            logger.info(f"BATCH START batch:{i//batch_size + 1} indices:{batch_start_index}-{batch_end_index} count:{len(batch)}")
            
            # Get next channel ID in rotation
            channel_id = self.get_next_channel_id()
            print(f"Utilisation du canal: {channel_id}")
            
            # Send media group to channel
            sent_data = self.send_media_group_to_channel(batch, channel_id)
            if sent_data:
                # Update database for each track in the batch
                for message_id, sent_audio_id, track_id in sent_data:
                    add_or_update_track_info(track_id, sent_audio_id, channel_id, message_id)
                    print(f"Base de données mise à jour pour {track_id} avec audio_id: {sent_audio_id[:15]}...")
                
                # Wait for messages to arrive
                await asyncio.sleep(3)
                
                # Upload all files in the group to S3
                batch_uploaded = await self.upload_media_group_to_s3(sent_data, channel_id)
                
                # Update S3 status for each successfully uploaded file
                for s3_key, track_id in batch_uploaded:
                    update_s3_status(track_id, 1)
                    uploaded_files.append(s3_key)
                    print(f"✓ Succès: s3://{S3_BUCKET_NAME}/{s3_key} - S3 status mis à jour")
                
                # Log results for each track in batch
                for j, (message_id, sent_audio_id, track_id) in enumerate(sent_data):
                    db_index = batch[j][0]
                    if any(track_id == t_id for _, t_id in batch_uploaded):
                        logger.info(f"SUCCESS index:{db_index} track:{track_id} | ch:{channel_id} msg:{message_id} s3:OK")
                    else:
                        logger.error(f"FAIL index:{db_index} track:{track_id} | ch:{channel_id} msg:{message_id} s3:FAIL")
                        print(f"✗ Échec de l'upload pour {track_id}")
            else:
                # Log failure for entire batch
                for track_data in batch:
                    db_index, track_id, audio_id = track_data
                    print(f"✗ Échec de l'envoi pour {track_id}")
                    logger.error(f"FAIL index:{db_index} track:{track_id} | telegram_send:FAIL")
            
            # Log current progress for resume functionality
            processed_count = min(i + batch_size, len(tracks_data))
            print(f"Progression: {processed_count}/{len(tracks_data)} (index global: {batch_end_index})")
            
            # Delay between batches (except for the last one)
            if i + batch_size < len(tracks_data):
                print(f"Attente de {delay} secondes avant le prochain lot...")
                await asyncio.sleep(delay)
        
        return uploaded_files
    
    async def cleanup(self):
        """Nettoie les ressources"""
        if self.client:
            await self.client.disconnect()
            print("Client déconnecté")

async def main():
    """Fonction principale"""
    downloader = TelegramDownloader()
    
    try:
        # Initialise le client
        await downloader.init_client()
        
        # Get total count for progress tracking
        total_tracks = get_total_tracks_count()
        print(f"Début de l'upload vers S3 à partir de l'index {START_INDEX}...")
        print(f"Total de tracks à traiter: {total_tracks}")
        
        if START_INDEX > 0:
            print(f"⚠️ REPRISE: Démarrage à partir de l'index {START_INDEX}")
            logger.info(f"RESUME: Starting from index {START_INDEX}")
        
        # Process tracks from database
        uploaded_files = await downloader.process_tracks_from_db(START_INDEX)
        
        # Résumé
        print(f"\n=== RÉSUMÉ ===")
        print(f"Fichiers uploadés: {len(uploaded_files)}")
        print(f"Index de départ: {START_INDEX}")
        for s3_key in uploaded_files:
            print(f"  - s3://{S3_BUCKET_NAME}/{s3_key}")
        
        if len(uploaded_files) > 0:
            print(f"\n💡 Pour reprendre après le dernier fichier traité, modifiez START_INDEX dans le script.")
            
    except Exception as e:
        print(f"Erreur: {e}")
        logger.error(f"Main error: {e}")
    finally:
        await downloader.cleanup()

if __name__ == "__main__":
    # Lance le script
    asyncio.run(main())