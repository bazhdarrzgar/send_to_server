#!/bin/bash
# test_ollama.sh
# Tests whether the Ollama server and gemma3:27b model are working correctly.
# Run this AFTER start_ollama_server_first.sh has been executed.

# ── Config (must match start_ollama_server_first.sh) ──────────────────────────
MODEL_NAME="gemma3:27b"
OLLAMA_PORT=11434
BASE_URL="http://localhost:${OLLAMA_PORT}"

# ── Helpers ───────────────────────────────────────────────────────────────────
PASS="\e[32m[PASS]\e[0m"
FAIL="\e[31m[FAIL]\e[0m"
INFO="\e[34m[INFO]\e[0m"
WARN="\e[33m[WARN]\e[0m"

pass() { echo -e "${PASS} $1"; }
fail() { echo -e "${FAIL} $1"; FAILED=$((FAILED + 1)); }
info() { echo -e "${INFO} $1"; }
warn() { echo -e "${WARN} $1"; }

FAILED=0

echo ""
echo "================================================"
echo "  Ollama Test Suite"
echo "  Model  : $MODEL_NAME"
echo "  API    : $BASE_URL"
echo "  $(date)"
echo "================================================"
echo ""

# ── Test 1: API reachability ──────────────────────────────────────────────────
info "Test 1 — API reachability..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/api/tags")
if [ "$HTTP_CODE" = "200" ]; then
    pass "Ollama API is reachable (HTTP $HTTP_CODE)"
else
    fail "Ollama API is NOT reachable (HTTP $HTTP_CODE). Is the server running?"
    echo ""
    echo "Run ./start_ollama_server_first.sh first, then retry."
    exit 1
fi

# ── Test 2: Model is listed ───────────────────────────────────────────────────
info "Test 2 — Model '$MODEL_NAME' is loaded..."
MODELS=$(curl -s "${BASE_URL}/api/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
if echo "$MODELS" | grep -q "^${MODEL_NAME}$"; then
    pass "Model '$MODEL_NAME' found in Ollama"
else
    warn "Model '$MODEL_NAME' not listed yet (may still be loading or not pulled)."
    info "Available models:"
    echo "$MODELS" | sed 's/^/    /'
    fail "Model check — '$MODEL_NAME' not available"
fi

# ── Test 3: Context window is 32 K ────────────────────────────────────────────
info "Test 3 — Context window reported as 32768..."
MODEL_INFO=$(curl -s -X POST "${BASE_URL}/api/show" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"${MODEL_NAME}\"}")
CTX=$(echo "$MODEL_INFO" | grep -o '"num_ctx":[0-9]*' | grep -o '[0-9]*')
if [ "$CTX" = "32768" ]; then
    pass "Context window is 32768 tokens"
elif [ -n "$CTX" ]; then
    warn "Context window is $CTX (expected 32768). Check OLLAMA_NUM_CTX export."
    FAILED=$((FAILED + 1))
else
    warn "Could not read num_ctx from model info (model may not be loaded yet)."
fi

# ── Test 4: Native API inference ──────────────────────────────────────────────
info "Test 4 — Native /api/generate inference..."
RESPONSE=$(curl -s -X POST "${BASE_URL}/api/generate" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"${MODEL_NAME}\",
        \"prompt\": \"Reply with exactly one sentence: confirm you are working.\",
        \"stream\": false,
        \"options\": { \"num_predict\": 60 }
    }")

NATIVE_REPLY=$(echo "$RESPONSE" | grep -o '"response":"[^"]*"' | cut -d'"' -f4)
if [ -n "$NATIVE_REPLY" ]; then
    pass "Native API inference OK"
    echo "    Model reply: $NATIVE_REPLY"
else
    fail "Native API inference returned no response"
    info "Raw response: $RESPONSE"
fi

# ── Test 5: OpenAI-compatible endpoint ────────────────────────────────────────
info "Test 5 — OpenAI-compatible /v1/chat/completions..."
OAI_RESPONSE=$(curl -s -X POST "${BASE_URL}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ollama" \
    -d "{
        \"model\": \"${MODEL_NAME}\",
        \"messages\": [
            {\"role\": \"user\", \"content\": \"Reply with exactly one sentence: confirm the OpenAI-compatible endpoint works.\"}
        ],
        \"max_tokens\": 60
    }")

OAI_REPLY=$(echo "$OAI_RESPONSE" | grep -o '"content":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -n "$OAI_REPLY" ]; then
    pass "OpenAI-compatible endpoint OK"
    echo "    Model reply: $OAI_REPLY"
else
    fail "OpenAI-compatible endpoint returned no response"
    info "Raw response: $OAI_RESPONSE"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "================================================"
if [ "$FAILED" -eq 0 ]; then
    echo -e "  \e[32mAll tests passed! Ollama is ready.\e[0m"
else
    echo -e "  \e[31m$FAILED test(s) failed. See output above.\e[0m"
fi
echo "================================================"
echo ""
exit $FAILED
