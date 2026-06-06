#!/bin/bash

# ==============================================================================
# Multi-Domain Project Cleanup Script
# ==============================================================================
# Description: Kills all Ollama instances and Python generator processes.
# ==============================================================================

# ANSI Color Codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${YELLOW}[*] Action: Cleaning up all project processes...${NC}"

# 1. Kill all Ollama processes (Servers and Loaders)
echo -e "${RED}[-] Stopping Ollama processes...${NC}"
pkill -9 ollama > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}[+] Ollama processes terminated.${NC}"
else
    echo -e "${NC}[i] No running Ollama processes found.${NC}"
fi

# 2. Kill all Python generator processes
echo -e "${RED}[-] Stopping Python generator scripts...${NC}"
pkill -9 -f "generate_dataset" > /dev/null 2>&1
pkill -9 -f "run_generator_bg" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}[+] Python processes terminated.${NC}"
else
    echo -e "${NC}[i] No running Python generator processes found.${NC}"
fi

# 3. Final verification
echo -e "${YELLOW}[*] Final Status Check:${NC}"
ps aux | grep -E "ollama|generate_dataset" | grep -v grep

echo -e "${GREEN}Cleanup Complete.${NC}"
