#!/bin/bash
# install_llama_binary.sh - Standalone C++ Build
set -e

echo "Building standalone llama.cpp binary (Stable Native Version)..."

# 1. Install build tools
sudo apt-get update
sudo apt-get install -y build-essential cmake git libcurl4-openssl-dev

# 2. Set CUDA paths (Detected 12.6)
export CUDA_HOME=/usr/local/cuda-12.6
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

if ! command -v nvcc &> /dev/null; then
    echo "Error: nvcc not found. Please ensure CUDA 12.6 is installed."
    exit 1
fi

# 3. Clone and build
# We clone into a subfolder 'llama_binary' to keep things clean
if [ ! -d "llama_cpp_source" ]; then
    echo "[*] Cloning llama.cpp repository..."
    git clone https://github.com/ggerganov/llama.cpp llama_cpp_source
fi

cd llama_cpp_source
mkdir -p build
cd build

echo "[*] Configuring with CUDA support..."
# Limit to 2 jobs for 16GB RAM safety
cmake .. -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89
echo "[*] Compiling llama-server (this may take a few minutes)..."
cmake --build . --config Release --target llama-server -j 2

echo "------------------------------------------------"
echo "SUCCESS! llama-server binary is ready."
echo "Binary path: $(pwd)/bin/llama-server"
echo "------------------------------------------------"
