#!/usr/bin/env python3
"""Full document test with base SaulLM and comprehensive prompt template."""

import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import time
from pathlib import Path
import re

def test_full_document():
    print("="*80)
    print("FULL DOCUMENT TEST: BASE SAULLM WITH COMPREHENSIVE PROMPT TEMPLATE")
    print("="*80)
    
    print("\n[1/5] Loading BASE SaulLM-7B model (NOT fine-tuned)...")
    model_id = "Equall/Saul-7B-Instruct-v1"
    
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    print("✓ Model loaded successfully")
    
    print("\n[2/5] Loading Rahimi document...")
    with open("rahimi_document.json", 'r') as f:
        doc_data = json.load(f)
        full_document = doc_data['markdown']
    
    print(f"✓ Document loaded: {len(full_document)} characters")
    
    print("\n[3/5] Loading comprehensive prompt template...")
    template = Path("src/prompts/saullm_entity_extraction_template.md").read_text()
    
    print(f"✓ Template loaded: {len(template)} characters")
    
    # Process document in chunks
    chunk_size = 3000
    chunks = [full_document[i:i+chunk_size] for i in range(0, len(full_document), chunk_size)]
    
    print(f"\n[4/5] Processing {len(chunks)} chunks of {chunk_size} chars each...")
    print("-"*80)
    
    all_entities = []
    all_relationships = []
    chunk_results = []
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i}/{len(chunks)}")
        print(f"Processing {len(chunk)} characters...")
        
        # Create prompt with this chunk
        prompt = template.replace("{{document_text}}", chunk)
        
        # Check if prompt is too large and truncate if needed
        max_prompt_chars = 15000  # Reduced to ensure it fits in context
        if len(prompt) > max_prompt_chars:
            # Keep the essential parts: entity type definitions and the document
            print(f"Prompt too large ({len(prompt)} chars), truncating to {max_prompt_chars} chars...")
            # Try to keep the document part and essential instructions
            prompt = prompt[:max_prompt_chars] + "\n\n## Task\nExtract all legal entities from the document above and return them in JSON format with 'entities' array."
        
        # Tokenize
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=4096
        ).to(model.device)
        
        start = time.time()
        
        # Generate
        print("Generating response...")
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
        
        print(f"Processing time: {elapsed:.2f}s")
        
        # Parse response
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group(0))
                entities = result.get('entities', [])
                relationships = result.get('relationships', [])
                
                print(f"✓ Found {len(entities)} entities in this chunk")
                
                if entities:
                    all_entities.extend(entities)
                if relationships:
                    all_relationships.extend(relationships)
                    
                chunk_results.append({
                    "chunk": i,
                    "entities_found": len(entities),
                    "relationships_found": len(relationships),
                    "processing_time": elapsed,
                    "response_sample": response[:500]
                })
            else:
                print("✗ No valid JSON found in response")
                print(f"Response preview: {response[:500]}")
                chunk_results.append({
                    "chunk": i,
                    "entities_found": 0,
                    "relationships_found": 0,
                    "processing_time": elapsed,
                    "error": "No JSON found",
                    "response_sample": response[:500]
                })
        except Exception as e:
            print(f"✗ Error parsing response: {e}")
            print(f"Response preview: {response[:500]}")
            chunk_results.append({
                "chunk": i,
                "entities_found": 0,
                "relationships_found": 0,
                "processing_time": elapsed,
                "error": str(e),
                "response_sample": response[:500]
            })
    
    print("\n" + "="*80)
    print("[5/5] COMPLETE RESULTS - ALL EXTRACTED ENTITIES")
    print("="*80)
    
    # Deduplicate entities
    seen = set()
    unique_entities = []
    for entity in all_entities:
        key = (entity.get("text", ""), entity.get("entity_type", ""))
        if key not in seen and key[0]:
            seen.add(key)
            unique_entities.append(entity)
    
    print(f"\n📊 SUMMARY STATISTICS:")
    print(f"   Total chunks processed: {len(chunks)}")
    print(f"   Total entities found (with duplicates): {len(all_entities)}")
    print(f"   Unique entities found: {len(unique_entities)}")
    print(f"   Total relationships found: {len(all_relationships)}")
    print(f"   Total processing time: {sum(c.get('processing_time', 0) for c in chunk_results):.2f}s")
    
    # Show entity type distribution
    entity_types = {}
    for entity in unique_entities:
        entity_type = entity.get("entity_type", "UNKNOWN")
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
    
    print(f"\n📈 ENTITY TYPE DISTRIBUTION ({len(entity_types)} types):")
    for entity_type, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   {entity_type}: {count}")
    
    print("\n" + "="*80)
    print("🔍 ALL EXTRACTED ENTITIES (COMPLETE LIST)")
    print("="*80)
    
    if unique_entities:
        for i, entity in enumerate(unique_entities, 1):
            print(f"\n[Entity {i}]")
            print(f"  Type: {entity.get('entity_type', 'UNKNOWN')}")
            print(f"  Text: \"{entity.get('text', '')}\"")
            if 'confidence' in entity:
                print(f"  Confidence: {entity.get('confidence', 0)}")
            if 'context' in entity:
                print(f"  Context: \"{entity.get('context', '')[:100]}...\"")
    else:
        print("\n❌ NO ENTITIES WERE EXTRACTED")
    
    print("\n" + "="*80)
    print("📋 PER-CHUNK EXTRACTION DETAILS")
    print("="*80)
    
    for chunk_result in chunk_results:
        print(f"\nChunk {chunk_result['chunk']}:")
        print(f"  Entities: {chunk_result.get('entities_found', 0)}")
        print(f"  Relationships: {chunk_result.get('relationships_found', 0)}")
        print(f"  Time: {chunk_result.get('processing_time', 0):.2f}s")
        if 'error' in chunk_result:
            print(f"  Error: {chunk_result['error']}")
        print(f"  Response preview: {chunk_result.get('response_sample', 'N/A')[:200]}...")
    
    # Save complete results
    complete_results = {
        "test_type": "BASE_SAULLM_WITH_COMPREHENSIVE_TEMPLATE",
        "model": "Equall/Saul-7B-Instruct-v1 (BASE, NOT FINE-TUNED)",
        "prompt_template": "saullm_entity_extraction_template.md",
        "document": "Rahimi.pdf (full document)",
        "document_size": len(full_document),
        "chunks_processed": len(chunks),
        "chunk_size": chunk_size,
        "all_entities_with_duplicates": all_entities,
        "unique_entities": unique_entities,
        "relationships": all_relationships,
        "statistics": {
            "total_entities_with_duplicates": len(all_entities),
            "total_unique_entities": len(unique_entities),
            "total_relationships": len(all_relationships),
            "entity_type_distribution": entity_types,
            "unique_entity_types": len(entity_types),
            "total_processing_time": sum(c.get('processing_time', 0) for c in chunk_results)
        },
        "chunk_results": chunk_results,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }
    
    output_file = "full_document_base_test_results.json"
    with open(output_file, 'w') as f:
        json.dump(complete_results, f, indent=2)
    
    print(f"\n💾 Complete results saved to: {output_file}")
    
    return complete_results

if __name__ == "__main__":
    results = test_full_document()
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    print(f"Final Result: {results['statistics']['total_unique_entities']} unique entities extracted")
    print(f"Entity Types: {results['statistics']['unique_entity_types']} different types")
    print("="*80)