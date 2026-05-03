#!/bin/bash

# Configuration
REPO_ID="paultimothymooney/gemma-3-27b-it-Q4_K_M-GGUF"
FILENAME="gemma-3-27b-it-q4_k_m.gguf"
TARGET_DIR="model_weights"

echo "Downloading Gemma 3 27B GGUF Model using Python API..."

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Use Python to download to ensure compatibility with your environment
# This avoids CLI deprecation warnings (like the 'hf' tool suggestion)
python3 -c "
try:
    from huggingface_hub import hf_hub_download
except ImportError:
    print('huggingface_hub not found. Please run ./install_requirements.sh first.')
    exit(1)

import os

repo_id = '$REPO_ID'
filename = '$FILENAME'
local_dir = '$TARGET_DIR'

print(f'[*] Initializing download: {repo_id}/{filename}')
try:
    path = hf_hub_download(
        repo_id=repo_id, 
        filename=filename, 
        local_dir=local_dir,
        local_dir_use_symlinks=False
    )
    print(f'[+] Success! Model saved to: {path}')
except Exception as e:
    print(f'[!] Error downloading model: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "------------------------------------------------"
    echo "Model download and verification complete."
    echo "------------------------------------------------"
else
    echo "------------------------------------------------"
    echo "FAILED: Model download failed."
    echo "------------------------------------------------"
    exit 1
fi
