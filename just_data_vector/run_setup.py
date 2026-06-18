import subprocess
import os
import sys

def run_setup_background():
    """
    Runs setup.sh in the background and redirects all output to setup.log.
    Designed for execution on an Ubuntu server.
    """
    script_name = "setup.sh"
    log_name = "setup.log"
    
    # Check if setup.sh exists
    if not os.path.exists(script_name):
        print(f"❌ Error: {script_name} not found in the current directory.")
        return

    # Ensure the script is executable
    os.chmod(script_name, 0o755)

    print(f"🚀 Launching {script_name} in the background...")
    print(f"📋 Output will be logged to {log_name}")

    try:
        # Open the log file for writing
        with open(log_name, "w") as log_file:
            # subprocess.Popen starts the process without waiting for it to finish
            # We use 'bash' explicitly to ensure it runs correctly on Ubuntu
            process = subprocess.Popen(
                ["bash", script_name],
                stdout=log_file,
                stderr=subprocess.STDOUT, # Redirect stderr to the same log file
                start_new_session=True    # Detach from the current terminal session
            )
        
        print(f"✅ Setup background process started successfully!")
        print(f"🆔 PID: {process.pid}")
        print(f"💡 You can monitor progress with: tail -f {log_name}")

    except Exception as e:
        print(f"❌ Failed to start the setup process: {e}")

if __name__ == "__main__":
    run_setup_background()
