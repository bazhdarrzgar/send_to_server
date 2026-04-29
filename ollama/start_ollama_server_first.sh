#!/bin/bash
# start_ollama_server_first.sh
# Ensures the Ollama daemon is running and the Gemma 3 27B model is loaded.
# Ollama itself is the server — this script just makes sure it is up.

# Bypass system proxy for localhost connections
export no_proxy="localhost,127.0.0.1,0.0.0.0"
export NO_PROXY="localhost,127.0.0.1,0.0.0.0"

# ── Storage: redirect all Ollama data to the large drive ──────────────────────
# /home is full; /mnt/storage1/shko/ollama has the free space.
# OLLAMA_HOME controls where Ollama stores models, blobs, and the ed25519 key.
export OLLAMA_HOME="/mnt/storage1/shko/ollama"
mkdir -p "$OLLAMA_HOME"

# Configuration
MODEL_NAME="gemma3:27b"
OLLAMA_HOST="0.0.0.0"
OLLAMA_PORT=11434

echo "------------------------------------------------"
echo "  Starting / checking Ollama server"
echo "  Model : $MODEL_NAME"
echo "  Host  : $OLLAMA_HOST"
echo "  Port  : $OLLAMA_PORT"
echo "  GPUs  : Both RTX 4090 D (CUDA_VISIBLE_DEVICES=0,1)"
echo "------------------------------------------------"

# Export so the Ollama process uses both GPUs
export CUDA_VISIBLE_DEVICES=0,1
export OLLAMA_HOST="${OLLAMA_HOST}:${OLLAMA_PORT}"

# If Ollama is running as a systemd service, restart it to pick up env vars
if systemctl is-active --quiet ollama 2>/dev/null; then
    echo "[*] Ollama systemd service is active — restarting to apply env vars..."
    # Patch the systemd override so the service also knows about OLLAMA_HOME
    sudo mkdir -p /etc/systemd/system/ollama.service.d
    sudo tee /etc/systemd/system/ollama.service.d/storage.conf > /dev/null <<EOF
[Service]
Environment="OLLAMA_HOME=/mnt/storage1/shko/ollama"
Environment="CUDA_VISIBLE_DEVICES=0,1"
EOF
    sudo systemctl daemon-reload
    sudo systemctl restart ollama
    sleep 3
else
    # Otherwise start it as a foreground process (useful when running manually)
    echo "[*] Starting Ollama serve in the foreground..."
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

# Configure the model to use a 32K context window (32768 tokens)
echo "[*] Configuring $MODEL_NAME with 32K context window..."
printf "FROM $MODEL_NAME\nPARAMETER num_ctx 32768\nPARAMETER num_gpu 100\n" | ollama create "$MODEL_NAME" -f -

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
