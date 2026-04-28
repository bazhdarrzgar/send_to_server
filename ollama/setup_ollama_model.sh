#!/bin/bash
# setup_ollama_model.sh - Register the already-downloaded Gemma 3 27B with Ollama
# Run this AFTER install_ollama.sh
set -e

echo "================================================"
echo "  Ollama Model Setup"
echo "  Model: gemma3:27b"
echo "================================================"

# Check Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[!] Ollama service does not seem to be running."
    echo "    Start it with: sudo systemctl start ollama"
    echo "    Or run the service manually: ollama serve"
    exit 1
fi

echo "[*] Pulling gemma3:27b from Ollama registry..."
echo "    (If you already have the weights, Ollama will reuse the cached layers)"
ollama pull gemma3:27b

echo ""
echo "================================================"
echo "  SUCCESS! Model is ready."
echo ""
echo "  Quick test:"
echo "    ollama run gemma3:27b \"Hello!\""
echo ""
echo "  List loaded models:"
echo "    ollama list"
echo "================================================"
