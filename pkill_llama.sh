#!/bin/bash
echo "🛑 Terminating all Llama-related processes..."
pkill -9 -f "llama-server" 2>/dev/null
pkill -9 -f "llama_cpp" 2>/dev/null
pkill -9 -f "run_server_bg" 2>/dev/null
pkill -9 -f "run_generator_bg" 2>/dev/null
pkill -9 -f "generate_dataset" 2>/dev/null
fuser -k 8011/tcp 2>/dev/null
fuser -k 8012/tcp 2>/dev/null
fuser -k 8013/tcp 2>/dev/null
echo "✅ All killed."
