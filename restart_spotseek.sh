#!/bin/bash

# Define the app module and server settings for uvicorn
APP_MODULE="spotseek:app"
HOST="0.0.0.0"
PORT="3006"

# get address of current script file (which is repository directory)
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PID_FILE="$SCRIPT_DIR/uvicorn.spotseek.pid"

# Find and stop any existing uvicorn process for this app (graceful, then force)
echo "Finding and stopping the existing instance..."

# First, try stopping by recorded PID (process group)
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$PID" ] && ps -p "$PID" >/dev/null 2>&1; then
        echo "Stopping PID $PID and its process group..."
        kill -TERM -"$PID" 2>/dev/null || true
        for i in {1..10}; do
            if ! ps -p "$PID" >/dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        if ps -p "$PID" >/dev/null 2>&1; then
            echo "Force killing PID $PID group..."
            kill -KILL -"$PID" 2>/dev/null || true
        fi
    fi
    rm -f "$PID_FILE" 2>/dev/null || true
fi

# Graceful stop by pattern and by port
pkill -f -TERM "uvicorn.*${APP_MODULE}" 2>/dev/null || true
fuser -k -TERM "${PORT}/tcp" 2>/dev/null || true

# Wait up to 10s for the port to free
for i in {1..10}; do
    if ! fuser "${PORT}/tcp" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Force stop if still busy
if fuser "${PORT}/tcp" >/dev/null 2>&1; then
    echo "Forcing termination of lingering processes..."
    pkill -f -KILL "uvicorn.*${APP_MODULE}" 2>/dev/null || true
    fuser -k -KILL "${PORT}/tcp" 2>/dev/null || true
fi

# Start the server
echo "Starting the server..."

# Navigate to the script's directory
cd "$SCRIPT_DIR"

# Activate the virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Run uvicorn in the background using the virtual environment's Python (new process group)
nohup setsid python3 -m uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" > /dev/null 2>&1 &
echo $! > "$PID_FILE"

echo "Uvicorn ($APP_MODULE) restarted successfully on $HOST:$PORT."
