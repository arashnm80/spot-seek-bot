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
START_INDEX = 7709  # Change this to resume from a specific index

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
    
    def send_audio_to_channel(self, audio_id, track_id, channel_id):
        """Envoie un fichier audio dans le canal via l'API bot"""
        url = f'https://api.telegram.org/bot{self.bot_token}/sendAudio'
        data = {
            'chat_id': channel_id,
            'audio': audio_id,
            'caption': track_id
        }
        
        # Try sending with current session, handle connection errors
        for attempt in range(2):  # Max 2 attempts
            try:
                print("before sendAudio post request")
                response = self.session.post(url, data=data, timeout=30)
                print("after sendAudio post request")
                
                if response.status_code == 200:
                    result = response.json()
                    if result['ok']:
                        message_id = result['result']['message_id']
                        # Get the audio_id from the sent message
                        sent_audio_id = result['result']['audio']['file_id']
                        
                        # Check if audio_id changed
                        if sent_audio_id != audio_id:
                            print(f"⚠️ Audio ID changed: {audio_id} → {sent_audio_id}")
                        else:
                            print(f"✓ Audio ID unchanged: {audio_id}")
                        
                        print(f"Fichier {audio_id} envoyé dans le canal {channel_id}, message_id: {message_id}")
                        return message_id, sent_audio_id
                    else:
                        print(f"Erreur lors de l'envoi: {result['description']}")
                        return None, None
                else:
                    print(f"Erreur HTTP: {response.status_code}")
                    return None, None
                    
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                print(f"Erreur de connexion (tentative {attempt + 1}/2): {e}")
                if attempt == 0:  # Only retry once
                    print("Rétablissement de la session...")
                    self.session.close()
                    self.session = requests.Session()  # Create new session
                else:
                    print(f"Échec définitif pour {track_id} après 2 tentatives")
                    return None, None
        
        return None, None
    
    async def upload_latest_audio_to_s3(self, track_id, channel_id, message_id):
        """Télécharge le fichier audio spécifique du canal et l'upload vers S3"""
        try:
            # Récupère le message spécifique par son ID
            message = await self.client.get_messages(channel_id, ids=message_id)
            
            if not message:
                print(f"Message {message_id} non trouvé dans le canal {channel_id}")
                return None
            
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
                return s3_key
            else:
                print("Le dernier message ne contient pas de fichier audio")
                return None
                
        except Exception as e:
            print(f"Erreur lors de l'upload: {e}")
            return None
    
    async def process_tracks_from_db(self, start_index=0, delay=0.01):
        """Process tracks from database starting from a specific index"""
        uploaded_files = []
        
        # Get tracks from database starting from start_index
        tracks_data = get_all_tracks_for_backup(start_index)
        total_tracks = get_total_tracks_count()
        
        if not tracks_data:
            print("Aucun track à traiter trouvé dans la base de données.")
            logger.info("No tracks to process found in database")
            return uploaded_files
        
        print(f"Traitement de {len(tracks_data)} tracks à partir de l'index {start_index}/{total_tracks}")
        logger.info(f"Processing {len(tracks_data)} tracks starting from index {start_index}/{total_tracks}")
        
        for track_data in tracks_data:
            db_index, track_id, audio_id = track_data
            
            print(f"\n--- Traitement index {db_index}: {track_id} ({audio_id[:15]}...) ---")
            logger.info(f"START index:{db_index} track:{track_id} | audio_id:{audio_id[:15]}...")
            
            # Get next channel ID in rotation
            channel_id = self.get_next_channel_id()
            print(f"Utilisation du canal: {channel_id}")
            
            # Envoie le fichier dans le canal
            message_id, sent_audio_id = self.send_audio_to_channel(audio_id, track_id, channel_id)
            if message_id and sent_audio_id:
                # Update database with channel and message info using the sent audio_id
                add_or_update_track_info(track_id, sent_audio_id, channel_id, message_id)
                print(f"Base de données mise à jour pour {track_id} avec audio_id: {sent_audio_id}")
                
                # Attend un peu pour que le message arrive
                await asyncio.sleep(2)
                
                # Upload le fichier vers S3
                s3_key = await self.upload_latest_audio_to_s3(track_id, channel_id, message_id)
                if s3_key:
                    # Update S3 status in database
                    update_s3_status(track_id, 1)
                    uploaded_files.append(s3_key)
                    print(f"✓ Succès: s3://{S3_BUCKET_NAME}/{s3_key} - S3 status mis à jour")
                    logger.info(f"SUCCESS index:{db_index} track:{track_id} | ch:{channel_id} msg:{message_id} s3:OK")
                else:
                    print(f"✗ Échec de l'upload pour {track_id}")
                    logger.error(f"FAIL index:{db_index} track:{track_id} | ch:{channel_id} msg:{message_id} s3:FAIL")
            else:
                print(f"✗ Échec de l'envoi pour {track_id}")
                logger.error(f"FAIL index:{db_index} track:{track_id} | telegram_send:FAIL")
            
            # Log current progress for resume functionality
            print(f"Progression: {db_index + 1 - start_index}/{len(tracks_data)} (index global: {db_index})")
            
            # Délai entre les uploads (sauf pour le dernier)
            if track_data != tracks_data[-1]:
                print(f"Attente de {delay} secondes...")
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