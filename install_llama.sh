#!/bin/bash

# Exit on error
set -e

echo "Starting llama-cpp-python installation with CUDA support..."

# Check if CUDA is available
if ! command -v nvcc &> /dev/null; then
    echo "Warning: nvcc not found. Attempting to add /usr/local/cuda/bin to PATH..."
    export PATH=/usr/local/cuda/bin:$PATH
    export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
fi

if ! command -v nvcc &> /dev/null; then
    echo "Error: CUDA toolkit (nvcc) not found. Please install CUDA before running this script."
    echo "You can try: sudo apt-get install -y nvidia-cuda-toolkit"
    exit 1
fi

echo "Found CUDA version: $(nvcc --version | grep release)"

# Install llama-cpp-python with CUDA support
# We use -DGGML_CUDA=on for the newer versions of llama-cpp-python
echo "Installing llama-cpp-python[server] with CUDA support..."

# Set CMAKE_ARGS for CUDA offloading
export CMAKE_ARGS="-DGGML_CUDA=on"

# Uninstall previous version if any to ensure clean build
pip3 uninstall -y llama-cpp-python

# Install with build from source to ensure CUDA is linked
pip3 install llama-cpp-python[server] --verbose --no-cache-dir

echo "------------------------------------------------"
echo "llama-cpp-python installed successfully!"
echo "You can verify installation with: python3 -m llama_cpp.server --help"
echo "------------------------------------------------"
