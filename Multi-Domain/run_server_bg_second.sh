import subprocess
import os
import time
import sys
from pathlib import Path

# --- Configuration ---
BASE_DIR = Path(__file__).parent.resolve()
SERVER_SCRIPT = BASE_DIR / "start_ollama_server_second.sh"
SERVER_LOG    = BASE_DIR / "ollama_server_logs_second.txt"

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
    if not SERVER_SCRIPT.exists():
        print(f"ERROR: {SERVER_SCRIPT} not found.")
        sys.exit(1)

    # Note: Global cleanup is skipped here to avoid killing the first instance.
    # If you need to stop this specific instance, use 'kill <PID>' or find its specific process.
    
    print("[*] Waiting 1 second for resources...")
    time.sleep(1)

    os.chmod(SERVER_SCRIPT, 0o755)

    print(f"{'='*60}")
    print(f" Ollama Server (Instance 2) Background Manager")
    print(f"{'='*60}")
    print(f" Server Log : {SERVER_LOG}")
    print(f"{'='*60}")

    with open(SERVER_LOG, "a") as server_handle:
        server_handle.write(f"\n\n{'='*80}\n")
        server_handle.write(f" OLLAMA SERVER (GPU 1) SESSION STARTED AT: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        server_handle.write(f"{'='*80}\n\n")
        server_handle.flush()

        server_proc = start_process(["bash", str(SERVER_SCRIPT)], server_handle, "Ollama Server (GPU 1)", cwd=BASE_DIR)

    print(f"\n{'='*60}")
    print(" SUCCESS: Ollama server script (GPU 1) is running in the background.")
    print(f" Server PID : {server_proc.pid}")
    print(f" Check logs : tail -f {SERVER_LOG}")
    print(f" API        : http://localhost:11435")
    print(f" OpenAI API : http://localhost:11435/v1")
    print(f"{'='*60}\n")
    print(f" To stop, use: kill {server_proc.pid}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)
