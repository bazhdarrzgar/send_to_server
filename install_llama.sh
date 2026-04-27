#!/bin/bash

# Exit on error
set -e

echo "Starting llama-cpp-python installation with CUDA support (Anaconda Fix)..."

# 1. FORCE SYSTEM TOOLCHAIN
# This prevents Anaconda's 'compiler_compat' from causing "undefined reference" errors
export CC=/usr/bin/gcc
export CXX=/usr/bin/g++

# 2. Set CUDA paths (Detected version 12.6)
export CUDA_HOME=/usr/local/cuda-12.6
export PATH=$CUDA_HOME/bin:$PATH
# Prioritize system libraries to fix the libgomp/libpthread issues
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

if ! command -v nvcc &> /dev/null; then
    echo "Error: nvcc not found. Please ensure CUDA is installed."
    exit 1
fi

echo "Found CUDA version: $(nvcc --version | grep release)"

# 3. CONFIGURE BUILD LIMITS (For 16GB RAM)
export MAX_JOBS=2
export CMAKE_BUILD_PARALLEL_LEVEL=2

# 4. ENHANCED CMAKE ARGS
# -DGGML_CUDA=on: Enables GPU
# CMAKE_EXE_LINKER_FLAGS: Forces linking against system libraries to fix GOMP/pthread errors
export CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_EXE_LINKER_FLAGS='-L/lib/x86_64-linux-gnu -L/usr/lib/x86_64-linux-gnu'"

echo "Installing llama-cpp-python with MAX_JOBS=$MAX_JOBS..."

# Uninstall previous failed attempt to ensure clean build
pip3 uninstall -y llama-cpp-python

# Install with build from source and verbose logging
pip3 install llama-cpp-python[server] --verbose --no-cache-dir

echo "------------------------------------------------"
echo "llama-cpp-python installed successfully!"
echo "------------------------------------------------"
