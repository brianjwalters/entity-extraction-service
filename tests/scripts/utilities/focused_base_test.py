#!/usr/bin/env python3
"""Focused test with clear instructions and actual document content."""

import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import time
import re

def test_focused():
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
    
    # Load first 1000 chars of actual document
    with open("rahimi_document.json", 'r') as f:
        doc_data = json.load(f)
        document_text = doc_data['markdown'][:1000]
    
    print("Document excerpt:")
    print(document_text[:200])
    
    # Create focused prompt
    prompt = f"""[INST] You are a legal entity extraction expert. Extract all legal entities from the following document text.

IMPORTANT: Extract entities ONLY from the document text below, not from these instructions.

Entity types to identify:
- CASE: Legal case names (e.g., "United States v. Rahimi")
- PERSON: Individual people mentioned
- COURT: Court names (e.g., "Supreme Court")
- DATE: Specific dates
- CITATION: Legal citations (e.g., "592 U.S. 348")

DOCUMENT TEXT STARTS HERE:
{document_text}
DOCUMENT TEXT ENDS HERE

Extract all entities from the above document and return them in this JSON format:
{{
  "entities": [
    {{
      "text": "exact text from document",
      "entity_type": "CASE/PERSON/COURT/DATE/CITATION",
      "confidence": 0.8
    }}
  ]
}}

Return ONLY the JSON, no other text. [/INST]"""
    
    print(f"\nPrompt length: {len(prompt)} characters")
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
            max_new_tokens=1024,
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
    print("\nRaw Response (first 500 chars):")
    print(response[:500])
    
    # Try to parse JSON
    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group(0))
            print(f"\nExtracted {len(result.get('entities', []))} entities:")
            for entity in result.get('entities', [])[:10]:
                print(f"  - {entity.get('entity_type', 'UNKNOWN')}: {entity.get('text', '')}")
            
            # Save result
            with open("focused_base_result.json", 'w') as f:
                json.dump(result, f, indent=2)
            print("\nFull results saved to focused_base_result.json")
        else:
            print("\nNo valid JSON found in response")
            with open("focused_base_result.txt", 'w') as f:
                f.write(response)
            print("Raw response saved to focused_base_result.txt")
    except Exception as e:
        print(f"\nError parsing JSON: {e}")
        with open("focused_base_result.txt", 'w') as f:
            f.write(response)

if __name__ == "__main__":
    test_focused()