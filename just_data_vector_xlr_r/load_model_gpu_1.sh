#!/bin/bash

# Load Model into Cache

echo -e "\033[1;33m[*] Action: Caching 'xlm-roberta-base' model...\033[0m"

# We use python to trigger the Hugging Face download
python3 -c "
from transformers import AutoTokenizer, AutoModel
print('Downloading tokenizer...')
AutoTokenizer.from_pretrained('xlm-roberta-base')
print('Downloading model...')
AutoModel.from_pretrained('xlm-roberta-base')
print('Done!')
"

echo -e "\033[1;32m[SUCCESS] Model 'xlm-roberta-base' is cached successfully!\033[0m"
