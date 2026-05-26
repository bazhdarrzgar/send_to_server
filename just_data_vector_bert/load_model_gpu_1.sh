#!/bin/bash

# Load Model into Cache

echo -e "\033[1;33m[*] Action: Caching 'bert-base-multilingual-cased' model...\033[0m"

# We use python to trigger the Hugging Face download
python3 -c "
from transformers import AutoTokenizer, AutoModel
print('Downloading tokenizer...')
AutoTokenizer.from_pretrained('bert-base-multilingual-cased')
print('Downloading model...')
AutoModel.from_pretrained('bert-base-multilingual-cased')
print('Done!')
"

echo -e "\033[1;32m[SUCCESS] Model 'bert-base-multilingual-cased' is cached successfully!\033[0m"
