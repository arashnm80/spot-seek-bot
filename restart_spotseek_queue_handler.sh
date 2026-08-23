#!/bin/bash

# remove folder of spotdl to bypass possible limitations from that side
rm -rf /root/.spotdl

# Define the script name
SCRIPT_NAME="spotseek_queue_handler.py"

# Find and kill the running process
echo "Finding and killing the existing process..."
PID=$(pgrep -f "$SCRIPT_NAME")

if [ -n "$PID" ]; then
    echo "Killing process with PID $PID..."
    kill -9 "$PID"
else
    echo "No running process found."
fi

# Restart the script
echo "Starting the script..."

# get address of current script file (which is repository directory)
SCRIPT_DIR=$(dirname "$(realpath "$0")")

# Deno on PATH so yt-dlp bestaudio (itag 251) works under proxychains (cron @reboot)
export PATH="$SCRIPT_DIR/.venv/bin:/root/.deno/bin:$PATH"

# Navigate to the script's directory
cd "$SCRIPT_DIR"

# Stale login env can still hold old /etc/environment values (dotenv override=False).
# Unset bot-only keys so repo .env is used. Leave WARP_PROXIES (shared).
unset SPOT_SEEK_BOT_API MUSIC_DATABASE_ID LOG_CHANNEL_ID SPOTIFY_APPS_LIST

# Activate the virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Run the Python script using the virtual environment's Python interpreter
nohup python3 "$SCRIPT_NAME" > /dev/null 2>&1 &

echo "$SCRIPT_NAME restarted successfully."
