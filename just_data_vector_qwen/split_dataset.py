import json
import math
import os

def split_dataset(input_path, output_part1, output_part2):
    print(f"Reading {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_entries = len(data)
    halfway = math.ceil(total_entries / 2)
    
    part1 = data[:halfway]
    part2 = data[halfway:]
    
    print(f"Total entries: {total_entries}")
    print(f"Part 1: {len(part1)} entries")
    print(f"Part 2: {len(part2)} entries")
    
    with open(output_part1, 'w', encoding='utf-8') as f:
        json.dump(part1, f, ensure_ascii=False, indent=2)
    
    with open(output_part2, 'w', encoding='utf-8') as f:
        json.dump(part2, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully saved to {output_part1} and {output_part2}")

if __name__ == "__main__":
    DATASET_PATH = "kurdish_medical_corpus_kmc.json"
    PART1_PATH = "kurdish_medical_corpus_kmc_part1.json"
    PART2_PATH = "kurdish_medical_corpus_kmc_part2.json"
    
    if os.path.exists(DATASET_PATH):
        split_dataset(DATASET_PATH, PART1_PATH, PART2_PATH)
    else:
        print(f"Error: {DATASET_PATH} not found.")
