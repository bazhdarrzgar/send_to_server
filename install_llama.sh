#!/bin/bash

# Exit on error
set -e

echo "Starting llama-cpp-python installation with CUDA support..."

# 1. Ensure CUDA paths are set correctly (detected from your error log as 12.6)
export CUDA_HOME=/usr/local/cuda-12.6
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

if ! command -v nvcc &> /dev/null; then
    # Fallback to standard path if 12.6 doesn't exist
    if [ ! -d "/usr/local/cuda-12.6" ]; then
        echo "CUDA 12.6 not found at /usr/local/cuda-12.6, trying standard /usr/local/cuda..."
        export CUDA_HOME=/usr/local/cuda
        export PATH=$CUDA_HOME/bin:$PATH
        export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
    fi
fi

if ! command -v nvcc &> /dev/null; then
    echo "Error: nvcc not found. Please ensure CUDA is installed."
    exit 1
fi

echo "Found CUDA version: $(nvcc --version | grep release)"

# 2. CONFIGURE BUILD LIMITS (CRITICAL for 16GB RAM systems)
# Your system has 20 cores. If ninja/make runs 20 jobs, it will use >60GB RAM and crash.
# We limit to 2 concurrent jobs to fit within your 16GB RAM.
export MAX_JOBS=2
export CMAKE_BUILD_PARALLEL_LEVEL=2

# 3. Install llama-cpp-python with CUDA support
echo "Installing llama-cpp-python with MAX_JOBS=$MAX_JOBS..."

# Set CMAKE_ARGS for CUDA offloading
export CMAKE_ARGS="-DGGML_CUDA=on"

# Uninstall previous failed attempt to ensure clean build
pip3 uninstall -y llama-cpp-python

# Install with build from source to ensure CUDA is linked
# --no-cache-dir ensures we don't reuse a broken partial build
pip3 install llama-cpp-python[server] --verbose --no-cache-dir

echo "------------------------------------------------"
echo "llama-cpp-python installed successfully!"
echo "------------------------------------------------"
