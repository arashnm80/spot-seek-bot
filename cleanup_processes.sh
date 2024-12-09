#!/bin/bash

# Define the process names for the two Python scripts
# PROCESS_NAME1="spotseek_queue_handler.py"
PROCESS_NAME2="spotseek.py"

# Define the time threshold (20 minutes in this case)
TIME_THRESHOLD="1200"  # 20 minutes in seconds

# Function to find and kill old processes
cleanup_old_processes() {
    local process_name=$1
    echo "Cleaning up processes for: $process_name"

    # Find processes older than the threshold
    ps -eo pid,etime,comm | grep $process_name | grep -v grep | while read -r pid etime comm; do
        # Convert elapsed time (etime) into seconds and compare with threshold
        # Elapsed time format can be in HH:MM:SS, MM:SS, or D-HH:MM
        # Example format: "23:01" or "3-05:22:01"
        
        seconds=$(echo $etime | awk -F '[:-]' '
            NF==3 { print ($1*3600)+($2*60)+$3 }
            NF==2 { print ($1*60)+$2 }
            NF==1 { print $1 }
        ')

        if (( seconds > TIME_THRESHOLD )); then
            echo "Killing process with PID: $pid (Running time: $etime)"
            kill -9 $pid
        fi
    done
}

# Cleanup for both processes
# cleanup_old_processes $PROCESS_NAME1
cleanup_old_processes $PROCESS_NAME2
