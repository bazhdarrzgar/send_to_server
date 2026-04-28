#!/bin/bash
# setup_ollama_model.sh - Register the local Gemma 3 27B GGUF with Ollama
# Run this AFTER install_ollama.sh
#
# The model weight file is expected at:
#   model_weights/gemma-3-27b-it-q4_k_m.gguf
# (relative to THIS script's directory, i.e. the directory you uploaded to the server)
#
# Ollama's "create" command reads a Modelfile, imports the GGUF blob into its
# internal content-addressed store, and registers it as "gemma3:27b".
# After this runs, "ollama run gemma3:27b" works offline — no internet needed.

set -e

# ── Storage ────────────────────────────────────────────────────────────────────
export OLLAMA_HOME="/mnt/storage1/shko/ollama"
mkdir -p "$OLLAMA_HOME"

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GGUF_FILE="$SCRIPT_DIR/model_weights/gemma-3-27b-it-q4_k_m.gguf"
MODEL_NAME="gemma3:27b"
MODELFILE="$SCRIPT_DIR/Modelfile"

echo "================================================"
echo "  Ollama Model Setup (local GGUF import)"
echo "  Model : $MODEL_NAME"
echo "  GGUF  : $GGUF_FILE"
echo "  Store : $OLLAMA_HOME"
echo "================================================"

# ── Sanity checks ──────────────────────────────────────────────────────────────
if [ ! -f "$GGUF_FILE" ]; then
    echo ""
    echo "[!] ERROR: GGUF file not found at:"
    echo "    $GGUF_FILE"
    echo ""
    echo "    Make sure you transferred the file with the correct path:"
    echo "    model_weights/gemma-3-27b-it-q4_k_m.gguf"
    exit 1
fi

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[!] Ollama service does not seem to be running."
    echo "    Start it with:  sudo systemctl start ollama"
    echo "    Or manually  :  OLLAMA_HOME=$OLLAMA_HOME ollama serve"
    exit 1
fi

# ── Write a minimal Modelfile ──────────────────────────────────────────────────
echo "[*] Writing Modelfile..."
cat > "$MODELFILE" <<EOF
# Modelfile for Gemma 3 27B Instruct (Q4_K_M GGUF)
FROM $GGUF_FILE

# Recommended chat template for Gemma 3 instruct models
TEMPLATE """<start_of_turn>user
{{ .Prompt }}<end_of_turn>
<start_of_turn>model
"""

# Generation parameters
PARAMETER temperature    0.7
PARAMETER top_p          0.9
PARAMETER top_k          40
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx        8192
EOF

echo "    Modelfile written to: $MODELFILE"

# ── Import the model ───────────────────────────────────────────────────────────
echo ""
echo "[*] Running: ollama create $MODEL_NAME -f $MODELFILE"
echo "    This copies the GGUF into Ollama's blob store — may take a minute..."
echo ""

OLLAMA_HOME="$OLLAMA_HOME" ollama create "$MODEL_NAME" -f "$MODELFILE"

echo ""
echo "================================================"
echo "  SUCCESS! Model is ready."
echo ""
echo "  Quick test:"
echo "    OLLAMA_HOME=$OLLAMA_HOME ollama run $MODEL_NAME \"Hello!\""
echo ""
echo "  List registered models:"
echo "    OLLAMA_HOME=$OLLAMA_HOME ollama list"
echo ""
echo "  The model is now registered as: $MODEL_NAME"
echo "  Start the server with: python3 run_server_bg_first.py"
echo "================================================"
