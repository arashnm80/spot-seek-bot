#!/bin/bash

#######################################################################
# this script is going to be executed on system reboot
# as a to-do I can fix it bugs later to be able to perform it without restart
#######################################################################


# # Function to check if a process is running
# is_process_running() {
#     pgrep -f "$1" > /dev/null
# }

# remove folder of spotdl to bypass possible limitations from that side
rm -rf /root/.spotdl

# Change to the directory
cd /root/Storage/spot-seek-bot/

# # Check if the spotseek main bot script is running before attempting to stop it
# if is_process_running "python3 spotseek.py"; then
#     echo "Stopping spotseek.py"
#     pkill -f "python3 spotseek.py"
#     sleep 5
# else
#     echo "spotseek.py is not running"
# fi

# Start the spotseek main bot with nohup
nohup python3 spotseek.py > /dev/null 2>&1 &

# # Check if the spotseek queue handler script is running before attempting to stop it
# if is_process_running "python3 spotseek_queue_handler.py"; then
#     echo "Stopping spotseek_queue_handler.py..."
#     pkill -f "python3 spotseek_queue_handler.py"
#     sleep 5
# else
#     echo "spotseek_queue_handler.py is not running"
# fi

# Start spotseek queue handler with nohup
nohup python3 spotseek_queue_handler.py > /dev/null 2>&1 &

# # Check if the script started successfully
# if [ $? -eq 0 ]; then
#     echo "Script started successfully."
# else
#     echo "Failed to start the script."
# fi
