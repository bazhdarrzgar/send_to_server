#!/bin/bash
# start_ollama_server_second.sh
# Ensures the Ollama daemon is running and the Gemma 3 27B model is loaded on GPU 1.

# Bypass system proxy for localhost connections
export no_proxy="localhost,127.0.0.1,0.0.0.0"
export NO_PROXY="localhost,127.0.0.1,0.0.0.0"

# ── Storage: redirect all Ollama data to the large drive ──────────────────────
export OLLAMA_HOME="/mnt/storage1/shko/ollama"
export OLLAMA_MODELS="/mnt/storage1/shko/ollama/Models"
mkdir -p "$OLLAMA_HOME"
mkdir -p "$OLLAMA_MODELS"

# Context window: allow up to 32 K tokens for both input and output
export OLLAMA_NUM_CTX=32768

# Configuration
MODEL_NAME="gemma3:27b"
OLLAMA_HOST="0.0.0.0"
OLLAMA_PORT=11435

echo "------------------------------------------------"
echo "  Starting / checking Ollama server (Instance 2)"
echo "  Model : $MODEL_NAME"
echo "  Host  : $OLLAMA_HOST"
echo "  Port  : $OLLAMA_PORT"
echo "  GPUs  : RTX 4090 D (CUDA_VISIBLE_DEVICES=1)"
echo "------------------------------------------------"

# Export so the Ollama process uses only GPU 1
export CUDA_VISIBLE_DEVICES=1
export OLLAMA_HOST="${OLLAMA_HOST}:${OLLAMA_PORT}"

# Note: We skip the systemd check for the second instance to avoid 
# conflicting with the primary Ollama service on port 11434.
echo "[*] Starting Ollama serve in the foreground on port ${OLLAMA_PORT}..."
exec ollama serve

# Wait until the REST API is reachable
echo "[*] Waiting for Ollama API to become available..."
for i in $(seq 1 30); do
    if curl -s http://localhost:${OLLAMA_PORT}/api/tags > /dev/null 2>&1; then
        echo "[+] Ollama API is up!"
        break
    fi
    echo "    ... attempt $i/30"
    sleep 2
done

# Pre-load the model so the first inference call is instant
echo "[*] Pre-loading model $MODEL_NAME into GPU VRAM..."
ollama run "$MODEL_NAME" "" 2>/dev/null || true

echo ""
echo "------------------------------------------------"
echo "  Ollama (Instance 2) is ready."
echo "  API endpoint : http://localhost:${OLLAMA_PORT}"
echo "  OpenAI compat: http://localhost:${OLLAMA_PORT}/v1"
echo "  Model        : $MODEL_NAME"
echo "------------------------------------------------"
