#!/bin/bash

# ==============================================================================
# Ollama Model GPU Loader & Verification Script (GPU 0)
# ==============================================================================
# Description: This script triggers the loading of an Ollama model into GPU 0
#              memory in the background and verifies the status.
# ==============================================================================

# --- Configuration ---
MODEL_NAME="qwen3.6:35b"
LOG_FILE="ollama_gpu_0_load.txt"
GPU_ID=0  # The index of the GPU to use
OLLAMA_PORT=11434

# ANSI Color Codes for Premium UI
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Header
echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "${CYAN}${BOLD}       OLLAMA GPU 0 LOAD & TEST UTILITY               ${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"

# Initialize log file
echo "--- Ollama GPU 0 Load Session: $(date) ---" > "$LOG_FILE"

# --- Function: Ensure Server is Running ---
ensure_server_running() {
    echo -e "${YELLOW}[*] Action: Checking Ollama server status on port $OLLAMA_PORT...${NC}"
    
    if curl -s "http://localhost:$OLLAMA_PORT/api/tags" > /dev/null 2>&1; then
        echo -e "${GREEN}[+] Ollama server is already active on port $OLLAMA_PORT.${NC}"
        return 0
    fi

    echo -e "${YELLOW}[!] Ollama server not detected on port $OLLAMA_PORT. Starting isolated instance...${NC}"
    
    # CRITICAL: Set CUDA_VISIBLE_DEVICES for the SERVER process
    export CUDA_VISIBLE_DEVICES=$GPU_ID
    export OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT"
    
    # Start server in background
    nohup ollama serve >> "$LOG_FILE" 2>&1 &

    # Wait and verify status
    echo -n "Waiting for API availability"
    for i in {1..20}; do
        echo -n "."
        if curl -s "http://localhost:$OLLAMA_PORT/api/tags" > /dev/null 2>&1; then
            echo -e "\n${GREEN}[SUCCESS] Ollama server (GPU $GPU_ID) is up!${NC}" | tee -a "$LOG_FILE"
            return 0
        fi
        sleep 2
    done

    echo -e "\n${RED}[ERROR] Server failed to start within 40 seconds.${NC}" | tee -a "$LOG_FILE"
    exit 1
}

# --- Function: Load Model ---
load_to_gpu_bg() {
    echo -e "${YELLOW}[*] Action: Triggering model load for '$MODEL_NAME' on port $OLLAMA_PORT...${NC}"
    
    # Trigger a run with empty input to force the model into VRAM
    export OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT"
    nohup ollama run $MODEL_NAME "" >> "$LOG_FILE" 2>&1 &
    
    BG_PID=$!
    echo -e "${GREEN}[+] Load command dispatched (PID: $BG_PID).${NC}" | tee -a "$LOG_FILE"
}

# --- Function: Verification Test ---
run_verification_test() {
    echo -e "\n${YELLOW}[*] Action: Verifying GPU VRAM status...${NC}"
    echo -n "Waiting for model initialization"
    
    MAX_ATTEMPTS=12
    SUCCESS=false
    
    for ((i=1; i<=MAX_ATTEMPTS; i++)); do
        echo -n "."
        if OLLAMA_HOST="localhost:$OLLAMA_PORT" ollama ps 2>/dev/null | grep -q "$MODEL_NAME"; then
            echo -e "\n${GREEN}${BOLD}[SUCCESS] Model '$MODEL_NAME' is active in GPU memory!${NC}" | tee -a "$LOG_FILE"
            SUCCESS=true
            break
        fi
        sleep 5
    done

    if [ "$SUCCESS" = true ]; then
        echo -e "${BLUE}------------------------------------------------------${NC}"
        echo -e "${BOLD}Current GPU Load Status (Port $OLLAMA_PORT):${NC}"
        OLLAMA_HOST="localhost:$OLLAMA_PORT" ollama ps | grep -E "NAME|${MODEL_NAME}"
        echo -e "${BLUE}------------------------------------------------------${NC}"
        return 0
    else
        echo -e "\n${RED}${BOLD}[FAILURE] Model verification timed out.${NC}" | tee -a "$LOG_FILE"
        return 1
    fi
}

# --- Main Execution ---
ensure_server_running
load_to_gpu_bg
run_verification_test

echo -e "\n${CYAN}Done.${NC}"
