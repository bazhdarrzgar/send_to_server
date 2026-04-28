#!/bin/bash
# install_requirements.sh - Python requirements for dataset generation
# Ollama runs as its own service, so we only need the OpenAI-compatible client + helpers.

set -e

echo "Updating system packages..."
sudo apt-get update

echo "Installing system dependencies..."
# psmisc provides 'fuser', used in the background manager scripts
sudo apt-get install -y psmisc python3-pip python3-venv

echo "Installing Python requirements for the project..."
# openai  - speaks to Ollama's /v1 OpenAI-compatible endpoint
# httpx   - used for fine-grained connection control in the generator
pip3 install openai httpx

echo "------------------------------------------------"
echo "Project requirements installed successfully!"
echo ""
echo "NOTE: Ollama itself is the model server."
echo "      No llama-cpp-python, huggingface_hub, or"
echo "      GGUF management libraries are needed."
echo "------------------------------------------------"
