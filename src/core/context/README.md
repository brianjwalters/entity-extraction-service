# Context Resolution Pipeline for CALES

## Overview

The Context Resolution Pipeline provides multi-stage context analysis for the CALES (Context-Aware Legal Entity System) entity extraction service. It combines pattern-based analysis, semantic analysis with Legal-BERT, dependency parsing with SpaCy, and section-based analysis to accurately determine the contextual role of entities in legal documents.

## Components

### 1. **context_resolver.py**
The main context resolution engine that implements multi-stage analysis:
- **Pattern-based analysis**: Uses regex patterns to identify context indicators
- **Semantic analysis**: Leverages Legal-BERT embeddings for deep contextual understanding
- **Dependency parsing**: Uses SpaCy for syntactic structure analysis
- **Section-based analysis**: Analyzes document structure and section headers
- **Signal combination**: Weighted voting system to combine multiple analysis methods

Key Features:
- Dynamic model loading with automatic fallbacks
- Configurable confidence thresholds
- Batch processing support
- Quality scoring for resolved contexts
- Comprehensive error handling

### 2. **context_mappings.py**
Complete context mappings for all 272 CALES entity types:
- Defines 60+ context types (case_header, party_section, jurisdiction, etc.)
- Maps each entity type to primary and secondary contexts
- Provides context indicators, proximity words, and section headers
- Implements confidence boost calculations
- Supports entity suggestion based on context

Entity Categories Covered:
- Legal Core (COURT, JUDGE, ATTORNEY, LAW_FIRM, etc.)
- Parties (PLAINTIFF, DEFENDANT, WITNESS, EXPERT, etc.)
- Legal Concepts (DOCTRINE, STANDARD, CAUSE_OF_ACTION, etc.)
- Statutory (STATUTE, REGULATION, CONSTITUTIONAL_PROVISION, etc.)
- Procedural (MOTION, ORDER, JUDGMENT, PLEADING, etc.)
- Contractual (CONTRACT, CONTRACT_PARTY, CONTRACT_TERM, etc.)
- Criminal (CRIME, SENTENCE, PLEA, CHARGE, etc.)
- Property (PROPERTY, DEED, EASEMENT, etc.)
- Intellectual Property (PATENT, TRADEMARK, COPYRIGHT, etc.)
- Corporate (CORPORATION, LLC, PARTNERSHIP, etc.)
- Financial (BANK, ACCOUNT, TAX, etc.)
- And 200+ more specialized entity types

### 3. **context_window_extractor.py**
Extracts contextual windows around entities at multiple levels:
- **Token level**: Configurable token-based windows
- **Sentence level**: Complete sentences around entities
- **Paragraph level**: Full paragraphs containing entities
- **Section level**: Document sections with headers
- **Document level**: Full document context

Features:
- Handles edge cases (beginning/end of document)
- Legal text-aware sentence splitting
- Section header detection for legal documents
- Quality analysis for extracted windows
- Nearby entity extraction

## Usage

### Basic Usage

```python
from src.core.context import ContextResolver, ExtractedEntity
from src.core.model_management.dynamic_model_loader import DynamicModelLoader

# Initialize model loader
model_loader = DynamicModelLoader()

# Create resolver
resolver = ContextResolver(
    dynamic_model_loader=model_loader,
    use_semantic_analysis=True,
    use_dependency_parsing=True,
    confidence_threshold=0.6
)

# Define an entity
entity = ExtractedEntity(
    text="United States District Court",
    type="COURT",
    start_pos=0,
    end_pos=28,
    confidence=0.95
)

# Resolve context
resolved = resolver.resolve_context(
    text=document_text,
    entity=entity,
    all_entities=all_extracted_entities
)

print(f"Primary Context: {resolved.primary_context}")
print(f"Confidence: {resolved.confidence}")
```

### Batch Processing

```python
# Process multiple entities efficiently
resolved_contexts = resolver.batch_resolve_contexts(
    text=document_text,
    entities=entity_list,
    batch_size=10
)
```

### Multi-Level Context Windows

```python
from src.core.context import ContextWindowExtractor, WindowLevel

extractor = ContextWindowExtractor()

# Extract different window levels
sentence_window = extractor.extract_window(text, entity, WindowLevel.SENTENCE)
paragraph_window = extractor.extract_window(text, entity, WindowLevel.PARAGRAPH)
section_window = extractor.extract_window(text, entity, WindowLevel.SECTION)
```

## Integration with Dynamic Model Loader

The context resolver seamlessly integrates with the dynamic model loader to use:
- **Legal-BERT**: For semantic analysis (falls back to base BERT if unavailable)
- **SpaCy Legal**: For dependency parsing (falls back to en_core_web_sm if unavailable)

Models are loaded automatically with priority-based selection:
1. Fine-tuned legal models (if available)
2. Base models (as fallback)

## Configuration

### Method Weights
The resolver uses configurable weights for combining signals:
- Pattern-based: 0.30
- Semantic: 0.35
- Dependency: 0.20
- Section-based: 0.15

### Confidence Thresholds
- Minimum confidence: 0.6 (configurable)
- Entity-specific boosts: 0.1-0.3 based on context match

### Window Sizes
- Token window: 50 tokens (default)
- Sentence window: 3 sentences (default)
- Paragraph window: 1 paragraph (default)

## Performance Considerations

- **Caching**: Models are cached after first load
- **Batch Processing**: Process multiple entities together for efficiency
- **Selective Analysis**: Can disable semantic/dependency analysis if not needed
- **Fallback Strategies**: Automatic fallbacks ensure system continues without all models

## Testing

Run the test script to verify functionality:

```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
python src/core/context/test_context_resolver.py
```

## API Reference

### ContextResolver

Main Methods:
- `resolve_context(text, entity, all_entities)`: Resolve context for single entity
- `batch_resolve_contexts(text, entities, batch_size)`: Batch process entities
- `get_context_quality_score(resolved_context)`: Calculate quality score

### ContextMappings

Main Methods:
- `get_entity_context(entity_type)`: Get mapping for entity type
- `get_entities_by_context(context_type)`: Get entities for context
- `suggest_entity_types_for_context(text)`: Suggest entities based on text

### ContextWindowExtractor

Main Methods:
- `extract_window(text, entity, level, window_size)`: Extract context window
- `extract_multi_level_context(text, entity)`: Extract all window levels
- `extract_surrounding_entities(entity, all_entities)`: Find nearby entities
- `analyze_context_quality(window)`: Analyze window quality

## Error Handling

The system implements comprehensive error handling:
- Graceful degradation when models unavailable
- Fallback context resolution using entity mappings
- Detailed error logging for debugging
- Quality scores to indicate resolution confidence

## Future Enhancements

Potential improvements:
1. Pre-computed Legal-BERT embeddings for context types
2. Fine-tuned models for legal context classification
3. Graph-based context propagation
4. Cross-document context linking
5. Real-time context learning from user feedback