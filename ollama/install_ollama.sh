#!/bin/bash
# install_ollama.sh - Install Ollama on Ubuntu (CUDA/GPU enabled)
set -e

echo "================================================"
echo "  Ollama Installation Script"
echo "  Target: Ubuntu 20.04 | Dual RTX 4090 D"
echo "================================================"

# 1. Install CURL if not present
echo "[*] Ensuring curl is installed..."
sudo apt-get update -y
sudo apt-get install -y curl

# 2. Remove any existing Ollama installation before reinstalling
echo ""
echo "[*] Checking for existing Ollama installation..."
OLLAMA_BIN=$(command -v ollama || echo "/usr/local/bin/ollama")

if [ -f "$OLLAMA_BIN" ] || systemctl list-unit-files | grep -q ollama.service; then
    echo "[!] Ollama installation detected — removing it completely for a clean reinstall..."

    # Stop and disable the service
    sudo systemctl stop ollama 2>/dev/null || true
    sudo systemctl disable ollama 2>/dev/null || true

    # Remove the binary
    if [ -f "$OLLAMA_BIN" ]; then
        sudo rm -f "$OLLAMA_BIN"
        echo "    [✓] Binary removed ($OLLAMA_BIN)"
    fi
    # Also check /usr/bin just in case
    sudo rm -f /usr/bin/ollama

    # Remove the systemd unit and any drop-in overrides
    sudo rm -f /etc/systemd/system/ollama.service
    sudo rm -rf /etc/systemd/system/ollama.service.d
    sudo systemctl daemon-reload
    echo "    [✓] Systemd unit and overrides removed"

    # Remove system data directory (libraries/runners)
    if [ -d /usr/share/ollama ]; then
        sudo rm -rf /usr/share/ollama
        echo "    [✓] System data directory /usr/share/ollama removed"
    fi

    # Remove the ollama system user/group
    if id -u ollama &>/dev/null; then
        sudo userdel ollama 2>/dev/null || true
        echo "    [✓] System user 'ollama' removed"
    fi
    if getent group ollama &>/dev/null; then
        sudo groupdel ollama 2>/dev/null || true
        echo "    [✓] System group 'ollama' removed"
    fi

    echo "[+] Old Ollama installation removed."
else
    echo "[+] No existing Ollama installation found — proceeding with fresh install."
fi
echo ""

# 3. Fresh Ollama install (automatically detects CUDA and installs GPU support)
echo "[*] Running official Ollama installer..."
curl -fsSL https://ollama.com/install.sh | sh

# 3. Configure Ollama storage on the large drive (/home is full)
echo "[*] Creating Ollama storage directory on /mnt/storage1/shko/ollama ..."
export OLLAMA_HOME="/mnt/storage1/shko/ollama"
sudo mkdir -p "$OLLAMA_HOME"
# Make the directory owned by the user that will run ollama
sudo chown -R "$USER":"$USER" "$OLLAMA_HOME"

# 4. Configure Ollama to listen on all interfaces (so the Python client can reach it)
echo "[*] Configuring Ollama systemd service (host, GPUs, storage)..."
sudo mkdir -p /etc/systemd/system/ollama.service.d
cat <<EOF | sudo tee /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
# Use both GPUs
Environment="CUDA_VISIBLE_DEVICES=0,1"
# Store all Ollama data (models, blobs, keys) on the large drive
Environment="OLLAMA_HOME=/mnt/storage1/shko/ollama"
EOF

# 5. Reload systemd and start the Ollama service
echo "[*] Enabling and starting Ollama service..."
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl restart ollama

echo ""
echo "================================================"
echo "  SUCCESS! Ollama is installed and running."
echo "  Service status: sudo systemctl status ollama"
echo "  API endpoint  : http://localhost:11434"
echo "================================================"
echo ""
echo "  NEXT STEPS:"
echo "  1. Run ./setup_ollama_model.sh    <- registers Gemma 3 27B"
echo "  2. Run python3 run_server_bg_first.py  <- starts the generator"
echo "================================================"
