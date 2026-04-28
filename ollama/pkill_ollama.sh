#!/bin/bash
# pkill_ollama.sh - Stop all Ollama and dataset-generator processes

echo "🛑 Terminating all Ollama and generator processes..."

# Stop the systemd Ollama service (if running)
if systemctl is-active --quiet ollama 2>/dev/null; then
    echo "  [*] Stopping ollama systemd service..."
    sudo systemctl stop ollama
fi

# Kill any manually started ollama serve processes
pkill -9 -f "ollama serve"    2>/dev/null || true
pkill -9 -f "run_server_bg"   2>/dev/null || true
pkill -9 -f "run_generator_bg" 2>/dev/null || true
pkill -9 -f "generate_dataset" 2>/dev/null || true

# Free the Ollama default port just in case
fuser -k 11434/tcp 2>/dev/null || true

echo "✅ All killed."
