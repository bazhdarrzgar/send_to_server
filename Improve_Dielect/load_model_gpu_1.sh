#!/bin/bash

# ==============================================================================
# Ollama Model GPU Loader & Verification Script
# ==============================================================================
# Description: This script triggers the loading of an Ollama model into GPU 
#              memory in the background and verifies the status.
# Author: Antigravity AI
# ==============================================================================

# --- Configuration ---
# You can change these variables to match your environment
MODEL_NAME="gemma3:27b"
LOG_FILE="ollama_gpu_1_load.txt"
GPU_ID=1  # The index of the GPU to use
OLLAMA_PORT=11435

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
echo -e "${CYAN}${BOLD}       OLLAMA GPU LOAD & TEST UTILITY                 ${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"

# Initialize log file
echo "--- Ollama GPU Load Session: $(date) ---" > "$LOG_FILE"

# --- Function: Ensure Server is Running ---
ensure_server_running() {
    echo -e "${YELLOW}[*] Action: Checking Ollama server status...${NC}"
    
    # Check if reachable
    if curl -s "http://localhost:$OLLAMA_PORT/api/tags" > /dev/null 2>&1; then
        echo -e "${GREEN}[+] Ollama server is already active.${NC}"
        return 0
    fi

    echo -e "${YELLOW}[!] Ollama server not detected. Attempting to start...${NC}"
    
    # Check if the user's custom start script exists in the same directory
    if [ -f "./start_ollama_server_second.sh" ]; then
        echo -e "${CYAN}[i] Found 'start_ollama_server_second.sh'. Using it to initialize...${NC}"
        # Run in background
        nohup bash ./start_ollama_server_second.sh >> "$LOG_FILE" 2>&1 &
    else
        echo -e "${CYAN}[i] No start script found. Running 'ollama serve' directly...${NC}"
        # Set basic environment just in case
        export OLLAMA_HOST="0.0.0.0:$OLLAMA_PORT"
        nohup ollama serve >> "$LOG_FILE" 2>&1 &
    fi

    # Wait and verify status
    echo -n "Waiting for API availability"
    for i in {1..20}; do
        echo -n "."
        if curl -s "http://localhost:$OLLAMA_PORT/api/tags" > /dev/null 2>&1; then
            echo -e "\n${GREEN}[SUCCESS] Ollama server is up and responding!${NC}" | tee -a "$LOG_FILE"
            return 0
        fi
        sleep 2
    done

    echo -e "\n${RED}[ERROR] Server failed to start within 40 seconds.${NC}" | tee -a "$LOG_FILE"
    exit 1
}

# --- Function: Load Model ---
load_to_gpu_bg() {
    echo -e "${YELLOW}[*] Action: Loading '$MODEL_NAME' to GPU $GPU_ID in background...${NC}"
    
    # Trigger loading using 'ollama run' with an empty input
    # We must set OLLAMA_HOST to talk to the correct port (11435)
    export OLLAMA_HOST="localhost:$OLLAMA_PORT"
    nohup bash -c "export CUDA_VISIBLE_DEVICES=$GPU_ID; export OLLAMA_HOST=localhost:$OLLAMA_PORT; ollama run $MODEL_NAME ''" >> "$LOG_FILE" 2>&1 &
    
    BG_PID=$!
    echo -e "${GREEN}[+] Load process dispatched (PID: $BG_PID).${NC}" | tee -a "$LOG_FILE"
    echo -e "${CYAN}[i] Logging output to: $LOG_FILE${NC}"
}

# --- Function: Verification Test ---
run_verification_test() {
    echo -e "\n${YELLOW}[*] Action: Verifying GPU VRAM status...${NC}"
    echo -n "Waiting for model initialization"
    
    # Polling for up to 60 seconds (12 attempts * 5 seconds)
    MAX_ATTEMPTS=12
    SUCCESS=false
    
    for ((i=1; i<=MAX_ATTEMPTS; i++)); do
        echo -n "."
        # Check 'ollama ps' on the specific host/port
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
        echo -e "${YELLOW}[!] Check '$LOG_FILE' for potential error messages.${NC}"
        return 1
    fi
}

# --- Main Execution ---
ensure_server_running
load_to_gpu_bg
run_verification_test

echo -e "\n${CYAN}Done.${NC}"
