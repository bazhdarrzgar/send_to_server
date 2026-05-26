#!/bin/bash

# Load Model into Cache

echo -e "\033[1;33m[*] Action: Caching 'xlm-roberta-large' model...\033[0m"

# We use python to trigger the Hugging Face download
python3 -c "
from transformers import AutoTokenizer, AutoModel
print('Downloading tokenizer...')
AutoTokenizer.from_pretrained('xlm-roberta-large')
print('Downloading model...')
AutoModel.from_pretrained('xlm-roberta-large')
print('Done!')
"

echo -e "\033[1;32m[SUCCESS] Model 'xlm-roberta-large' is cached successfully!\033[0m"
