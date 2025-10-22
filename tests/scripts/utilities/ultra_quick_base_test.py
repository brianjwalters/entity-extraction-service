#!/usr/bin/env python3
"""Ultra quick test with only essential entity types."""

import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import time

def test_minimal():
    print("Loading BASE SaulLM model...")
    model_id = "Equall/Saul-7B-Instruct-v1"
    
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load document (very small chunk)
    with open("rahimi_document.json", 'r') as f:
        doc_data = json.load(f)
        document_text = doc_data['markdown'][:500]  # Only 500 chars
    
    # Create minimal prompt with key entity types
    prompt = f"""
You are a legal entity extraction system. Extract entities from the document.

## Entity Types to Extract:
- CASE: Legal cases (e.g., "Miranda v. Arizona")
- PERSON: Individual persons
- DATE: Dates and time references
- ORGANIZATION: Organizations and agencies
- CITATION: Legal citations

## Document:
{document_text}

## Output Format:
Return a JSON object with "entities" array. Each entity should have:
- text: The exact text
- entity_type: One of the types above
- confidence: 0.0 to 1.0

Begin extraction:
"""
    
    print(f"Prompt length: {len(prompt)} characters")
    print("Processing...")
    
    # Tokenize
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=2048
    ).to(model.device)
    
    start = time.time()
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.1,
            do_sample=True,
            top_p=0.95,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    elapsed = time.time() - start
    
    # Decode
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if prompt in response:
        response = response[len(prompt):].strip()
    
    print(f"\nProcessing time: {elapsed:.2f}s")
    print("\nResponse:")
    print(response[:1000])
    
    # Save result
    with open("ultra_quick_base_result.txt", 'w') as f:
        f.write(response)
    print("\nSaved to ultra_quick_base_result.txt")

if __name__ == "__main__":
    test_minimal()