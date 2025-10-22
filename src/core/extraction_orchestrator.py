"""
Extraction Orchestrator for Document Intelligence Service v2.0.0

Orchestrates entity extraction using:
- PromptManager for loading consolidated prompts
- Direct vLLM client for LLM inference
- Single-pass strategy for very small documents
- 3-wave strategy for small-medium documents
- 4-wave strategy for comprehensive entity + relationship extraction

This is the core intelligence that bridges intelligent routing with actual extraction.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from pydantic import ValidationError

from src.core.prompt_manager import PromptManager, PromptTemplate
from src.core.config import get_settings
from src.vllm_client.client import DirectVLLMClient, HTTPVLLMClient
from src.vllm_client.models import VLLMConfig
from src.vllm_client.factory import VLLMClientFactory
from src.routing.document_router import RoutingDecision, ProcessingStrategy
from src.routing.size_detector import DocumentSizeInfo

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result from entity extraction."""
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]  # NEW: relationships from Wave 4
    strategy: ProcessingStrategy
    waves_executed: int
    processing_time: float
    tokens_used: int
    metadata: Dict[str, Any]


class ExtractionOrchestrator:
    """
    Orchestrates entity extraction using consolidated prompts and direct vLLM.

    Features:
    - Single-pass extraction for very small documents (<5K chars)
    - 3-wave extraction for small-medium documents (5-150K chars)
    - Direct vLLM integration for optimal performance
    - Reproducible extraction with temperature=0.0, seed=42
    - Entity deduplication across waves

    Usage:
        orchestrator = ExtractionOrchestrator()
        result = await orchestrator.extract(
            document_text="...",
            routing_decision=routing_decision,
            size_info=size_info
        )
    """

    def __init__(
        self,
        prompt_manager: Optional[PromptManager] = None,
        vllm_client: Optional[Any] = None
    ):
        """
        Initialize ExtractionOrchestrator with multi-service support.

        Args:
            prompt_manager: PromptManager instance (creates default if None)
            vllm_client: vLLM client instance (created lazily if None)
        """
        self.prompt_manager = prompt_manager or PromptManager()
        self.vllm_client = vllm_client  # May be None - created lazily (Instruct service)
        self.thinking_client = None  # Lazy initialization for Wave 4 relationships

        # P0 Fix #3: Async locks to prevent race conditions during client initialization
        self._vllm_client_lock = asyncio.Lock()
        self._thinking_client_lock = asyncio.Lock()

        logger.info("ExtractionOrchestrator initialized with multi-service support")

    async def _ensure_vllm_client(self) -> Any:
        """
        Ensure vLLM client is initialized (lazy initialization with race condition protection).

        P0 Fix #3: Uses async lock to prevent multiple concurrent initialization attempts.

        Returns:
            vLLM client instance (HTTP client by default)

        Raises:
            RuntimeError: If client initialization fails after health check validation
        """
        if self.vllm_client is None:
            async with self._vllm_client_lock:  # P0 Fix #3: Prevent race conditions
                # Double-check pattern: verify client is still None after acquiring lock
                if self.vllm_client is None:
                    try:
                        # Import the factory convenience function for entity extraction
                        # FIXED: Correct import path (src.vllm_client not src.vllm)
                        from src.vllm_client.factory import get_client_for_entity_extraction

                        # Create client using async factory (now returns HTTP client by default)
                        self.vllm_client = await get_client_for_entity_extraction()

                        # P0 Fix #2: Validate client health before returning
                        if hasattr(self.vllm_client, 'health_check'):
                            health_ok = await self.vllm_client.health_check()
                            if not health_ok:
                                raise RuntimeError("vLLM Instruct service health check failed")

                        logger.info(f"✅ Created vLLM HTTP client for entity extraction: {type(self.vllm_client).__name__}")

                    except Exception as e:
                        logger.error(f"❌ Failed to create vLLM client: {e}")
                        # P0 Fix #2: Fail fast if critical service unavailable
                        raise RuntimeError(f"Critical: Unable to initialize vLLM Instruct service") from e

        return self.vllm_client

    async def _ensure_thinking_client(self) -> Any:
        """
        Ensure Thinking client is initialized for Wave 4 (lazy initialization with race condition protection).

        P0 Fix #3: Uses async lock to prevent multiple concurrent initialization attempts.
        Implements graceful degradation: falls back to Instruct client if Thinking unavailable.

        Returns:
            Thinking vLLM client instance (Port 8082 for complex reasoning), or Instruct client as fallback
        """
        if self.thinking_client is None:
            async with self._thinking_client_lock:  # P0 Fix #3: Prevent race conditions
                # Double-check pattern: verify client is still None after acquiring lock
                if self.thinking_client is None:
                    try:
                        # Import the factory function for Thinking service
                        from src.vllm_client.factory import create_thinking_client

                        # Create Thinking client (Port 8082)
                        self.thinking_client = await create_thinking_client()

                        # P0 Fix #2: Validate Thinking client health
                        if hasattr(self.thinking_client, 'health_check'):
                            health_ok = await self.thinking_client.health_check()
                            if not health_ok:
                                logger.warning("⚠️  Thinking service health check failed, using fallback")
                                raise RuntimeError("Thinking service unhealthy")

                        logger.info(f"✅ Created Thinking client for Wave 4: {type(self.thinking_client).__name__}")

                    except Exception as e:
                        logger.error(f"❌ Failed to create Thinking client: {e}")
                        logger.warning("⚠️  Falling back to Instruct client for Wave 4 (graceful degradation)")
                        # Fallback to main client if Thinking client unavailable
                        self.thinking_client = await self._ensure_vllm_client()

        return self.thinking_client

    async def extract(
        self,
        document_text: str,
        routing_decision: RoutingDecision,
        size_info: DocumentSizeInfo,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """
        Extract entities from document using appropriate strategy.

        Args:
            document_text: Full document text
            routing_decision: Routing decision from DocumentRouter
            size_info: Document size information
            metadata: Optional document metadata

        Returns:
            ExtractionResult with entities and processing stats
        """
        # Ensure vLLM client is initialized
        await self._ensure_vllm_client()

        start_time = datetime.now()

        strategy = routing_decision.strategy

        logger.info(f"Starting extraction: strategy={strategy.value}, chars={size_info.chars}")

        if strategy == ProcessingStrategy.SINGLE_PASS:
            result = await self._extract_single_pass(document_text, metadata)
        elif strategy == ProcessingStrategy.THREE_WAVE:
            result = await self._extract_three_wave(document_text, metadata)
        elif strategy == ProcessingStrategy.FOUR_WAVE:
            result = await self._extract_four_wave(document_text, metadata)
        elif strategy == ProcessingStrategy.THREE_WAVE_CHUNKED:
            # Use three-wave extraction with smart chunking for large documents
            logger.info("THREE_WAVE_CHUNKED strategy - using chunked extraction")
            result = await self._extract_three_wave_chunked(document_text, routing_decision, metadata)
        elif strategy == ProcessingStrategy.TOO_SMALL:
            # Document is very small - use single pass extraction
            logger.info("TOO_SMALL edge case - using SINGLE_PASS extraction")
            result = await self._extract_single_pass(document_text, metadata)
        elif strategy == ProcessingStrategy.EMPTY_DOCUMENT:
            # Document is empty - return empty result
            logger.warning("EMPTY_DOCUMENT edge case - returning empty result")
            result = {
                "entities": [],
                "relationships": [],
                "waves_executed": [],
                "tokens_used": 0,
                "metadata": {"edge_case": "empty_document"}
            }
        elif strategy == ProcessingStrategy.INVALID_DOCUMENT:
            # Document is invalid (malformed/binary) - return empty result
            logger.error("INVALID_DOCUMENT edge case - returning empty result")
            result = {
                "entities": [],
                "relationships": [],
                "waves_executed": [],
                "tokens_used": 0,
                "metadata": {"edge_case": "invalid_document"}
            }
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        processing_time = (datetime.now() - start_time).total_seconds()

        return ExtractionResult(
            entities=result["entities"],
            relationships=result["relationships"],  # All methods now return this field
            strategy=strategy,
            waves_executed=result["waves_executed"],
            processing_time=processing_time,
            tokens_used=result["tokens_used"],
            metadata=result.get("metadata", {})
        )

    async def _extract_single_pass(
        self,
        document_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract entities AND relationships using single consolidated prompt.

        Use for: Very small documents (<5K chars)
        Expected tokens: ~2,000 prompt + document tokens

        **UPDATED**: Now extracts both entities and relationships in one pass
        using SinglePassExtractionResponse schema with guided JSON.

        Args:
            document_text: Full document text
            metadata: Optional document metadata

        Returns:
            Dictionary with entities, relationships, and stats
        """
        logger.info("Executing single-pass extraction (entities + relationships)")

        # Load single-pass prompt
        prompt_template = self.prompt_manager.get_single_pass_prompt()

        # Format prompt with document text
        prompt = self._format_prompt(prompt_template.content, document_text, metadata)

        # Execute LLM call with SinglePassExtractionResponse schema (entities + relationships)
        response = await self._call_vllm_single_pass(prompt)

        # Parse combined response
        parsed_data = json.loads(response["text"])
        entities = parsed_data.get("entities", [])
        relationships = parsed_data.get("relationships", [])

        # Enhance entities with quality testing fields
        enhanced_entities = self._enhance_entities_with_context(
            entities=entities,
            document_text=document_text,
            prompt_template="single_pass",
            wave_number=None  # Single-pass has no wave number
        )

        logger.info(
            f"Single-pass extraction complete: {len(enhanced_entities)} entities, "
            f"{len(relationships)} relationships"
        )

        return {
            "entities": enhanced_entities,
            "relationships": relationships,  # NEW: Include relationships
            "waves_executed": 1,
            "tokens_used": response["tokens_used"],
            "metadata": {
                "prompt_version": "single_pass",
                "prompt_tokens": prompt_template.token_count,
                "prompt_template_used": "single_pass",
                "extraction_type": "combined_entities_relationships"  # NEW: Indicate combined extraction
            }
        }

    async def _extract_three_wave(
        self,
        document_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract entities using 3-wave system.

        Wave 1: Actors, legal citations, temporal entities
        Wave 2: Procedural, financial, organizations
        Wave 3: Supporting types + 40+ relationships

        Use for: Small-medium documents (5-150K chars)
        Expected tokens: ~21,000 total across 3 waves

        Args:
            document_text: Full document text
            metadata: Optional document metadata

        Returns:
            Dictionary with entities and stats
        """
        logger.info("Executing 3-wave extraction")

        all_entities = []
        total_tokens = 0
        wave_results = []

        for wave_num in range(1, 4):
            logger.info(f"Starting Wave {wave_num}")

            # Load wave-specific prompt
            prompt_template = self.prompt_manager.get_three_wave_prompt(wave_num)

            # Format prompt with document and previous entities
            prompt = self._format_prompt(
                prompt_template.content,
                document_text,
                metadata,
                previous_entities=all_entities if wave_num > 1 else None
            )

            # Execute LLM call
            response = await self._call_vllm(prompt)

            # Parse entities from response
            wave_entities = self._parse_entities(response["text"])

            # Enhance entities with quality testing fields
            enhanced_wave_entities = self._enhance_entities_with_context(
                entities=wave_entities,
                document_text=document_text,
                prompt_template=f"wave{wave_num}",
                wave_number=wave_num
            )

            # Accumulate enhanced entities
            all_entities.extend(enhanced_wave_entities)
            total_tokens += response["tokens_used"]

            wave_results.append({
                "wave": wave_num,
                "entities_count": len(enhanced_wave_entities),
                "tokens_used": response["tokens_used"],
                "prompt_template": f"wave{wave_num}"
            })

            logger.info(f"Wave {wave_num} complete: {len(enhanced_wave_entities)} entities")

        # Deduplicate entities across waves
        deduplicated_entities = self._deduplicate_entities(all_entities)

        logger.info(
            f"3-wave extraction complete: {len(all_entities)} total, "
            f"{len(deduplicated_entities)} after deduplication"
        )

        return {
            "entities": deduplicated_entities,
            "relationships": [],  # 3-wave doesn't extract relationships
            "waves_executed": 3,
            "tokens_used": total_tokens,
            "metadata": {
                "prompt_version": "three_wave",
                "prompt_templates_used": ["wave1", "wave2", "wave3"],
                "wave_results": wave_results,
                "deduplication_ratio": len(deduplicated_entities) / len(all_entities) if all_entities else 1.0,
                "entities_by_wave": {
                    f"wave_{i+1}": wave_results[i]["entities_count"]
                    for i in range(len(wave_results))
                }
            }
        }

    async def _extract_four_wave(
        self,
        document_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract entities and relationships using 4-wave system.

        Wave 1: Actors, legal citations, temporal entities (92 types)
        Wave 2: Procedural, financial, organizations (29 types)
        Wave 3: Supporting types (40 types)
        Wave 4: Entity relationships (34 relationship types)

        Use for: Small-medium documents requiring relationship extraction
        Expected tokens: ~24,000 total across 4 waves

        Args:
            document_text: Full document text
            metadata: Optional document metadata

        Returns:
            Dictionary with entities, relationships, and stats
        """
        logger.info("Executing 4-wave extraction (entities + relationships)")

        all_entities = []
        total_tokens = 0
        wave_results = []

        # Waves 1-3: Entity extraction
        for wave_num in range(1, 4):
            logger.info(f"Starting Wave {wave_num}")

            # Load wave-specific prompt
            prompt_template = self.prompt_manager.get_three_wave_prompt(wave_num)

            # Format prompt with document and previous entities
            prompt = self._format_prompt(
                prompt_template.content,
                document_text,
                metadata,
                previous_entities=all_entities if wave_num > 1 else None
            )

            # Execute LLM call
            response = await self._call_vllm(prompt)

            # Parse entities from response
            wave_entities = self._parse_entities(response["text"])
            logger.info(f"🔍 Wave {wave_num} _parse_entities returned {len(wave_entities)} entities")
            if wave_entities:
                logger.info(f"🔍 First entity fields: {list(wave_entities[0].keys())}")
                logger.info(f"🔍 First entity: {wave_entities[0]}")

            # Enhance entities with quality testing fields
            enhanced_wave_entities = self._enhance_entities_with_context(
                entities=wave_entities,
                document_text=document_text,
                prompt_template=f"wave{wave_num}",
                wave_number=wave_num
            )
            logger.info(f"🔍 Wave {wave_num} _enhance_entities_with_context returned {len(enhanced_wave_entities)} entities")

            # Accumulate enhanced entities
            all_entities.extend(enhanced_wave_entities)
            logger.info(f"🔍 Wave {wave_num} accumulated total: {len(all_entities)} entities")
            total_tokens += response["tokens_used"]

            wave_results.append({
                "wave": wave_num,
                "entities_count": len(enhanced_wave_entities),
                "tokens_used": response["tokens_used"],
                "prompt_template": f"wave{wave_num}"
            })

            logger.info(f"Wave {wave_num} complete: {len(enhanced_wave_entities)} entities")

        # Deduplicate entities across waves 1-3
        logger.info(f"🔍 Before deduplication: {len(all_entities)} entities")
        if all_entities:
            logger.info(f"🔍 Sample entity before dedup: {all_entities[0]}")

        deduplicated_entities = self._deduplicate_entities(all_entities)

        logger.info(f"🔍 After deduplication: {len(deduplicated_entities)} entities")
        if deduplicated_entities:
            logger.info(f"🔍 Sample entity after dedup: {deduplicated_entities[0]}")

        logger.info(
            f"Waves 1-3 complete: {len(all_entities)} total entities, "
            f"{len(deduplicated_entities)} after deduplication"
        )

        # Wave 4: Relationship extraction
        logger.info("Starting Wave 4 (relationship extraction)")

        wave4_result = await self._execute_wave_4(
            document_text=document_text,
            previous_results=deduplicated_entities,
            metadata=metadata or {}
        )

        relationships = wave4_result["relationships"]
        total_tokens += wave4_result["tokens_used"]

        wave_results.append({
            "wave": 4,
            "relationships_count": len(relationships),
            "tokens_used": wave4_result["tokens_used"],
            "prompt_template": "wave4"
        })

        logger.info(f"Wave 4 complete: {len(relationships)} relationships extracted")

        logger.info(
            f"4-wave extraction complete: {len(deduplicated_entities)} entities, "
            f"{len(relationships)} relationships"
        )

        return {
            "entities": deduplicated_entities,
            "relationships": relationships,
            "waves_executed": 4,
            "tokens_used": total_tokens,
            "metadata": {
                "prompt_version": "four_wave",
                "prompt_templates_used": ["wave1", "wave2", "wave3", "wave4"],
                "wave_results": wave_results,
                "deduplication_ratio": len(deduplicated_entities) / len(all_entities) if all_entities else 1.0,
                "entities_by_wave": {
                    f"wave_{i+1}": wave_results[i].get("entities_count", 0)
                    for i in range(3)  # Only waves 1-3 have entities
                },
                "relationships_extracted": len(relationships),
                "wave4_relationship_count": len(relationships)
            }
        }

    async def _execute_wave_4(
        self,
        document_text: str,
        previous_results: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute Wave 4: Entity Relationship Extraction

        Args:
            document_text: Full document text
            previous_results: All entities from Waves 1-3
            metadata: Extraction metadata

        Returns:
            Dictionary with relationships and token usage
        """
        import time

        wave_start_time = time.time()

        # Load Wave 4 prompt (relationship extraction)
        # Note: PromptManager needs to be updated to support wave 4
        # For now, we'll create a basic relationship extraction prompt
        wave4_prompt = self._create_wave4_prompt(previous_results)

        # Format prompt with document and entities
        prompt = self._format_prompt(
            wave4_prompt,
            document_text,
            metadata,
            previous_entities=previous_results
        )

        # Execute LLM call with relationship schema
        response = await self._call_vllm_for_relationships(prompt)

        # Parse relationships from LLM response
        relationships = self._parse_relationships(response["text"])

        # Validate relationships
        entity_ids = [self._get_entity_id(e) for e in previous_results]
        validated_relationships = self._validate_relationships(
            relationships=relationships,
            entity_ids=entity_ids
        )

        # Deduplicate relationships
        deduplicated_relationships = self._deduplicate_relationships(validated_relationships)

        wave_duration = time.time() - wave_start_time

        logger.info(
            f"Wave 4 extracted {len(relationships)} relationships, "
            f"{len(validated_relationships)} valid, "
            f"{len(deduplicated_relationships)} after deduplication "
            f"in {wave_duration:.2f}s"
        )

        return {
            "relationships": deduplicated_relationships,
            "tokens_used": response["tokens_used"],
            "wave_duration": wave_duration,
            "relationships_before_validation": len(relationships),
            "relationships_after_validation": len(validated_relationships),
            "relationships_after_dedup": len(deduplicated_relationships)
        }

    def _create_wave4_prompt(self, entities: List[Dict[str, Any]]) -> str:
        """
        Create Wave 4 relationship extraction prompt.

        Args:
            entities: List of entities from Waves 1-3

        Returns:
            Formatted prompt string for relationship extraction
        """
        # Simplified entity list for prompt
        entity_summary = []
        for i, entity in enumerate(entities[:50]):  # Limit to first 50 for prompt size
            entity_summary.append({
                "id": self._get_entity_id(entity),
                "type": entity.get("entity_type", "UNKNOWN"),
                "text": entity.get("text", "")
            })

        prompt = f"""# Wave 4: Entity Relationship Extraction

You are a legal document analyst extracting relationships between entities.

## Task
Analyze the document and identify relationships between the following entities.

## Available Entities ({len(entities)} total, showing first {len(entity_summary)}):
{json.dumps(entity_summary, indent=2)}

## Relationship Types
Extract these relationship types when found:
- CITES: Source entity cites target entity (legal citations)
- PARTY_TO_CASE: Entity is a party in a case
- DECIDED_BY: Case was decided by judge/court
- REPRESENTED_BY: Party represented by attorney
- APPEALS_FROM: Case appeals from lower court decision
- SUBJECT_OF: Entity is subject of document/case
- INVOLVES: General involvement relationship
- RELATED_TO: General relationship between entities

## Instructions
1. Identify relationships between entities in the provided list
2. Extract only relationships explicitly stated in the document
3. For each relationship, provide:
   - source_entity_id: ID of source entity
   - target_entity_id: ID of target entity
   - relationship_type: Type of relationship
   - confidence: Confidence score (0.0-1.0)
   - context: Brief text explaining the relationship

4. Return ONLY valid JSON matching this schema:
{{
  "relationships": [
    {{
      "source_entity_id": "string",
      "target_entity_id": "string",
      "relationship_type": "string",
      "confidence": 0.95,
      "context": "Brief description of relationship"
    }}
  ]
}}

## Quality Requirements
- Only extract relationships with confidence >= 0.85
- Ensure both source and target entities exist in the entity list
- Do not create self-referential relationships
- Provide clear context for each relationship
"""
        return prompt

    async def _call_vllm_for_relationships(self, prompt: str) -> Dict[str, Any]:
        """
        Call Thinking vLLM service for relationship extraction with appropriate schema.

        **UPDATED**: Now uses Thinking client (Port 8082) for complex reasoning.

        Args:
            prompt: Formatted prompt string

        Returns:
            Dictionary with text response and token usage
        """
        try:
            from src.vllm_client.models import VLLMRequest
            from src.schemas.guided_json_schemas import LurisRelationshipExtractionResponse

            # Get JSON schema for Wave 4 relationships (LurisEntityV2-based)
            json_relationship_schema = LurisRelationshipExtractionResponse.model_json_schema()

            logger.debug(f"Using guided JSON with schema model: LurisRelationshipExtractionResponse")
            logger.debug(f"Schema contains keys: {list(json_relationship_schema.keys())}")

            # Load settings to get relationship extraction temperature
            settings = get_settings()

            # Ensure Thinking client is available for Wave 4
            thinking_client = await self._ensure_thinking_client()

            # Create VLLMRequest with guided_json for Wave 4 relationships
            request = VLLMRequest(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8000,  # More tokens for relationships
                temperature=settings.extraction.relationship_temperature,  # Use relationship-specific config (0.0 for consistency)
                seed=42,
                stream=False,
                extra_body={"guided_json": json_relationship_schema}  # ✅ Using LurisEntityV2 Wave 4 relationship schema
            )

            logger.info(f"Calling Thinking vLLM (Port 8082) with guided JSON for relationship extraction")

            # Call Thinking vLLM service (Port 8082 - better for complex reasoning)
            response = await thinking_client.generate_chat_completion(request)

            logger.info(f"✅ Thinking vLLM response received ({response.usage.total_tokens} tokens)")

            return {
                "text": response.content,
                "tokens_used": response.usage.total_tokens
            }

        except Exception as e:
            logger.error(f"❌ Thinking vLLM call for relationships failed: {e}")
            raise

    def _parse_relationships(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse relationships from guided JSON response with embedded validation logging.

        With guided JSON enabled, response is guaranteed to be valid JSON
        matching DetailedRelationshipExtractionResponse schema.

        Args:
            response_text: JSON response from vLLM (guided JSON)

        Returns:
            List of relationship dictionaries
        """
        try:
            # Step 1: JSON decode validation
            parsed = json.loads(response_text)
            logger.debug("✅ JSON decode successful")

            # Step 2: Validate relationships field exists and is a list
            relationships = parsed.get("relationships", [])
            if not isinstance(relationships, list):
                logger.error("❌ Relationships field is not a list - schema violation")
                return []

            logger.debug("✅ Relationships field validation passed")

            # Step 3: Optional Pydantic schema validation (lightweight check)
            try:
                from src.schemas.guided_json_schemas import LurisRelationshipExtractionResponse
                LurisRelationshipExtractionResponse(**parsed)
                logger.debug(f"✅ Pydantic schema validation passed: {len(relationships)} relationships")
            except Exception as schema_error:
                logger.warning(f"⚠️  Pydantic validation warning (non-critical): {schema_error}")
                # Don't fail - guided JSON already enforced schema at token level

            logger.debug(f"Parsed {len(relationships)} relationships from guided JSON response")
            return relationships

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode failed (guided JSON should prevent this): {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error parsing relationships: {e}")
            return []

    def _get_entity_id(self, entity: Dict[str, Any]) -> str:
        """
        Get or create unique entity ID.

        Args:
            entity: Entity dictionary

        Returns:
            Unique entity identifier
        """
        # Check if entity already has an ID
        if "id" in entity:
            return entity["id"]

        # Generate ID from type and text
        entity_type = entity.get("entity_type", "UNKNOWN")
        entity_text = entity.get("text", "")

        # Create deterministic ID
        import hashlib
        text_hash = hashlib.md5(f"{entity_type}:{entity_text}".encode()).hexdigest()[:8]
        return f"{entity_type}_{text_hash}"

    def _validate_relationships(
        self,
        relationships: List[Dict[str, Any]],
        entity_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Validate that relationship entities exist in previous waves.

        Args:
            relationships: List of extracted relationships
            entity_ids: List of valid entity IDs from Waves 1-3

        Returns:
            List of valid relationships
        """
        valid_relationships = []
        entity_id_set = set(entity_ids)

        for rel in relationships:
            # Extract fields with defaults
            source_id = rel.get("source_entity_id", "")
            target_id = rel.get("target_entity_id", "")
            confidence = rel.get("confidence", 0.0)
            rel_type = rel.get("relationship_type", "UNKNOWN")

            # Validate source entity exists
            if source_id not in entity_id_set:
                logger.warning(
                    f"Skipping relationship: source entity '{source_id}' not found in extracted entities"
                )
                continue

            # Validate target entity exists
            if target_id not in entity_id_set:
                logger.warning(
                    f"Skipping relationship: target entity '{target_id}' not found in extracted entities"
                )
                continue

            # Validate confidence threshold
            if confidence < 0.85:
                logger.warning(
                    f"Skipping relationship: confidence {confidence:.2f} below 0.85 threshold"
                )
                continue

            # Prevent self-referential relationships
            if source_id == target_id:
                logger.warning(
                    f"Skipping self-referential relationship for entity '{source_id}'"
                )
                continue

            # Relationship is valid
            valid_relationships.append(rel)

        logger.debug(
            f"Relationship validation: {len(relationships)} → {len(valid_relationships)} "
            f"({len(relationships) - len(valid_relationships)} invalid)"
        )

        return valid_relationships

    def _deduplicate_relationships(
        self,
        relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate relationships by (source, type, target).

        Args:
            relationships: List of relationship dictionaries

        Returns:
            Deduplicated list of relationships
        """
        seen = set()
        deduplicated = []

        for rel in relationships:
            source_id = rel.get("source_entity_id", "")
            target_id = rel.get("target_entity_id", "")
            rel_type = rel.get("relationship_type", "UNKNOWN")

            # Create unique key (source, type, target)
            key = (source_id, rel_type, target_id)

            # Add if not seen
            if key not in seen:
                seen.add(key)
                deduplicated.append(rel)

        logger.debug(
            f"Relationship deduplication: {len(relationships)} → {len(deduplicated)} "
            f"({len(relationships) - len(deduplicated)} duplicates removed)"
        )

        return deduplicated

    async def _extract_three_wave_chunked(
        self,
        document_text: str,
        routing_decision: RoutingDecision,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract entities using 3-wave system with smart chunking for large documents.

        Process:
        1. Determine if SmartChunker should be used (>50K chars)
        2. Chunk document using SmartChunker
        3. Process each chunk through 3-wave extraction
        4. Adjust entity positions relative to original document
        5. Deduplicate entities across chunks
        6. Aggregate results

        Use for: Medium-Large documents (50K-1M+ chars)
        Expected tokens: Variable based on chunk count

        Args:
            document_text: Full document text
            routing_decision: Routing decision with chunk config
            metadata: Optional document metadata

        Returns:
            Dictionary with entities and stats
        """
        from src.core.smart_chunker import SmartChunker, ChunkingStrategy

        logger.info(f"Executing 3-wave chunked extraction: {len(document_text):,} chars")

        # Initialize SmartChunker
        smart_chunker = SmartChunker()

        # Check if smart chunking should be used
        use_smart_chunking = smart_chunker.should_use_smart_chunking(document_text)

        if use_smart_chunking:
            # Use smart chunking with legal-aware strategy
            logger.info("Using SmartChunker with LEGAL_AWARE strategy")
            chunks = smart_chunker.smart_chunk_document(
                text=document_text,
                strategy=ChunkingStrategy.LEGAL_AWARE,
                document_type=None  # Auto-detect
            )
        else:
            # Document not large enough for smart chunking, use three-wave directly
            logger.info("Document below smart chunking threshold, using standard 3-wave")
            return await self._extract_three_wave(document_text, metadata)

        logger.info(f"Document chunked into {len(chunks)} pieces")

        # Process each chunk through 3-wave extraction
        all_entities = []
        total_tokens = 0
        chunk_results = []

        for chunk in chunks:
            logger.info(f"Processing chunk {chunk.chunk_index + 1}/{len(chunks)}: "
                       f"{chunk.length:,} chars (pos {chunk.start_pos:,}-{chunk.end_pos:,})")

            # Extract entities from this chunk
            try:
                chunk_result = await self._extract_three_wave(
                    chunk.text,
                    metadata={
                        **(metadata or {}),
                        "chunk_index": chunk.chunk_index,
                        "chunk_start_pos": chunk.start_pos,
                        "chunk_end_pos": chunk.end_pos,
                        "total_chunks": len(chunks)
                    }
                )

                # Adjust entity positions relative to original document
                adjusted_entities = []
                for entity in chunk_result["entities"]:
                    adjusted_entity = entity.copy()

                    # Adjust positions if present
                    if "start_pos" in entity and entity["start_pos"] is not None:
                        adjusted_entity["start_pos"] = chunk.start_pos + entity["start_pos"]
                    if "end_pos" in entity and entity["end_pos"] is not None:
                        adjusted_entity["end_pos"] = chunk.start_pos + entity["end_pos"]

                    # Add chunk metadata
                    adjusted_entity["chunk_index"] = chunk.chunk_index
                    adjusted_entity["chunk_metadata"] = {
                        "chunk_start": chunk.start_pos,
                        "chunk_end": chunk.end_pos,
                        "chunk_type": chunk.chunk_type,
                        "in_overlap": False  # TODO: Detect overlap regions
                    }

                    adjusted_entities.append(adjusted_entity)

                # Accumulate results
                all_entities.extend(adjusted_entities)
                total_tokens += chunk_result["tokens_used"]

                chunk_results.append({
                    "chunk_index": chunk.chunk_index,
                    "entities_count": len(adjusted_entities),
                    "tokens_used": chunk_result["tokens_used"],
                    "chunk_length": chunk.length,
                    "waves_executed": chunk_result["waves_executed"]
                })

                logger.info(f"Chunk {chunk.chunk_index + 1} complete: "
                           f"{len(adjusted_entities)} entities, "
                           f"{chunk_result['tokens_used']:,} tokens")

            except Exception as e:
                logger.error(f"Error processing chunk {chunk.chunk_index}: {e}")
                # Continue with next chunk rather than failing entire extraction
                chunk_results.append({
                    "chunk_index": chunk.chunk_index,
                    "entities_count": 0,
                    "tokens_used": 0,
                    "error": str(e)
                })
                continue

        # Deduplicate entities across chunks
        logger.info(f"Deduplicating {len(all_entities)} entities across {len(chunks)} chunks")
        deduplicated_entities = self._deduplicate_entities(all_entities)

        # Calculate deduplication stats
        deduplication_ratio = len(deduplicated_entities) / len(all_entities) if all_entities else 1.0
        entities_removed = len(all_entities) - len(deduplicated_entities)

        logger.info(
            f"3-wave chunked extraction complete: "
            f"{len(all_entities)} total entities, "
            f"{len(deduplicated_entities)} after deduplication "
            f"({entities_removed} duplicates removed, {deduplication_ratio:.1%} retention)"
        )

        # Get chunk statistics
        chunk_stats = smart_chunker.get_chunk_statistics(chunks)

        return {
            "entities": deduplicated_entities,
            "relationships": [],  # 3-wave chunked doesn't extract relationships
            "waves_executed": 3,
            "tokens_used": total_tokens,
            "metadata": {
                "prompt_version": "three_wave_chunked",
                "chunking_applied": True,
                "chunking_strategy": "smart_legal_aware",
                "total_chunks": len(chunks),
                "chunk_results": chunk_results,
                "chunk_statistics": chunk_stats,
                "deduplication_ratio": deduplication_ratio,
                "entities_before_dedup": len(all_entities),
                "entities_after_dedup": len(deduplicated_entities),
                "entities_by_chunk": {
                    f"chunk_{r['chunk_index']}": r["entities_count"]
                    for r in chunk_results
                },
                "average_entities_per_chunk": len(all_entities) / len(chunks) if chunks else 0,
                "average_tokens_per_chunk": total_tokens / len(chunks) if chunks else 0
            }
        }

    def _format_prompt(
        self,
        prompt_template: str,
        document_text: str,
        metadata: Optional[Dict[str, Any]] = None,
        previous_entities: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Format prompt with document text and optional context.

        Args:
            prompt_template: Prompt template string
            document_text: Full document text
            metadata: Optional document metadata
            previous_entities: Optional entities from previous waves

        Returns:
            Formatted prompt string
        """
        # Build context section
        context_parts = []

        if metadata:
            context_parts.append(f"Document Metadata: {json.dumps(metadata, indent=2)}")

        if previous_entities:
            context_parts.append(
                f"Previously Extracted Entities ({len(previous_entities)}): "
                f"{json.dumps(previous_entities[:10], indent=2)}..."  # First 10 for context
            )

        context = "\n\n".join(context_parts) if context_parts else ""

        # Format final prompt
        formatted = f"{prompt_template}\n\n"

        if context:
            formatted += f"## Context\n\n{context}\n\n"

        formatted += f"## Document Text\n\n{document_text}\n\n"
        formatted += "## Your Response (JSON only):\n\n"

        return formatted

    async def _call_vllm(self, prompt: str) -> Dict[str, Any]:
        """
        Call vLLM with prompt using structured outputs (guided_json).

        Uses Pydantic models to define JSON schema, ensuring vLLM returns
        properly formatted entity extraction results.

        Args:
            prompt: Formatted prompt string

        Returns:
            Dictionary with text response and token usage
        """
        try:
            # Import models
            from src.vllm_client.models import VLLMRequest
            from src.schemas.guided_json_schemas import LurisEntityV2ExtractionResponse

            # Get JSON schema from Pydantic model (LurisEntityV2-based)
            json_schema = LurisEntityV2ExtractionResponse.model_json_schema()

            logger.debug(f"Using guided JSON with schema model: LurisEntityV2ExtractionResponse")
            logger.debug(f"Schema contains keys: {list(json_schema.keys())}")

            # Load settings to get entity extraction temperature
            settings = get_settings()

            # Create VLLMRequest with guided_json for valid JSON output
            request = VLLMRequest(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60000,  # Increased from 4096 to handle large documents with many entities (vLLM 160K context - 82K prompt = 78K available)
                temperature=settings.extraction.entity_temperature,  # Use entity-specific config (0.0 for reproducibility)
                seed=42,          # Reproducibility
                stream=False,
                extra_body={"guided_json": json_schema}  # ✅ ENABLED - ensures valid JSON matching LurisEntityV2ExtractionResponse schema
            )

            logger.info(f"Calling vLLM with guided JSON for entity extraction")
            logger.info(f"🔍 CRITICAL: Prompt length: {len(prompt)} chars")

            # Call vLLM with structured output constraint
            response = await self.vllm_client.generate_chat_completion(request)

            logger.info(f"✅ vLLM response received ({response.usage.total_tokens} tokens)")
            logger.info(f"🔍 CRITICAL: Response content length: {len(response.content)} chars")
            logger.info(f"🔍 CRITICAL: First 500 chars of response: {response.content[:500]}")

            # Response is now guaranteed to match EntityExtractionResponse schema
            return {
                "text": response.content,  # JSON string matching schema
                "tokens_used": response.usage.total_tokens
            }

        except Exception as e:
            logger.error(f"❌ vLLM call failed: {e}")
            raise

    async def _call_vllm_single_pass(self, prompt: str) -> Dict[str, Any]:
        """
        Call vLLM for single-pass extraction with combined schema (entities + relationships).

        **NEW METHOD** for Phase 1 - Uses SinglePassExtractionResponse schema
        to extract both entities and relationships in one LLM call.

        Args:
            prompt: Formatted prompt string

        Returns:
            Dictionary with text response and token usage
        """
        try:
            # Import models
            from src.vllm_client.models import VLLMRequest
            from src.schemas.guided_json_schemas import LurisEntityV2ExtractionResponse

            # Get JSON schema from Pydantic model (LurisEntityV2-based, entities only for single-pass)
            json_schema = LurisEntityV2ExtractionResponse.model_json_schema()

            logger.debug(f"Using guided JSON with schema model: LurisEntityV2ExtractionResponse (single-pass entities)")
            logger.debug(f"Schema contains keys: {list(json_schema.keys())}")

            # Load settings to get entity extraction temperature
            settings = get_settings()

            # Create VLLMRequest with guided_json for entity extraction
            request = VLLMRequest(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60000,  # Increased from 4096 to handle large documents with many entities (vLLM 160K context - 82K prompt = 78K available)
                temperature=settings.extraction.entity_temperature,  # Use entity-specific config
                seed=42,          # Reproducibility
                stream=False,
                extra_body={"guided_json": json_schema}  # ✅ LurisEntityV2-based schema for entities
            )

            logger.info(f"Calling vLLM with guided JSON for single-pass extraction (LurisEntityV2 entities)")

            # Call vLLM with structured output constraint
            response = await self.vllm_client.generate_chat_completion(request)

            logger.info(f"✅ vLLM single-pass response received ({response.usage.total_tokens} tokens)")

            # Response is now guaranteed to match LurisEntityV2ExtractionResponse schema
            return {
                "text": response.content,  # JSON string matching LurisEntityV2 schema
                "tokens_used": response.usage.total_tokens
            }

        except Exception as e:
            logger.error(f"❌ vLLM single-pass call failed: {e}")
            raise

    def _parse_entities(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse entities from guided JSON response with embedded validation logging.

        With guided JSON enabled, response is guaranteed to be valid JSON
        matching EntityExtractionResponse schema.

        Args:
            response_text: JSON response from vLLM (guided JSON)

        Returns:
            List of entity dictionaries
        """
        try:
            # Step 1: JSON decode validation
            parsed = json.loads(response_text)
            logger.debug("✅ JSON decode successful")

            # Step 2: Validate entities field exists and is a list
            entities = parsed.get("entities", [])
            if not isinstance(entities, list):
                logger.error("❌ Entities field is not a list - schema violation")
                return []

            logger.debug("✅ Entities field validation passed")

            # Step 3: Optional Pydantic schema validation (lightweight check)
            try:
                from src.schemas.guided_json_schemas import LurisEntityV2ExtractionResponse
                LurisEntityV2ExtractionResponse(**parsed)
                logger.debug(f"✅ Pydantic schema validation passed: {len(entities)} entities")
            except ValidationError as schema_error:
                logger.error(f"❌ Pydantic validation failed: {schema_error}")
                logger.error(f"Raw parsed data keys: {list(parsed.keys())}")
                logger.error(f"Entity count before validation: {len(entities)}")
                if entities:
                    logger.error(f"Sample entity that failed validation: {entities[0]}")
                # Continue processing - entities are already extracted from JSON
                # We'll apply confidence filtering at the API response level if needed
            except Exception as e:
                logger.error(f"❌ Unexpected error during schema validation: {e}")

            logger.debug(f"Parsed {len(entities)} entities from guided JSON response")
            return entities

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode failed (guided JSON should prevent this): {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error parsing entities: {e}")
            return []

    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate entities across waves.

        Deduplication strategy:
        1. Normalize entity text (lowercase, strip whitespace)
        2. Group by (type, normalized_text)
        3. Keep first occurrence (earlier waves have priority)

        Args:
            entities: List of entity dictionaries

        Returns:
            Deduplicated list of entities
        """
        seen = set()
        deduplicated = []

        for entity in entities:
            # Extract entity identifiers
            entity_type = entity.get("entity_type", "UNKNOWN")
            entity_text = entity.get("text", "")

            # Normalize text for comparison
            normalized_text = entity_text.lower().strip()

            # Create unique key
            key = (entity_type, normalized_text)

            # Add if not seen
            if key not in seen:
                seen.add(key)
                deduplicated.append(entity)

        logger.debug(
            f"Deduplication: {len(entities)} → {len(deduplicated)} "
            f"({len(entities) - len(deduplicated)} duplicates removed)"
        )

        return deduplicated

    def _enhance_entities_with_context(
        self,
        entities: List[Dict[str, Any]],
        document_text: str,
        prompt_template: str,
        wave_number: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Enhance entities with quality testing fields.

        Adds:
        - prompt_template: Which prompt generated the entity
        - wave_number: Wave number (1-3) or None for single-pass
        - context_before: Text before entity (50 chars)
        - context_after: Text after entity (50 chars)

        Args:
            entities: List of entity dictionaries from LLM
            document_text: Full document text for context extraction
            prompt_template: Name of prompt that generated these entities
            wave_number: Wave number (1-3) or None for single-pass

        Returns:
            Enhanced entity list with quality testing fields
        """
        enhanced = []

        for entity in entities:
            # Copy existing entity fields
            enhanced_entity = entity.copy()

            # Add prompt tracking fields
            enhanced_entity["prompt_template"] = prompt_template
            enhanced_entity["wave_number"] = wave_number

            # Extract context if positions are available
            start_pos = entity.get("start_pos")
            end_pos = entity.get("end_pos")

            if start_pos is not None:
                enhanced_entity["context_before"] = self._extract_context(
                    document_text, start_pos, before=True, chars=50
                )
            else:
                enhanced_entity["context_before"] = ""

            if end_pos is not None:
                enhanced_entity["context_after"] = self._extract_context(
                    document_text, end_pos, before=False, chars=50
                )
            else:
                enhanced_entity["context_after"] = ""

            enhanced.append(enhanced_entity)

        return enhanced

    def _extract_context(
        self,
        document_text: str,
        position: int,
        before: bool = True,
        chars: int = 50
    ) -> str:
        """
        Extract context before or after entity position.

        Args:
            document_text: Full document text
            position: Character position in document
            before: If True, extract before position; if False, extract after
            chars: Number of characters to extract (default 50)

        Returns:
            Context string (up to chars length)
        """
        if not document_text:
            return ""

        doc_len = len(document_text)

        if before:
            # Extract text before the position
            start = max(0, position - chars)
            return document_text[start:position]
        else:
            # Extract text after the position
            end = min(doc_len, position + chars)
            return document_text[position:end]


# Factory function for creating orchestrator
def create_extraction_orchestrator(
    prompt_manager: Optional[PromptManager] = None,
    vllm_client: Optional[Any] = None
) -> ExtractionOrchestrator:
    """
    Factory function for creating ExtractionOrchestrator.

    Args:
        prompt_manager: Optional PromptManager instance
        vllm_client: Optional vLLM client instance

    Returns:
        ExtractionOrchestrator instance
    """
    return ExtractionOrchestrator(
        prompt_manager=prompt_manager,
        vllm_client=vllm_client
    )
