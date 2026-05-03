import subprocess
import os
import time
import sys
from pathlib import Path

# --- Configuration ---
BASE_DIR = Path(__file__).parent.resolve()
GENERATOR_SCRIPT = BASE_DIR / "generate_dataset_first.py"
GENERATOR_LOG = BASE_DIR / "generate_dataset_logs_first.txt"
PYTHON_EXEC = sys.executable

def start_process(command, log_file_handle, description, cwd=None):
    """Starts a process in the background and redirects output to a log file."""
    print(f"[*] Starting {description}...")

    process = subprocess.Popen(
        command,
        stdout=log_file_handle,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setpgrp if sys.platform != "win32" else None,
        cwd=str(cwd) if cwd else str(BASE_DIR)
    )

    print(f"[+] {description} started with PID: {process.pid}")
    return process

def main():
    if not GENERATOR_SCRIPT.exists():
        print(f"ERROR: {GENERATOR_SCRIPT} not found.")
        sys.exit(1)

    # --- Selective Cleanup ---
    # Kill old generator processes for 'four' script, but exclude our own PID
    my_pid = os.getpid()
    print(f"[*] Cleaning up old generator processes for {GENERATOR_SCRIPT.name} (excluding PID {my_pid})...")
    # Use pgrep to find matching PIDs by filename
    os.system(f"pgrep -f '{GENERATOR_SCRIPT.name}' | grep -v '^{my_pid}$' | xargs -r kill -9 2>/dev/null || true")
    time.sleep(2)

    print(f"{'='*60}")
    print(f" Dataset Generator Background Manager")
    print(f"{'='*60}")
    print(f" Generator Log : {GENERATOR_LOG}")
    print(f"{'='*60}")

    with open(GENERATOR_LOG, "a") as generator_handle:
        generator_handle.write(f"\n\n{'='*80}\n")
        generator_handle.write(f" DATASET GENERATOR SESSION STARTED AT: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        generator_handle.write(f"{'='*80}\n\n")
        generator_handle.flush()

        generator_proc = start_process([PYTHON_EXEC, str(GENERATOR_SCRIPT)], generator_handle, "Dataset Generator", cwd=BASE_DIR)

    print(f"\n{'='*60}")
    print(" SUCCESS: Generator is running in the background.")
    print(f" Generator PID : {generator_proc.pid}")
    print(f" Check logs    : tail -f {GENERATOR_LOG}")
    print(f"{'='*60}\n")
    print(f" To stop, use: kill {generator_proc.pid}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)