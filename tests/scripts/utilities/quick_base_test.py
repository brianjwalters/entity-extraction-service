#!/usr/bin/env python3
"""Quick test of base SaulLM with a single chunk using enhanced prompt."""

import json
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import re
import time

def test_single_chunk():
    print("Loading BASE SaulLM model (not fine-tuned)...")
    model_id = "Equall/Saul-7B-Instruct-v1"
    
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    print("Model loaded!")
    
    # Load document
    with open("rahimi_document.json", 'r') as f:
        doc_data = json.load(f)
        document_text = doc_data['markdown'][:3000]  # First 3000 chars
    
    # Load template
    template = Path("src/prompts/saullm_entity_extraction_template.md").read_text()
    prompt = template.replace("{{document_text}}", document_text)
    
    print(f"Prompt length: {len(prompt)} characters")
    print("Processing chunk...")
    
    # Tokenize
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=4096
    ).to(model.device)
    
    start = time.time()
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=2048,
            temperature=0.1,
            do_sample=True,
            top_p=0.95,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    elapsed = time.time() - start
    
    # Decode
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if prompt in response:
        response = response[len(prompt):].strip()
    
    print(f"\nProcessing time: {elapsed:.2f}s")
    print("\nResponse (first 1000 chars):")
    print(response[:1000])
    
    # Try to parse JSON
    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group(0))
            print(f"\nParsed JSON successfully!")
            print(f"Entities found: {len(result.get('entities', []))}")
            print(f"Entity types: {set(e.get('entity_type') for e in result.get('entities', []))}")
            
            # Save result
            with open("quick_base_test_result.json", 'w') as f:
                json.dump(result, f, indent=2)
            print("\nSaved to quick_base_test_result.json")
        else:
            print("\nNo valid JSON found in response")
    except Exception as e:
        print(f"\nError parsing JSON: {e}")

if __name__ == "__main__":
    test_single_chunk()