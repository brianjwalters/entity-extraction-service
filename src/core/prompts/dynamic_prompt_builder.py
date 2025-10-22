"""
Dynamic Prompt Builder for Entity Extraction

This module creates enhanced prompts by leveraging the existing PatternLoader system
to inject real examples from the 75 YAML pattern files into both unified and multipass
extraction strategies.
"""

import asyncio
import hashlib
import logging
import httpx
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PromptConfiguration:
    """Configuration for prompt generation."""
    strategy: str  # "multipass" or "unified"
    pass_number: Optional[int] = None  # For multipass strategy
    max_tokens: int = 50000
    examples_per_type: int = 3
    context_window: int = 8000
    confidence_threshold: float = 0.8
    include_pattern_context: bool = True
    include_comprehensive_examples: bool = True
    entity_extraction_service_url: str = "http://10.10.0.87:8007"


@dataclass
class EntityPassDefinition:
    """Definition for a multipass extraction pass."""
    pass_number: int
    pass_name: str
    focus_entities: List[str]
    pattern_sources: List[str]
    examples_per_type: int
    confidence_threshold: float
    priority: int
    description: str


class PromptPatternEnhancer:
    """
    Service that enhances prompts with examples from the existing PatternLoader system.
    Calls the /patterns/comprehensive and /entity-types endpoints to get real examples
    from the 75 YAML pattern files.
    """
    
    def __init__(self, config: PromptConfiguration):
        self.config = config
        self.pattern_cache = {}
        self.entity_cache = {}
        self.http_client = None
        
    async def __aenter__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.http_client:
            await self.http_client.aclose()
    
    async def get_entity_examples_for_prompt(
        self, 
        entity_types: List[str],
        max_examples_per_type: int = 3,
        include_pattern_context: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get examples for specified entity types from PatternLoader via API.
        
        Args:
            entity_types: List of entity types to get examples for
            max_examples_per_type: Maximum examples per entity type
            include_pattern_context: Include pattern hints and metadata
            
        Returns:
            Dict mapping entity types to their examples and metadata
        """
        examples_by_type = {}
        
        try:
            # Call the patterns/comprehensive endpoint for each entity type
            for entity_type in entity_types:
                cache_key = f"{entity_type}_{max_examples_per_type}_{include_pattern_context}"
                
                # Check cache first
                if cache_key in self.pattern_cache:
                    examples_by_type[entity_type] = self.pattern_cache[cache_key]
                    continue
                
                # Make API call to get comprehensive pattern data
                url = f"{self.config.entity_extraction_service_url}/api/v1/patterns/comprehensive"
                params = {
                    "entity_type": entity_type,
                    "include_examples": True,
                    "include_patterns": include_pattern_context
                }
                
                response = await self.http_client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract examples and metadata from the response
                    entity_info = self._extract_entity_info_from_response(
                        data, entity_type, max_examples_per_type
                    )
                    
                    if entity_info:
                        examples_by_type[entity_type] = entity_info
                        # Cache the result
                        self.pattern_cache[cache_key] = entity_info
                    
                else:
                    logger.warning(f"Failed to get patterns for {entity_type}: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error getting entity examples: {e}")
            
        return examples_by_type
    
    async def get_all_entity_types_with_examples(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all entity types with examples from the /entity-types endpoint.
        
        Returns:
            Dict mapping all entity types to their examples and metadata
        """
        cache_key = "all_entity_types"
        
        # Check cache first
        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key]
        
        try:
            url = f"{self.config.entity_extraction_service_url}/api/v1/entity-types"
            params = {
                "include_examples": True,
                "include_descriptions": True
            }
            
            response = await self.http_client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Process entity types and citation types
                all_entities = {}
                
                # Process entity types
                for entity_info in data.get("entity_types", []):
                    entity_type = entity_info.get("type")
                    if entity_type:
                        all_entities[entity_type] = {
                            "examples": entity_info.get("pattern_examples", [])[:3],
                            "description": entity_info.get("description", ""),
                            "pattern_count": entity_info.get("pattern_count", 0),
                            "category": entity_info.get("category", "")
                        }
                
                # Process citation types
                for citation_info in data.get("citation_types", []):
                    citation_type = citation_info.get("type")
                    if citation_type:
                        all_entities[citation_type] = {
                            "examples": citation_info.get("pattern_examples", [])[:3],
                            "description": citation_info.get("description", ""),
                            "pattern_count": citation_info.get("pattern_count", 0),
                            "category": citation_info.get("category", "")
                        }
                
                # Cache the result
                self.entity_cache[cache_key] = all_entities
                return all_entities
                
            else:
                logger.error(f"Failed to get entity types: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting all entity types: {e}")
            return {}
    
    def _extract_entity_info_from_response(
        self, 
        data: Dict, 
        entity_type: str, 
        max_examples: int
    ) -> Optional[Dict[str, Any]]:
        """
        Extract entity information from the patterns/comprehensive API response.
        """
        try:
            patterns_data = data.get("patterns", [])
            
            if not patterns_data:
                return None
            
            # Collect all examples from patterns
            all_examples = []
            pattern_hints = []
            confidence_scores = []
            
            for pattern_info in patterns_data:
                examples = pattern_info.get("examples", [])
                all_examples.extend(examples)
                
                # Extract pattern hints
                description = pattern_info.get("description", "")
                if description:
                    pattern_hints.append(description)
                
                # Track confidence scores
                confidence = pattern_info.get("confidence", 0.8)
                confidence_scores.append(confidence)
            
            # Remove duplicates and limit examples
            unique_examples = list(dict.fromkeys(all_examples))[:max_examples]
            
            # Calculate average confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.8
            
            return {
                "examples": unique_examples,
                "pattern_hints": pattern_hints[:2],  # Limit to avoid bloat
                "confidence": avg_confidence,
                "pattern_count": len(patterns_data)
            }
            
        except Exception as e:
            logger.error(f"Error extracting entity info for {entity_type}: {e}")
            return None


class DynamicPromptBuilder:
    """
    Main prompt builder that creates enhanced prompts for both unified and multipass
    strategies using examples from the existing PatternLoader system.
    """
    
    def __init__(self, config: PromptConfiguration = None):
        self.config = config or PromptConfiguration()
        self.multipass_passes = self._define_multipass_passes()
        
    def _define_multipass_passes(self) -> List[EntityPassDefinition]:
        """
        Define the 7 specialized passes for multipass extraction strategy.
        Based on the existing pattern library and entity type distributions.
        """
        return [
            EntityPassDefinition(
                pass_number=1,
                pass_name="Core Legal Entities",
                focus_entities=[
                    "CASE_CITATION", "STATUTE_CITATION", "PARTY", "ATTORNEY", 
                    "COURT", "JUDGE", "PLAINTIFF", "DEFENDANT"
                ],
                pattern_sources=["case_citations.yaml", "attorneys.yaml", "court_names.yaml", "judges.yaml"],
                examples_per_type=4,
                confidence_threshold=0.9,
                priority=1,
                description="Extract the most critical legal entities with highest precision"
            ),
            EntityPassDefinition(
                pass_number=2,
                pass_name="Legal Citations & References", 
                focus_entities=[
                    "USC_CITATION", "CFR_CITATION", "STATE_STATUTE_CITATION",
                    "CONSTITUTIONAL_CITATION", "FEDERAL_CASE_CITATION", "STATE_CASE_CITATION"
                ],
                pattern_sources=["usc_statutes.yaml", "cfr_regulations.yaml", "statute_citations.yaml"],
                examples_per_type=4,
                confidence_threshold=0.85,
                priority=2,
                description="Focus on statutory and regulatory citations with Bluebook compliance"
            ),
            EntityPassDefinition(
                pass_number=3,
                pass_name="Case Information & Procedural Elements",
                focus_entities=[
                    "CASE_NUMBER", "DOCKET_NUMBER", "MOTION", "BRIEF", 
                    "PROCEDURAL_RULE", "JURISDICTION", "VENUE"
                ],
                pattern_sources=["structure.yaml", "procedural_terms.yaml"],
                examples_per_type=3,
                confidence_threshold=0.8,
                priority=3,
                description="Extract case identifiers and procedural information"
            ),
            EntityPassDefinition(
                pass_number=4,
                pass_name="Dates, Deadlines & Temporal Information",
                focus_entities=[
                    "DATE", "FILING_DATE", "DEADLINE", "HEARING_DATE", 
                    "TRIAL_DATE", "DECISION_DATE", "EFFECTIVE_DATE"
                ],
                pattern_sources=["dates.yaml"],
                examples_per_type=3,
                confidence_threshold=0.85,
                priority=4,
                description="Identify all temporal references and legal deadlines"
            ),
            EntityPassDefinition(
                pass_number=5,
                pass_name="Financial & Monetary Elements",
                focus_entities=[
                    "MONETARY_AMOUNT", "DAMAGES", "FINE", "FEE", 
                    "AWARD", "SETTLEMENT_AMOUNT", "COST"
                ],
                pattern_sources=["monetary_amounts.yaml"],
                examples_per_type=3,
                confidence_threshold=0.8,
                priority=5,
                description="Extract all financial amounts and monetary references"
            ),
            EntityPassDefinition(
                pass_number=6,
                pass_name="Legal Professionals & Organizations",
                focus_entities=[
                    "LAW_FIRM", "PROSECUTOR", "PUBLIC_DEFENDER", 
                    "GOVERNMENT_ENTITY", "FEDERAL_AGENCY", "STATE_AGENCY"
                ],
                pattern_sources=["law_firms.yaml", "attorneys.yaml"],
                examples_per_type=2,
                confidence_threshold=0.75,
                priority=6,
                description="Identify legal professionals and organizational entities"
            ),
            EntityPassDefinition(
                pass_number=7,
                pass_name="Geographic & Miscellaneous Entities",
                focus_entities=[
                    "ADDRESS", "EMAIL", "PHONE_NUMBER", "BAR_NUMBER", 
                    "CORPORATION", "PARTNERSHIP", "NONPROFIT"
                ],
                pattern_sources=["addresses.yaml"],
                examples_per_type=2,
                confidence_threshold=0.7,
                priority=7,
                description="Extract contact information and miscellaneous entities"
            )
        ]
    
    async def build_enhanced_prompt(
        self,
        document_text: str,
        strategy: str,
        pass_number: Optional[int] = None,
        target_entities: Optional[List[str]] = None
    ) -> str:
        """
        Build an enhanced prompt with examples from PatternLoader.
        
        Args:
            document_text: The document to extract entities from
            strategy: "unified" or "multipass"
            pass_number: Pass number for multipass strategy
            target_entities: Specific entity types to focus on
            
        Returns:
            Enhanced prompt string with injected examples
        """
        async with PromptPatternEnhancer(self.config) as enhancer:
            if strategy == "multipass" and pass_number is not None:
                return await self._build_multipass_prompt(
                    document_text, pass_number, enhancer
                )
            else:
                return await self._build_unified_prompt(
                    document_text, target_entities, enhancer
                )
    
    async def _build_multipass_prompt(
        self,
        document_text: str,
        pass_number: int,
        enhancer: PromptPatternEnhancer
    ) -> str:
        """
        Build a specialized prompt for a specific multipass pass.
        """
        # Get the pass definition
        pass_def = None
        for p in self.multipass_passes:
            if p.pass_number == pass_number:
                pass_def = p
                break
        
        if not pass_def:
            raise ValueError(f"Invalid pass number: {pass_number}")
        
        # Get examples for the focus entities
        entity_examples = await enhancer.get_entity_examples_for_prompt(
            entity_types=pass_def.focus_entities,
            max_examples_per_type=pass_def.examples_per_type,
            include_pattern_context=True
        )
        
        # Build the specialized prompt
        prompt = f"""# Entity Extraction Pass {pass_def.pass_number}: {pass_def.pass_name}

## Objective
{pass_def.description}

## Target Entity Types
Extract the following entity types with high precision:

"""
        
        # Add entity type definitions and examples
        for entity_type in pass_def.focus_entities:
            prompt += f"\n### {entity_type}\n"
            
            entity_info = entity_examples.get(entity_type)
            if entity_info:
                examples = entity_info.get("examples", [])
                if examples:
                    prompt += "**Examples**:\n"
                    for i, example in enumerate(examples, 1):
                        prompt += f"{i}. \"{example}\"\n"
                    prompt += "\n"
                
                # Add pattern hints if available
                hints = entity_info.get("pattern_hints", [])
                if hints:
                    prompt += "**Pattern Guidance**:\n"
                    for hint in hints:
                        prompt += f"- {hint}\n"
                    prompt += "\n"
            else:
                prompt += "**Note**: No specific examples available for this entity type.\n\n"
        
        # Add extraction instructions
        prompt += f"""
## Extraction Instructions
1. **Focus**: Only extract the {len(pass_def.focus_entities)} entity types listed above
2. **Confidence**: Minimum confidence threshold is {pass_def.confidence_threshold}
3. **Precision**: Prefer high precision over recall for this specialized pass
4. **Context**: Use the legal document context to inform extraction decisions

## Output Format
Return results as JSON with this exact structure:
{{
  "entities": [
    {{
      "entity_type": "ENTITY_TYPE",
      "text": "exact text from document", 
      "confidence": 0.95,
      "start_position": 100,
      "end_position": 150,
      "context": "surrounding text for validation"
    }}
  ],
  "pass_summary": {{
    "pass_number": {pass_def.pass_number},
    "entities_found": 0,
    "high_confidence_count": 0,
    "processing_notes": "any important observations"
  }}
}}

## Document Text to Analyze
{document_text}

⚡ Execute extraction NOW. Output starts with {{ and ends with }}
FIRST CHARACTER OF YOUR RESPONSE MUST BE {{
LAST CHARACTER OF YOUR RESPONSE MUST BE }}
"""
        
        return prompt
    
    async def _build_unified_prompt(
        self,
        document_text: str,
        target_entities: Optional[List[str]],
        enhancer: PromptPatternEnhancer
    ) -> str:
        """
        Build a comprehensive prompt for unified extraction strategy.
        """
        # Get all entity types with examples if target_entities not specified
        if target_entities is None:
            all_entity_data = await enhancer.get_all_entity_types_with_examples()
            target_entities = list(all_entity_data.keys())[:50]  # Limit to avoid token overflow
        
        # Get examples for target entities
        entity_examples = await enhancer.get_entity_examples_for_prompt(
            entity_types=target_entities,
            max_examples_per_type=self.config.examples_per_type,
            include_pattern_context=True
        )
        
        # Build comprehensive prompt
        prompt = """# Comprehensive Legal Entity Extraction

## Objective
Extract ALL legal entities from the provided document with high accuracy and completeness.

## Supported Entity Types
This system recognizes 275+ entity types with examples from the pattern library:

"""
        
        # Group entities by category for better organization
        entity_clusters = self._cluster_entities_by_domain(target_entities)
        
        for cluster_name, cluster_entities in entity_clusters.items():
            prompt += f"\n### {cluster_name}\n"
            
            for entity_type in cluster_entities[:10]:  # Limit per cluster to manage tokens
                entity_info = entity_examples.get(entity_type)
                if entity_info and entity_info.get("examples"):
                    examples = entity_info["examples"][:2]  # Limit examples for unified
                    example_text = ", ".join(f'"{ex}"' for ex in examples)
                    prompt += f"- **{entity_type}**: {example_text}\n"
        
        # Add comprehensive extraction instructions
        prompt += f"""

## Advanced Extraction Guidelines

### Entity Relationship Awareness
- Consider relationships between entities (attorney represents party, case cites precedent)
- Maintain context awareness across the document
- Handle entity co-references and aliases

### Legal Document Context
- Adapt extraction based on document type (motion, brief, contract, opinion)
- Apply domain-specific validation rules
- Consider procedural context and litigation stage

### Quality Standards
- Minimum confidence threshold: {self.config.confidence_threshold}
- Prefer precision over recall for critical entities (citations, parties)
- Flag ambiguous cases for manual review

## Output Format
Provide comprehensive JSON output:
{{
  "entities": [
    {{
      "entity_type": "ENTITY_TYPE",
      "text": "exact text",
      "confidence": 0.95,
      "start_position": 100,
      "end_position": 150,
      "context": "surrounding text",
      "normalized_value": "standardized form"
    }}
  ],
  "document_analysis": {{
    "document_type": "inferred_type",
    "jurisdiction": "detected_jurisdiction", 
    "entity_count_by_type": {{}}
  }}
}}

## Document Text to Analyze
{document_text}

⚡ IMMEDIATE ACTION REQUIRED:
Execute extraction NOW. Output starts with {{ and ends with }}
No explanations. No formatting. Just JSON.
FIRST CHARACTER OF YOUR RESPONSE MUST BE {{
LAST CHARACTER OF YOUR RESPONSE MUST BE }}
"""
        
        return prompt
    
    def _cluster_entities_by_domain(self, entity_types: List[str]) -> Dict[str, List[str]]:
        """
        Group entity types by legal domain for better prompt organization.
        """
        clusters = {
            "Core Legal Entities": [],
            "Citations & References": [],
            "Court & Procedural": [],
            "Financial & Temporal": [],
            "Parties & Organizations": [],
            "Other Entities": []
        }
        
        # Define clustering rules based on entity type names
        for entity_type in entity_types:
            if any(term in entity_type.upper() for term in ["CITATION", "USC", "CFR", "STATUTE"]):
                clusters["Citations & References"].append(entity_type)
            elif any(term in entity_type.upper() for term in ["COURT", "JUDGE", "MOTION", "BRIEF"]):
                clusters["Court & Procedural"].append(entity_type)
            elif any(term in entity_type.upper() for term in ["PARTY", "ATTORNEY", "PLAINTIFF", "DEFENDANT"]):
                clusters["Core Legal Entities"].append(entity_type)
            elif any(term in entity_type.upper() for term in ["MONETARY", "DATE", "DEADLINE", "AMOUNT"]):
                clusters["Financial & Temporal"].append(entity_type)
            elif any(term in entity_type.upper() for term in ["ORGANIZATION", "FIRM", "AGENCY", "CORPORATION"]):
                clusters["Parties & Organizations"].append(entity_type)
            else:
                clusters["Other Entities"].append(entity_type)
        
        # Remove empty clusters
        return {k: v for k, v in clusters.items() if v}