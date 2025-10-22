# Entity Extraction Prompt Templates

## Overview
This directory contains comprehensive prompt templates for a 7-pass entity extraction strategy designed to work with the vLLM service (IBM Granite 3.3 2B model on port 8080). These templates use Jinja2 syntax and include concrete examples from the YAML pattern files.

## 7-Pass Extraction Strategy

### Pass 1: Case Citations (`entity_extraction_pass1_citations.md`)
- Extracts all case citations including full citations, short forms, and electronic citations
- Covers 23 types of case citation patterns
- Examples: Supreme Court, Federal Courts, State Courts, Bankruptcy, Tax Court
- Includes pinpoint citations, parallel citations, and Westlaw/Lexis formats

### Pass 2: Statute Citations (`entity_extraction_pass2_statutes.md`)
- Extracts federal and state statute citations
- Covers USC, Federal Rules (FRCP, FRCrP, FRE, FRAP)
- Includes all 50 state statute formats
- Handles section symbols, ranges, and "et seq." references

### Pass 3: Regulation Citations (`entity_extraction_pass3_regulations.md`)
- Extracts Code of Federal Regulations (CFR) citations
- Covers federal agency regulations (SEC, EPA, OSHA, FDA, IRS)
- Includes state administrative codes
- Handles executive orders and Federal Register citations

### Pass 4: Legal Entities (`entity_extraction_pass4_entities.md`)
- Extracts judges, attorneys, parties, and law firms
- Identifies government entities and agencies
- Captures corporate entities and business organizations
- Handles professional designations (Esq., P.C., LLC, etc.)

### Pass 5: Court Information (`entity_extraction_pass5_courts.md`)
- Extracts court names and jurisdictions
- Captures docket numbers and case numbers
- Identifies court locations and divisions
- Handles judge assignments and filing information

### Pass 6: Temporal and Monetary Values (`entity_extraction_pass6_temporal.md`)
- Extracts dates in multiple formats
- Identifies deadlines and time periods
- Captures monetary amounts (damages, settlements, fees)
- Handles financial terms and payment schedules

### Pass 7: Addresses and Catch-All (`entity_extraction_pass7_catchall.md`)
- Extracts physical addresses and contact information
- Captures legal doctrines and principles
- Identifies procedural terms and motions
- Serves as final pass to catch any missed entities

## Usage with vLLM Service

### Python Example
```python
from jinja2 import Template
import httpx
import json

# Load prompt template
with open('entity_extraction_pass1_citations.md', 'r') as f:
    template_content = f.read()

# Create Jinja2 template
template = Template(template_content)

# Render with actual text
prompt = template.render(text_chunk="Brown v. Board, 347 U.S. 483 (1954)")

# Call vLLM service
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8080/v1/chat/completions",
        json={
            "model": "qwen-instruct-160k",
            "messages": [
                {"role": "system", "content": "You are a legal entity extraction specialist."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,  # Low temperature for consistent extraction
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }
    )
    
    result = response.json()
    entities = json.loads(result["choices"][0]["message"]["content"])
```

### Integration with Entity Extraction Service
```python
class MultiPassExtractor:
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.prompts = self.load_prompts()
    
    def load_prompts(self):
        prompts = {}
        for i in range(1, 8):
            if i == 1:
                name = "citations"
            elif i == 2:
                name = "statutes"
            elif i == 3:
                name = "regulations"
            elif i == 4:
                name = "entities"
            elif i == 5:
                name = "courts"
            elif i == 6:
                name = "temporal"
            else:
                name = "catchall"
            
            with open(f'entity_extraction_pass{i}_{name}.md', 'r') as f:
                prompts[f'pass_{i}'] = Template(f.read())
        
        return prompts
    
    async def extract_entities(self, text: str):
        all_entities = {}
        
        for pass_name, template in self.prompts.items():
            prompt = template.render(text_chunk=text)
            
            response = await self.llm_client.chat_completion(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            entities = json.loads(response["content"])
            all_entities[pass_name] = entities
        
        return self.merge_entities(all_entities)
```

## Template Variables

All templates use the following Jinja2 variables:
- `{{ text_chunk }}`: The input text to extract entities from

## Output Format

Each template returns a standardized JSON structure:
- `entities/citations/statutes/etc.`: Array of extracted items
- `metadata`: Statistics about extraction results
- Each entity includes:
  - `text`: Original text
  - `type`: Entity type
  - `normalized`: Standardized format
  - `components`: Parsed components
  - `confidence`: Confidence score
  - `start_pos/end_pos`: Text positions

## Performance Optimization

### Recommended Settings for vLLM
- Temperature: 0.1 (low for consistent extraction)
- Max tokens: 2000-4000 (depending on text length)
- Top-p: 0.95
- Response format: JSON object

### Batch Processing
Process multiple chunks in parallel for better throughput:
```python
import asyncio

async def batch_extract(chunks, extractor):
    tasks = [extractor.extract_entities(chunk) for chunk in chunks]
    return await asyncio.gather(*tasks)
```

## Testing

Test templates with the actual YAML patterns:
```bash
cd /srv/luris/be/entity-extraction-service
python tests/test_prompt_templates.py
```

## Notes

1. Templates are optimized for the 2B parameter Granite model
2. Each pass is independent and can be run in parallel
3. Results should be merged and deduplicated after all passes
4. Confidence scores help prioritize conflicting extractions
5. Templates include extensive examples from actual YAML patterns