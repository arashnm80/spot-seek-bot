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

# Navigate to the script's directory
cd "$SCRIPT_DIR"

nohup python3 "$SCRIPT_NAME" > /dev/null 2>&1 &

echo "Script restarted successfully."
