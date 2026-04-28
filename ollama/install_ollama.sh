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

# 2. Official Ollama installer (automatically detects CUDA and installs GPU support)
echo "[*] Running official Ollama installer..."
curl -fsSL https://ollama.com/install.sh | sh

# 3. Configure Ollama to listen on all interfaces (so the Python client can reach it)
echo "[*] Configuring Ollama to listen on 0.0.0.0:11434..."
sudo mkdir -p /etc/systemd/system/ollama.service.d
cat <<EOF | sudo tee /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
# Use both GPUs
Environment="CUDA_VISIBLE_DEVICES=0,1"
EOF

# 4. Reload systemd and start the Ollama service
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
