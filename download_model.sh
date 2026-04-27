#!/bin/bash

# Configuration
REPO_ID="paultimothymooney/gemma-3-27b-it-Q4_K_M-GGUF"
FILENAME="gemma-3-27b-it-q4_k_m.gguf"
TARGET_DIR="model_weights"

echo "Downloading Gemma 3 27B GGUF Model..."
echo "Repo: $REPO_ID"
echo "File: $FILENAME"

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Check if huggingface-cli is installed
if ! command -v huggingface-cli &> /dev/null; then
    echo "huggingface-cli not found. Installing huggingface_hub..."
    pip3 install huggingface_hub
fi

# Download the model file specifically
# We use local-dir to place it in the model_weights folder
huggingface-cli download "$REPO_ID" "$FILENAME" --local-dir "$TARGET_DIR" --local-dir-use-symlinks False

echo "------------------------------------------------"
echo "Model downloaded successfully to $TARGET_DIR/$FILENAME"
echo "------------------------------------------------"
