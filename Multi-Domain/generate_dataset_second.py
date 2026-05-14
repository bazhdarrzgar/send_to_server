#!/usr/bin/env python3
"""
generate_dataset_second.py (Ollama version) - Second Dataset Instance

For every .txt file under the configured DATA_DIR:
  - Standalone files  (e.g. 1-10.txt):   run the prompt NUM_RUNS times → JSON files
                                           → merge all runs into one final JSON file
  - Part files        (e.g. 163267_part1.txt, 163267_part2.txt, …):
                        run the prompt NUM_RUNS times per part → JSON files per part
                        → after ALL parts are done, merge everything into one final JSON

Original .txt files are NEVER deleted.
Duplicate (question, response) pairs within the same final merged file are removed.

Requires: Ollama running on localhost:11435 with gemma3:27b loaded (GPU 1).
"""

import os
import re
import json
import time
import httpx
from openai import OpenAI

# ─────────────────────────── Bypass Proxy ─────────────────────────────────────
# Ensure localhost connections are NOT routed through any system proxy
os.environ["no_proxy"] = "localhost,127.0.0.1"
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

# ─────────────────────────── Configuration ────────────────────────────────────

# Use absolute paths for input and output
BASE_DATA_DIR   = "../SKNAD_Split_Only"
BASE_OUTPUT_DIR = "../SKNAD_Split_Only_Output"

# Specific subfolders for the SECOND script (GPU 1)
TARGET_FOLDERS = [
    "part1/Ava News_12807",
    "part1/BasNews_9984",
    "part1/Channel8_12289",
    "part1/Haremnews_30199",
    "part1/gksat_140834",
    "part2/Kurdistan TV_29841",
    "part2/Payam_18409",
    "part3/Rudaw_31656",
    "part3/Shanpress_19142"
]

MODEL_NAME      = "gemma3:27b"
NUM_RUNS        = 10

# Ollama OpenAI-compatible endpoint
# Instance 2: Port 11435 (GPU 1)
client = OpenAI(
    base_url="http://localhost:11435/v1",
    api_key="ollama",          # Ollama ignores the key but the field must be non-empty
    http_client=httpx.Client(proxy=None),
)

# ──────────────────────────── Prompt Template ─────────────────────────────────

def build_prompt(text: str, run_index: int) -> str:
    """
    Build the prompt for a given run.
    """
    return f"""Act as an expert Kurdish linguist and data engineer.
Analyze the following text and determine its category (e.g., History, Medical, Mathematics, Technology, Literature, Science, etc.).
Then, generate high-quality, information-rich question-and-answer pairs based on the text.

IMPORTANT: Return a VALID JSON array. Start your response with '[' and end with ']'.
Do NOT include any markdown formatting, code fences (```json), or introductory/concluding text.

Structure:
[
  {{
    "id": "1",
    "category": "<category>",
    "question": "<formal Sorani question>",
    "response": "<formal Sorani answer>",
    "document": {{
      "title": "<title>",
      "source_url": "",
      "publication_date": ""
    }}
  }}
]

Rules:
- Language: Central Kurdish (Sorani) ONLY.
- Grammar: Formal and academic level.
- Format: Output ONLY the raw JSON array.

Source text:
\"\"\"
{text}
\"\"\"
"""

# ─────────────────────────────── Helpers ──────────────────────────────────────

def call_model(prompt: str) -> str:
    """Send a prompt to Ollama (OpenAI-compatible API) and return the raw response string.
    If the server is down or unreachable, it waits indefinitely until the connection returns."""

    retry_wait = 30  # seconds to wait between retries on connection error

    while True:
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=32768,  # Large output limit
            )
            return response.choices[0].message.content
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError) as e:
            print(f"\n    ❌  Server connection lost: {e}")
            print(f"    ⏳ Waiting {retry_wait}s for server to come back online...")
            time.sleep(retry_wait)
        except Exception as e:
            # Handle other types of errors (e.g. timeout, invalid JSON, etc.)
            print(f"\n    ❌  Error calling model: {e}")
            print(f"    ⏳ Retrying in {retry_wait}s...")
            time.sleep(retry_wait)



def extract_json_array(raw: str) -> list:
    """
    Attempt to extract a JSON array from the model's raw output.
    Handles markdown fences, conversational filler, and common JSON errors.
    """
    if not raw or not isinstance(raw, str):
        return []

    # ── Step 1: strip ALL markdown code fences ────────────────────────────────
    # e.g.  ```json\n[...]\n```   or   ```\n[...]\n```
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = cleaned.replace("```", "").strip()

    # ── Step 2: find the outermost JSON array by scanning characters ──────────
    # This is much more reliable than a regex on the raw string because it
    # handles any amount of preamble text before the '['.
    start = cleaned.find("[")
    end   = cleaned.rfind("]")

    if start != -1 and end != -1 and end > start:
        json_str = cleaned[start : end + 1]

        # Fix trailing commas before } or ] (common LLM mistake)
        json_str = re.sub(r",\s*([\]}])", r"\1", json_str)

        try:
            data = json.loads(json_str)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return [data]
        except json.JSONDecodeError:
            pass

    # ── Step 3: maybe the model returned a bare object, not an array ──────────
    start_obj = cleaned.find("{")
    end_obj   = cleaned.rfind("}")
    if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
        json_str = cleaned[start_obj : end_obj + 1]
        json_str = re.sub(r",\s*([\]}])", r"\1", json_str)
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                return [data]
        except json.JSONDecodeError:
            pass

    # ── Step 4: last resort — try raw_decode to grab whatever JSON is there ───
    for candidate in (cleaned, raw):
        for opener in ("[", "{"):
            idx = candidate.find(opener)
            if idx == -1:
                continue
            try:
                obj, _ = json.JSONDecoder().raw_decode(candidate, idx)
                if isinstance(obj, list):
                    return obj
                if isinstance(obj, dict):
                    return [obj]
            except json.JSONDecodeError:
                pass

    # ── Nothing worked — log a useful snippet so you can debug ────────────────
    snippet = raw[:300].replace("\n", " ")
    print(f"    ⚠️  Could not parse JSON from model output. Saving raw output for inspection.")
    print(f"    📋 First 300 chars: {snippet!r}")
    return []


def deduplicate(records: list) -> list:
    """Remove duplicate (question, response) pairs — keeps first occurrence."""
    seen = set()
    unique = []
    for rec in records:
        key = (rec.get("question", "").strip(), rec.get("response", "").strip())
        if key not in seen and key != ("", ""):
            seen.add(key)
            unique.append(rec)
    return unique


def re_index(records: list, offset: int = 0) -> list:
    """Assign fresh sequential IDs to all records."""
    for i, rec in enumerate(records, start=offset + 1):
        rec["id"] = str(i)
    return records


def save_json(path: str, data: list):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"    💾 Saved {len(data)} records → {os.path.relpath(path)}")


def load_json(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ────────────────────────── Core Processing ───────────────────────────────────

def process_single_txt(txt_path: str, output_dir: str, base_name: str):
    """
    Run the prompt NUM_RUNS times for a single .txt file.
    Save one JSON file per run, then merge into a single final JSON.
    Returns the list of merged records.
    """
    print(f"\n  📄 Processing: {os.path.relpath(txt_path)}")

    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    run_files = []
    for run in range(1, NUM_RUNS + 1):
        run_output = os.path.join(output_dir, f"{base_name}_run{run}.json")

        # Skip if this run was already completed WITH actual data (resume support)
        if os.path.exists(run_output):
            try:
                existing = load_json(run_output)
                if len(existing) > 0:
                    print(f"    ↩  Run {run}/{NUM_RUNS} already done ({len(existing)} records) — skipping.")
                    run_files.append(run_output)
                    continue
                else:
                    print(f"    ⚠  Run {run}/{NUM_RUNS} file exists but has 0 records — re-running.")
                    os.remove(run_output)
            except Exception:
                print(f"    ⚠  Run {run}/{NUM_RUNS} file exists but is corrupt — re-running.")
                os.remove(run_output)

        print(f"    🔄 Run {run}/{NUM_RUNS}…", end=" ", flush=True)
        prompt  = build_prompt(text, run)
        raw     = call_model(prompt)
        records = extract_json_array(raw)
        print(f"{len(records)} records")

        # Only save if we got actual records
        if records:
            save_json(run_output, records)
            run_files.append(run_output)
        else:
            # Save raw output as backup for inspection, but do NOT save empty JSON
            # so this run will be retried on next execution
            raw_backup = os.path.join(output_dir, f"{base_name}_run{run}_RAW.txt")
            with open(raw_backup, "w", encoding="utf-8") as f:
                f.write(raw)
            print(f"    ⚠  No records extracted. Raw output saved. Will retry on next run.")

        # Small pause to allow the Ollama server to breathe between runs
        time.sleep(2)

    # Merge & deduplicate
    all_records = []
    for rf in run_files:
        if os.path.exists(rf):
            try:
                all_records.extend(load_json(rf))
            except Exception as e:
                print(f"    ⚠  Could not load {rf}: {e}")

    unique_records = re_index(deduplicate(all_records))
    return unique_records


def process_folder(input_folder: str, output_folder: str):
    """
    Process all .txt files inside a single document folder.
    """
    os.makedirs(output_folder, exist_ok=True)

    all_files = sorted(
        f for f in os.listdir(input_folder)
        if f.endswith(".txt") and os.path.isfile(os.path.join(input_folder, f))
    )

    if not all_files:
        print(f"    ⚠  No .txt files found in {input_folder}")
        return

    # Treat part_XXXX.txt as standalone if they don't follow the prefix_partX pattern
    standalone = [f for f in all_files if "_part" not in f or f.startswith("part_")]
    parts       = [f for f in all_files if "_part"     in f and not f.startswith("part_")]

    for fname in standalone:
        txt_path  = os.path.join(input_folder, fname)
        base_name = os.path.splitext(fname)[0]
        final_out = os.path.join(output_folder, f"{base_name}_FINAL.json")

        if os.path.exists(final_out):
            try:
                existing_final = load_json(final_out)
                if len(existing_final) > 0:
                    print(f"\n  ✅ Already finalised: {os.path.relpath(final_out)} ({len(existing_final)} records) — skipping.")
                    continue
                else:
                    print(f"\n  ⚠  Final file exists but has 0 records — re-processing.")
                    os.remove(final_out)
            except Exception:
                print(f"\n  ⚠  Final file exists but is corrupt — re-processing.")
                os.remove(final_out)

        merged = process_single_txt(txt_path, output_folder, base_name)
        if merged:
            save_json(final_out, merged)
            print(f"  ✅ Final merged ({len(merged)} unique records) → {os.path.relpath(final_out)}")
        else:
            print(f"  ⚠  No records produced for {base_name}. Will retry on next run.")

    if parts:
        groups: dict[str, list[str]] = {}
        for fname in parts:
            group_key = re.sub(r"_part\d+\.txt$", "", fname)
            groups.setdefault(group_key, []).append(fname)

        for group_key, part_files in groups.items():
            final_out = os.path.join(output_folder, f"{group_key}_FINAL.json")

            if os.path.exists(final_out):
                try:
                    existing_final = load_json(final_out)
                    if len(existing_final) > 0:
                        print(f"\n  ✅ Already finalised: {os.path.relpath(final_out)} ({len(existing_final)} records) — skipping.")
                        continue
                    else:
                        print(f"\n  ⚠  Final file exists but has 0 records — re-processing.")
                        os.remove(final_out)
                except Exception:
                    print(f"\n  ⚠  Final file exists but is corrupt — re-processing.")
                    os.remove(final_out)

            print(f"\n  📦 Group '{group_key}' — {len(part_files)} part(s)")
            group_records = []
            for fname in sorted(part_files):
                txt_path  = os.path.join(input_folder, fname)
                base_name = os.path.splitext(fname)[0]
                merged = process_single_txt(txt_path, output_folder, base_name)
                group_records.extend(merged)

            group_records = re_index(deduplicate(group_records))
            if group_records:
                save_json(final_out, group_records)
                print(f"  ✅ Group final merged ({len(group_records)} unique records) → {os.path.relpath(final_out)}")
            else:
                print(f"  ⚠  No records produced for group '{group_key}'. Will retry on next run.")


# ──────────────────────────────── Main ────────────────────────────────────────

def main():
    print(f"🚀 Starting dataset generation for (SECOND Script - GPU 1)")
    print(f"📂 Base Input : {BASE_DATA_DIR}")
    print(f"📂 Base Output: {BASE_OUTPUT_DIR}")

    for subpath in TARGET_FOLDERS:
        data_dir = os.path.join(BASE_DATA_DIR, subpath)
        
        # Determine output directory (keep the same structure as input)
        output_dir = os.path.join(BASE_OUTPUT_DIR, subpath)

        if not os.path.exists(data_dir):
            print(f"❌ Input directory '{data_dir}' not found. Skipping.")
            continue

        print(f"\n📂 Processing: {subpath}...")
        print(f"   Input : {data_dir}")
        print(f"   Output: {output_dir}")
        print(f"   Model : {MODEL_NAME}")
        print(f"   Runs  : {NUM_RUNS} per file\n")

        process_folder(data_dir, output_dir)

    print(f"\n{'═'*60}")
    print("🎉 All done! Look for *_FINAL.json files inside each folder.")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
