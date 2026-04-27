#!/usr/bin/env python3
"""
generate_dataset_second.py (Optimized Async Version) - Second Dataset Instance
"""

import os
import re
import json
import asyncio
import httpx
from openai import AsyncOpenAI
import time

# ─────────────────────────── Bypass Proxy ─────────────────────────────────────
os.environ["no_proxy"] = "localhost,127.0.0.1"
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

# ─────────────────────────── Configuration ────────────────────────────────────
DATA_DIR   = "UKH-AIIC-KA_Just_TXT_file/part2"
OUTPUT_DIR = "UKH-AIIC-KA_Just_TXT_file_Output/part2" 
MODEL_NAME = "gemma-3-27b-it"
NUM_RUNS   = 1

# llama-cpp-python server address (Second Instance: Port 8021)
client = AsyncOpenAI(
    base_url="http://localhost:8021/v1",
    api_key="token-not-needed",
    http_client=httpx.AsyncClient(proxy=None, timeout=None),
)

MAX_CONCURRENT_REQUESTS = 2
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# ──────────────────────────── Prompt Template ─────────────────────────────────

def build_prompt(text: str) -> str:
    return f"""Act as an expert Kurdish linguist and data engineer.
Analyze the following text and determine its category (e.g., History, Medical, Mathematics, Technology, Literature, Science, etc.).
Then, generate high-quality, information-rich question-and-answer pairs based on the text.

Return a valid JSON array where EVERY object has exactly this structure:
{{
  "id": "<unique uuid or sequential string>",
  "category": "<identified category name (e.g., History, Medical, Mathematics, Technology, Literature, Science, etc.)>",
  "question": "<question in Central Kurdish (Sorani) — formal, academic level>",
  "response": "<detailed answer in Central Kurdish (Sorani) — formal, academic level>",
  "document": {{
    "title": "<title of the document if identifiable, else empty string>",
    "source_url": "<URL if present in the text, else empty string>",
    "publication_date": "<date if present in the text, else empty string>"
  }}
}}

Rules:
- Category: Identify the category accurately from the text.
- Language: Central Kurdish (Sorani) ONLY. Perfect grammar and spelling.
- Grammar: Formal and academic level. Correct any errors or colloquialisms from the source.
- Content: Extract ALL information from the document. Do NOT skip or omit any facts.
- Variety: Produce different types of questions (factual, analytical, comparative, definitional…).
- Format: Output ONLY the JSON array — no explanation, no markdown fences, no extra text.

Source text:
\"\"\"
{text}
\"\"\"
"""

# ─────────────────────────────── Helpers ──────────────────────────────────────

async def call_model_async(prompt: str) -> str:
    retry_wait = 10
    while True:
        async with semaphore:
            try:
                response = await client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=32768,
                )
                return response.choices[0].message.content
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError) as e:
                print(f"\n    ❌  Server connection lost: {e}. Retrying in {retry_wait}s...")
                await asyncio.sleep(retry_wait)
            except Exception as e:
                print(f"\n    ❌  Error calling model: {e}. Retrying in {retry_wait}s...")
                await asyncio.sleep(retry_wait)

def extract_json_array(raw: str) -> list:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, list): return data
        if isinstance(data, dict): return [data]
    except json.JSONDecodeError:
        pass
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list): return data
        except json.JSONDecodeError:
            pass
    return []

def deduplicate(records: list) -> list:
    seen = set()
    unique = []
    for rec in records:
        key = (rec.get("question", "").strip(), rec.get("response", "").strip())
        if key not in seen and key != ("", ""):
            seen.add(key)
            unique.append(rec)
    return unique

def re_index(records: list, offset: int = 0) -> list:
    for i, rec in enumerate(records, start=offset + 1):
        rec["id"] = str(i)
    return records

def save_json(path: str, data: list):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"    💾 Saved {len(data)} records → {os.path.basename(path)}")

def load_json(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ────────────────────────── Core Processing ───────────────────────────────────

async def process_run(text: str, run: int, num_runs: int, output_dir: str, base_name: str) -> str:
    run_output = os.path.join(output_dir, f"{base_name}_run{run}.json")
    if os.path.exists(run_output):
        try:
            existing = load_json(run_output)
            if existing: return run_output
        except: pass
        os.remove(run_output)

    prompt = build_prompt(text)
    raw = await call_model_async(prompt)
    records = extract_json_array(raw)
    
    if records:
        save_json(run_output, records)
        return run_output
    else:
        raw_backup = os.path.join(output_dir, f"{base_name}_run{run}_RAW.txt")
        with open(raw_backup, "w", encoding="utf-8") as f: f.write(raw)
        return None

async def process_single_txt(txt_path: str, output_dir: str, base_name: str):
    print(f"\n  📄 Processing: {os.path.basename(txt_path)}")
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    tasks = [process_run(text, r, NUM_RUNS, output_dir, base_name) for r in range(1, NUM_RUNS + 1)]
    run_results = await asyncio.gather(*tasks)
    
    all_records = []
    for rf in run_results:
        if rf and os.path.exists(rf):
            all_records.extend(load_json(rf))

    return re_index(deduplicate(all_records))

async def process_folder(input_folder: str, output_folder: str):
    os.makedirs(output_folder, exist_ok=True)
    all_files = sorted(f for f in os.listdir(input_folder) if f.endswith(".txt"))
    if not all_files: return

    standalone = [f for f in all_files if "_part" not in f or f.startswith("part_")]
    parts = [f for f in all_files if "_part" in f and not f.startswith("part_")]

    for fname in standalone:
        base_name = os.path.splitext(fname)[0]
        final_out = os.path.join(output_folder, f"{base_name}_FINAL.json")
        if os.path.exists(final_out) and load_json(final_out): continue
        
        merged = await process_single_txt(os.path.join(input_folder, fname), output_folder, base_name)
        if merged: save_json(final_out, merged)

    if parts:
        groups = {}
        for fname in parts:
            key = re.sub(r"_part\d+\.txt$", "", fname)
            groups.setdefault(key, []).append(fname)

        for group_key, part_files in groups.items():
            final_out = os.path.join(output_folder, f"{group_key}_FINAL.json")
            if os.path.exists(final_out) and load_json(final_out): continue
            
            print(f"\n  📦 Group '{group_key}' — {len(part_files)} parts")
            group_records = []
            for fname in sorted(part_files):
                res = await process_single_txt(os.path.join(input_folder, fname), output_folder, os.path.splitext(fname)[0])
                group_records.extend(res)
            
            final_res = re_index(deduplicate(group_records))
            if final_res: save_json(final_out, final_res)

async def main():
    if not os.path.exists(DATA_DIR):
        print(f"❌ Input directory '{DATA_DIR}' not found.")
        return
    print(f"🚀 Starting Optimized Dataset Generation (Instance 2)")
    await process_folder(DATA_DIR, OUTPUT_DIR)
    print("\n🎉 All done!")

if __name__ == "__main__":
    asyncio.run(main())
