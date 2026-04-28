# 1. Install Ollama + GPU support
chmod +x install_ollama.sh && ./install_ollama.sh

# 2. Register / download the Gemma 3 27B model
chmod +x setup_ollama_model.sh && ./setup_ollama_model.sh

# 3. Install Python dependencies
chmod +x install_requirements.sh && ./install_requirements.sh

# 4. Start the Ollama server in background
python3 run_server_bg_first.py

# 5. Start the dataset generator in background
python3 run_generator_bg_first.py

# To stop everything:
chmod +x pkill_ollama.sh && ./pkill_ollama.sh