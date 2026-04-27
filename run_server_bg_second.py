import subprocess
import os
import time
import sys
from pathlib import Path

# --- Configuration ---
BASE_DIR = Path(__file__).parent.resolve()
SERVER_SCRIPT = BASE_DIR / "start_llamacpp_server.sh"
SERVER_LOG = BASE_DIR / "llamacpp_server_logs.txt"

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

    # --- Robust Cleanup ---
    print("[*] Forcefully cleaning up port 8021 and old server processes...")
    os.system("fuser -k 8021/tcp > /dev/null 2>&1 || true")
    os.system("pkill -9 -f llama_cpp || true")
    
    print("[*] Waiting 5 seconds for resources to be released...")
    time.sleep(5) 
    
    os.chmod(SERVER_SCRIPT, 0o755)

    print(f"{'='*60}")
    print(f" llama.cpp Server Background Manager")
    print(f"{'='*60}")
    print(f" Server Log : {SERVER_LOG}")
    print(f"{'='*60}")

    with open(SERVER_LOG, "a") as server_handle:
        server_handle.write(f"\n\n{'='*80}\n")
        server_handle.write(f" LLAMACPP SERVER SESSION STARTED AT: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        server_handle.write(f"{'='*80}\n\n")
        server_handle.flush()

        server_proc = start_process(["bash", str(SERVER_SCRIPT)], server_handle, "llama.cpp Server", cwd=BASE_DIR)

    print(f"\n{'='*60}")
    print(" SUCCESS: Server is running in the background.")
    print(f" Server PID : {server_proc.pid}")
    print(f" Check logs : tail -f {SERVER_LOG}")
    print(f"{'='*60}\n")
    print(f" To stop, use: kill {server_proc.pid}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)
