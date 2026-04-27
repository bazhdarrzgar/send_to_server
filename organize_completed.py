import os
import shutil

# ─────────────────────────── Configuration ────────────────────────────────────
# The base folders
SOURCE_BASE_DIR = "UKH-AIIC-KA_Just_TXT_file"
OUTPUT_BASE_DIR = "UKH-AIIC-KA_Just_TXT_file_Output"
COMPLETE_BASE   = "complete"

# The sub-folders we are working with
PARTS = ["part1", "part2", "part3"]

def organize_completed():
    print("🚀 Moving completed records to the 'complete' folder...")

    for part in PARTS:
        src_part_path = os.path.join(SOURCE_BASE_DIR, part)
        out_part_path = os.path.join(OUTPUT_BASE_DIR, part)

        # Check if source exists; output might not exist if nothing is done yet
        if not os.path.exists(src_part_path):
            print(f"⏩ Skipping {part}: Source folder not found.")
            continue

        # Target folders inside 'complete'
        target_src_dir = os.path.join(COMPLETE_BASE, part, "source_files")
        target_out_dir = os.path.join(COMPLETE_BASE, part, "processed_files")

        # Find completed files in the output folder
        completed_bases = []
        if os.path.exists(out_part_path):
            for filename in os.listdir(out_part_path):
                if filename.endswith("_FINAL.json"):
                    # Extract the base name (e.g., '163267' from '163267_FINAL.json')
                    base_name = filename.replace("_FINAL.json", "")
                    completed_bases.append(base_name)

        if not completed_bases:
            print(f"ℹ️  No completed files found in {part}.")
            continue

        # Ensure target 'complete' folders exist
        os.makedirs(target_src_dir, exist_ok=True)
        os.makedirs(target_out_dir, exist_ok=True)

        print(f"📦 Found {len(completed_bases)} completed records in {part}. Moving now...")

        for base in completed_bases:
            # 1. Move ALL related Output files (Final, Runs, RAW)
            for out_f in os.listdir(out_part_path):
                if out_f.startswith(base):
                    shutil.move(
                        os.path.join(out_part_path, out_f),
                        os.path.join(target_out_dir, out_f)
                    )

            # 2. Move related Source files (Standalone .txt or Part files)
            for src_f in os.listdir(src_part_path):
                # Move if it's 'base.txt' or 'base_partX.txt'
                if src_f == f"{base}.txt" or (src_f.startswith(f"{base}_part") and src_f.endswith(".txt")):
                    shutil.move(
                        os.path.join(src_part_path, src_f),
                        os.path.join(target_src_dir, src_f)
                    )

    print("\n✨ Done! Completed files have been moved to the 'complete' folder.")
    print("Unprocessed files remain in the original folder for the generator to continue.")



if __name__ == "__main__":
    organize_completed()
