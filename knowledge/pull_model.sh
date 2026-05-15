#!/bin/bash

# Configuration
MODEL_NAME="gemma4:26b"
LOG_FILE="ollama_pull_log.txt"

echo "Starting pull for $MODEL_NAME in the background..."
echo "Logs will be saved to $LOG_FILE"

# Run ollama pull in the background and redirect both stdout and stderr to the log file
nohup ollama pull $MODEL_NAME > "$LOG_FILE" 2>&1 &

# Get the process ID
PID=$!

echo "Process started with PID: $PID"
echo "You can check the progress with: tail -f $LOG_FILE"
