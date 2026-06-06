#!/usr/bin/env python3
"""
generate_dataset_first.py (Ollama version)
Edited to read JSON files from kmc_part, fix grammar/dialect of instruction and response,
check for quality, and output to kmc_part_output with _FINAL.json.
Keeps original structure and parameters.
Model: gemma4:31b
"""

import os
import re
import json
import time
import httpx
from openai import OpenAI

# ─────────────────────────── Bypass Proxy ─────────────────────────────────────
os.environ["no_proxy"] = "localhost,127.0.0.1"
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

# ─────────────────────────── Configuration ────────────────────────────────────
BASE_DATA_DIR   = "kmc_part"
BASE_OUTPUT_DIR = "kmc_part_output"

MODEL_NAME      = "gemma4:31b"

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    http_client=httpx.Client(proxy=None),
)

# ──────────────────────────── Prompt Templates ────────────────────────────────
def build_fix_prompt(instruction: str, response: str) -> str:
    return f"""Act as an expert Kurdish linguist and subject-matter expert.
Your task is to significantly improve and refine the following question and response:
1. **Grammar & Dialect**: Correct all dialectal, grammatical, and spelling issues. The output MUST be in high-quality, formal Central Kurdish (Sorani).
2. **Completeness & Accuracy**: Provide AS MUCH DETAIL AS POSSIBLE. If the question or response lacks meaning, context, or sufficient details, rewrite and expand them extensively. Add every piece of necessary and relevant information so that they form an exhaustive, comprehensive, and perfect QA pair. Do not summarize; elaborate deeply.
3. **Numerals**: Convert any English (Western) numbers (0-9) to Kurdish (Eastern Arabic) numbers (٠, ١, ٢, ٣, ٤, ٥, ٦, ٧, ٨, ٩).

Return a valid JSON object EXACTLY in this format:
{{
  "instruction": "<fixed and highly enriched question>",
  "response": "<fixed, extremely detailed, and enriched response>"
}}
Do NOT include any markdown formatting, explanations, or introductory text. Output only the JSON.

Original:
Question: {instruction}
Response: {response}
"""

def build_check_prompt(instruction: str, response: str) -> str:
    return f"""Act as an expert Kurdish linguist and quality assurance reviewer.
Evaluate the following question and response pair. Check rigorously for:
1. **Grammar & Dialect**: Is it written in flawless, formal Central Kurdish (Sorani) without grammatical errors?
2. **Completeness & Depth**: Are the question and response extremely detailed, highly expansive, and thoroughly informative? Does it contain as much detail as possible?
3. **Numerals**: Are all numbers written using Kurdish (Eastern Arabic) numerals (٠-٩) instead of English numerals (0-9)?

If they are absolutely perfect, highly detailed, and meet all three criteria, return a JSON object containing ONLY: {{"status": "good"}}
If they lack depth, details, or have ANY grammar/numeral issues, fix them completely by expanding and enriching the response with as much relevant detail as possible, and return the perfected text in this JSON format:
{{
  "status": "fixed",
  "instruction": "<perfected and highly detailed question>",
  "response": "<perfected and extremely detailed response>"
}}
Do NOT include any markdown formatting, code fences, or explanations. Output only the JSON.

Text to evaluate:
Question: {instruction}
Response: {response}
"""

def estimate_tokens(text: str) -> int:
    # A rough estimate for Kurdish CKB where 1 token is around 2-3 characters.
    return len(text) // 2

def call_model(prompt: str, base_max_tokens: int = 4096) -> str:
    retry_wait = 30
    
    input_tokens = estimate_tokens(prompt)
    # Give the model huge room to output an extremely enriched, longer response
    dynamic_max_tokens = max(base_max_tokens, input_tokens * 5)
    
    print(f"(Input ~{input_tokens} tokens, Output limit {dynamic_max_tokens})", end=" ", flush=True)
    
    while True:
        try:
            res = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=dynamic_max_tokens,
            )
            return res.choices[0].message.content
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError) as e:
            print(f"\\n    ❌  Server connection lost: {e}")
            print(f"    ⏳ Waiting {retry_wait}s for server to come back online...")
            time.sleep(retry_wait)
        except Exception as e:
            print(f"\\n    ❌  Error calling model: {e}")
            print(f"    ⏳ Retrying in {retry_wait}s...")
            time.sleep(retry_wait)

def parse_json_object(raw: str) -> dict:
    if not raw or not isinstance(raw, str):
        return {}
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = cleaned.replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start:end+1])
        except json.JSONDecodeError:
            pass
    return {}

def process_single_item(item: dict) -> dict:
    original_instruction = item.get("instruction", "")
    original_response = item.get("response", "")
    
    if not original_instruction and not original_response:
        return item
        
    print("      -> Phase 1: Fixing grammar/dialect...", end=" ", flush=True)
    prompt1 = build_fix_prompt(original_instruction, original_response)
    raw1 = call_model(prompt1)
    fixed = parse_json_object(raw1)
    
    current_inst = fixed.get("instruction", original_instruction)
    current_resp = fixed.get("response", original_response)
    print("Done")
    
    print("      -> Phase 2: Quality check...", end=" ", flush=True)
    prompt2 = build_check_prompt(current_inst, current_resp)
    raw2 = call_model(prompt2)
    checked = parse_json_object(raw2)
    
    if checked.get("status") == "good":
        final_inst = current_inst
        final_resp = current_resp
        print("Good")
    else:
        final_inst = checked.get("instruction", current_inst)
        final_resp = checked.get("response", current_resp)
        print("Fixed again")
        
    item["instruction"] = final_inst
    item["response"] = final_resp
    return item

def process_file(in_path: str, out_path: str):
    print(f"\\n  📄 Processing: {os.path.basename(in_path)}")
    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    if not isinstance(data, list):
        print("    ⚠️  Expected a JSON array, skipping.")
        return
        
    updated_data = []
    for i, item in enumerate(data):
        print(f"    Item {i+1}/{len(data)}:")
        if isinstance(item, dict):
            updated_item = process_single_item(item)
            updated_data.append(updated_item)
        else:
            updated_data.append(item)
        
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Saved finalized records -> {os.path.basename(out_path)}")

# ──────────────────────────────── Main ────────────────────────────────────────
def main():
    print(f"🚀 Starting dataset dialect/grammar fix")
    print(f"📂 Input : {BASE_DATA_DIR}")
    print(f"📂 Output: {BASE_OUTPUT_DIR}")
    print(f"🧠 Model : {MODEL_NAME}")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, BASE_DATA_DIR)
    output_dir = os.path.join(script_dir, BASE_OUTPUT_DIR)
    
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(input_dir):
        print(f"❌ Input directory '{input_dir}' not found. Please create it and add JSON files.")
        return
        
    files = sorted([f for f in os.listdir(input_dir) if f.endswith(".json")])
    if not files:
        print(f"⚠️  No JSON files found in {input_dir}")
        return
        
    for fname in files:
        in_path = os.path.join(input_dir, fname)
        base_name = os.path.splitext(fname)[0]
        out_path = os.path.join(output_dir, f"{base_name}_FINAL.json")
        
        if os.path.exists(out_path):
            print(f"\\n  ✅ Already finalized: {fname} — skipping.")
            continue
            
        process_file(in_path, out_path)
        
    print(f"\\n{'═'*60}")
    print("🎉 All done! Look for *_FINAL.json files inside kmc_part_output.")
    print(f"{'═'*60}\\n")

if __name__ == "__main__":
    main()