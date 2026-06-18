#!/bin/bash

# Navigate to the script directory (optional, usually good practice)
# cd "$(dirname "$0")"

# Check if virtual environment exists and activate it
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating virtual environment (venv)..."
    source venv/bin/activate
fi

# Run the kg_generator.py in the background
# We use nohup to keep it running after logout
# We redirect output to kg_console.log
nohup python3 kg_generator.py > kg_console.log 2>&1 &

PID=$!
echo "--------------------------------------------------"
echo "Knowledge Graph Generator started in background."
echo "PID: $PID"
echo "Console output is being redirected to: kg_console.log"
echo "Application logs are in: kg_pipeline.log"
echo "To stop the process, run: kill $PID"
echo "--------------------------------------------------"
