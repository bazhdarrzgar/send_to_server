#!/bin/bash

# Configuration
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "------------------------------------------------"
echo " 🛑 Terminating all Llama-related processes..."
echo "------------------------------------------------"

# Kill llama servers
pkill -9 -f "llama-server" 2>/dev/null
# Kill background managers
pkill -9 -f "run_server_bg" 2>/dev/null
pkill -9 -f "run_generator_bg" 2>/dev/null
# Kill python generators
pkill -9 -f "generate_dataset" 2>/dev/null

# Clean up ports specifically
fuser -k 8011/tcp 2>/dev/null
fuser -k 8012/tcp 2>/dev/null
fuser -k 8013/tcp 2>/dev/null

echo "✅ All processes killed."

# Check if user wants to generate dataset
# If --generate or -g is passed as an argument, or if prompt is answered 'y'
START_GEN=false

if [[ "$1" == "--generate" || "$1" == "-g" ]]; then
    START_GEN=true
else
    read -p "❓ Do you want to start the generation pipeline now? (y/N): " choice
    if [[ "$choice" =~ ^[Yy]$ ]]; then
        START_GEN=true
    fi
fi

if [ "$START_GEN" = true ]; then
    echo ""
    echo "------------------------------------------------"
    echo " 🚀 Starting Servers and Generators..."
    echo "------------------------------------------------"
    
    # Start Servers
    python3 "$BASE_DIR/run_server_bg_first.py"
    python3 "$BASE_DIR/run_server_bg_second.py"
    python3 "$BASE_DIR/run_server_bg_third.py"
    
    echo "⏳ Waiting 10 seconds for servers to warm up..."
    sleep 10
    
    # Start Generators
    python3 "$BASE_DIR/run_generator_bg_first.py"
    python3 "$BASE_DIR/run_generator_bg_second.py"
    python3 "$BASE_DIR/run_generator_bg_third.py"
    
    echo "✅ Generation pipeline is now running in the background."
    echo "   Check your logs with: tail -f *.txt"
else
    echo "🔚 Setup complete. No new processes started."
fi
