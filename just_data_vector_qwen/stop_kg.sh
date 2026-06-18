#!/bin/bash

# ==============================================================================
# KMC Knowledge Graph Pipeline Shutdown Script
# ==============================================================================

echo "--------------------------------------------------"
echo "🛑 Initiating shutdown of KG Pipeline and Models..."
echo "--------------------------------------------------"

# 1. Stop Python Generators
stop_python_process() {
    local script_name=$1
    local gpu_id=$2
    local pid=$(pgrep -f "python3.*$script_name")
    
    if [ -n "$pid" ]; then
        echo "[*] GPU $gpu_id: Stopping $script_name (PID: $pid)..."
        kill $pid
        sleep 2
        # Force kill if still running
        if ps -p $pid > /dev/null; then
            echo "[!] GPU $gpu_id: Process persistent. Force killing..."
            kill -9 $pid
        fi
    else
        echo "[-] GPU $gpu_id: No generator process found for $script_name."
    fi
}

stop_python_process "kg_generator_gpu_0.py" 0
stop_python_process "kg_generator_gpu_1.py" 1

# 2. Stop Ollama Instances
echo "[*] Cleaning up Ollama server and model instances..."
if pgrep -f "ollama" > /dev/null; then
    echo "[!] Found active Ollama processes. Terminating..."
    pkill -f "ollama"
    sleep 3
    # Check again and force kill if necessary
    if pgrep -f "ollama" > /dev/null; then
        echo "[!] Some Ollama processes are stuck. Force killing all..."
        pkill -9 -f "ollama"
    fi
    echo "[+] Ollama processes terminated."
else
    echo "[-] No Ollama processes found."
fi

echo "--------------------------------------------------"
echo "✅ Shutdown complete."
