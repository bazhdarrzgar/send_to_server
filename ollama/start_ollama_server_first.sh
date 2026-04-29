#!/bin/bash
# start_ollama_server_first.sh
# Ensures the Ollama daemon is running and the Gemma 3 27B model is loaded.
# Ollama itself is the server — this script just makes sure it is up.

# Bypass system proxy for localhost connections
export no_proxy="localhost,127.0.0.1,0.0.0.0"
export NO_PROXY="localhost,127.0.0.1,0.0.0.0"

# ── Storage: redirect all Ollama data to the large drive ──────────────────────
# /home is full; /mnt/storage1/shko/ollama has the free space.
export OLLAMA_HOME="/mnt/storage1/shko/ollama"
export OLLAMA_MODELS="$OLLAMA_HOME/models"
mkdir -p "$OLLAMA_MODELS"

# Configuration
MODEL_NAME="gemma3:27b"
OLLAMA_HOST="0.0.0.0"
OLLAMA_PORT=11434

# Performance and GPU Settings
export CUDA_VISIBLE_DEVICES=0,1
export OLLAMA_NUM_PARALLEL=2
export OLLAMA_MAX_LOADED_MODELS=1

# Finalize host
export OLLAMA_HOST="${OLLAMA_HOST}:${OLLAMA_PORT}"

# If Ollama is running as a systemd service, restart it to pick up env vars
if systemctl is-active --quiet ollama 2>/dev/null; then
    echo "[*] Ollama systemd service is active — restarting to apply env vars..."
    # Patch the systemd override so the service also knows about storage and performance
    sudo mkdir -p /etc/systemd/system/ollama.service.d
    sudo tee /etc/systemd/system/ollama.service.d/storage.conf > /dev/null <<EOF
[Service]
Environment="OLLAMA_HOME=$OLLAMA_HOME"
Environment="OLLAMA_MODELS=$OLLAMA_MODELS"
Environment="CUDA_VISIBLE_DEVICES=0,1"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_HOST=$OLLAMA_HOST"
EOF
    sudo systemctl daemon-reload
    sudo systemctl restart ollama
    sleep 3
else
    # Otherwise start it as a foreground process (useful when running manually)
    echo "[*] Starting Ollama serve in the foreground..."
    # Ensure OLLAMA_MODELS is explicitly set for the exec process
    exec ollama serve
fi

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
echo "  Ollama is ready."
echo "  API endpoint : http://localhost:${OLLAMA_PORT}"
echo "  OpenAI compat: http://localhost:${OLLAMA_PORT}/v1"
echo "  Model        : $MODEL_NAME"
echo "------------------------------------------------"
