#!/bin/bash

# Check if virtual environment exists and activate it
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating virtual environment (venv)..."
    source venv/bin/activate
fi

# Run the kg_generator_gpu_1.py in the background
# We use -u for unbuffered output to ensure logs appear in real-time
export PYTHONUNBUFFERED=1
nohup python3 -u kg_generator_gpu_1.py > kg_console_gpu_1.log 2>&1 &

PID=$!
echo "--------------------------------------------------"
echo "KG Generator (GPU 1) started in background."
echo "PID: $PID"
echo "Console output: kg_console_gpu_1.log"
echo "To stop the process, run: kill $PID"
echo "--------------------------------------------------"
