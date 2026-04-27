#!/bin/bash

# Bypass system proxy for localhost connections
export no_proxy="localhost,127.0.0.1,0.0.0.0"
export NO_PROXY="localhost,127.0.0.1,0.0.0.0"

# Configuration
# Default model path specified for Gemma 3 27B
MODEL_PATH="model_weights/gemma-3-27b-it-q4_k_m.gguf"
HOST="0.0.0.0"
PORT=8010
GPU_LAYERS=-1  # -1 means offload all layers to GPU (RTX Pro 6000)
CONTEXT_SIZE=131072 # Full context size for Gemma 3 (128k)

# Check if model path is provided as an argument (overrides default)
if [ ! -z "$1" ]; then
    MODEL_PATH="$1"
fi

# Check if model file exists
if [ ! -f "$MODEL_PATH" ]; then
    echo "Error: Model file not found at $MODEL_PATH"
    echo "Please ensure the model path is correct."
    exit 1
fi

echo "------------------------------------------------"
echo "Starting llama-cpp-python server..."
echo "Model: $MODEL_PATH"
echo "Host:  $HOST"
echo "Port:  $PORT"
echo "GPU:   Offloading all layers ($GPU_LAYERS)"
echo "Context size: $CONTEXT_SIZE"
echo "Environment: Using your current active environment"
echo "------------------------------------------------"

# Run the server using the python3 in your PATH
python3 -m llama_cpp.server \
    --model "$MODEL_PATH" \
    --host "$HOST" \
    --port "$PORT" \
    --n_gpu_layers "$GPU_LAYERS" \
    --n_ctx "$CONTEXT_SIZE" \
    --flash_attn True \
    --chat_format gemma