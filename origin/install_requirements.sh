#!/bin/bash

# Exit on error
set -e

echo "Updating system packages..."
sudo apt-get update

echo "Installing system dependencies..."
# psmisc provides 'fuser', which is used in the background manager scripts
sudo apt-get install -y psmisc python3-pip python3-venv git-lfs

echo "Installing Python requirements for the project..."
# Install requirements for the generation and management scripts
pip3 install openai httpx huggingface_hub

echo "------------------------------------------------"
echo "Project requirements installed successfully!"
echo "Note: If you plan to use a virtual environment, run these inside it."
echo "------------------------------------------------"
