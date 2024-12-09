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
cd /root/Storage/spot-seek-bot/
nohup python3 "$SCRIPT_NAME" > /dev/null 2>&1 &

echo "Script restarted successfully."
