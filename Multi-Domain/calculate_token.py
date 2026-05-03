import os
import tiktoken
from concurrent.futures import ThreadPoolExecutor

def count_tokens_in_file(file_path, encoder):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            return len(encoder.encode(content))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

def calculate_tokens_for_folder(folder_path, encoder):
    if not os.path.exists(folder_path):
        return 0, 0
    
    file_paths = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".txt"):
                file_paths.append(os.path.join(root, file))
    
    if not file_paths:
        return 0, 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda p: count_tokens_in_file(p, encoder), file_paths))
        total_tokens = sum(results)
        
    return total_tokens, len(file_paths)

def main():
    base_dir = "/media/swyanswartz/e02e2612-6768-4d79-b2b3-a07d5b9b35a1/home/soyanswartz/Documents/a/send/News/SKNAD_Split_Only"
    parts = ["part1", "part2", "part3"]
    encoder = tiktoken.get_encoding("cl100k_base")
    
    results = []
    grand_total_tokens = 0
    grand_total_files = 0

    print("Analyzing folders... this may take a moment.\n")

    for part in parts:
        part_path = os.path.join(base_dir, part)
        if not os.path.exists(part_path):
            continue
            
        # Get immediate subdirectories
        subfolders = sorted([f for f in os.listdir(part_path) if os.path.isdir(os.path.join(part_path, f))])
        
        part_tokens = 0
        part_files = 0
        
        for sub in subfolders:
            sub_path = os.path.join(part_path, sub)
            tokens, num_files = calculate_tokens_for_folder(sub_path, encoder)
            results.append({
                "part": part,
                "subfolder": sub,
                "tokens": tokens,
                "files": num_files
            })
            part_tokens += tokens
            part_files += num_files
            
        grand_total_tokens += part_tokens
        grand_total_files += part_files

    # Print Table
    header = f"{'Part':<10} | {'Subfolder':<30} | {'Files':<10} | {'Tokens':<15}"
    separator = "-" * len(header)
    print(header)
    print(separator)
    
    current_part = ""
    for res in results:
        # Add a visual separator between parts
        if current_part and current_part != res['part']:
            print("-" * 15 + " | " + "-" * 30 + " | " + "-" * 10 + " | " + "-" * 15)
        
        print(f"{res['part']:<10} | {res['subfolder']:<30} | {res['files']:<10,} | {res['tokens']:<15,}")
        current_part = res['part']
        
    print(separator)
    print(f"{'TOTAL':<10} | {'':<30} | {grand_total_files:<10,} | {grand_total_tokens:<15,}")

if __name__ == "__main__":
    main()
