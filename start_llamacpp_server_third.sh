#!/bin/bash

# Bypass system proxy for localhost connections
export no_proxy="localhost,127.0.0.1,0.0.0.0"
export NO_PROXY="localhost,127.0.0.1,0.0.0.0"

# Configuration
MODEL_PATH="model_weights/gemma-3-27b-it-q4_k_m.gguf"
HOST="0.0.0.0"
PORT=8010
GPU_LAYERS=-1 

# Check if model path is provided as an argument
if [ ! -z "$1" ]; then
    MODEL_PATH="$1"
fi

if [ ! -f "$MODEL_PATH" ]; then
    echo "Error: Model file not found at $MODEL_PATH"
    exit 1
fi

echo "------------------------------------------------"
echo "Starting STANDALONE llama-server (Port $PORT)..."
echo "Model: $MODEL_PATH"
echo "------------------------------------------------"

# Run the standalone binary (Built via install_llama_binary.sh)
./llama_cpp_source/build/bin/llama-server \
    -m "$MODEL_PATH" \
    --host "$HOST" \
    --port "$PORT" \
    -ngl "$GPU_LAYERS" \
    -c 32768 \
    -b 2048 \
    -ub 2048 \
    --flash-attn on