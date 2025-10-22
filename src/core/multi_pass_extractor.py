"""
Multi-Pass Entity Extraction Orchestrator

This module provides a sophisticated multi-pass extraction system that runs
7 specialized extraction passes in parallel, each focusing on different entity types.
It leverages the vLLM service for AI-enhanced extraction with optimized parallelism.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# CLAUDE.md Compliant: Absolute imports only
from src.core.config import get_settings
from src.core.entity_registry import EntityRegistry

# Import config to get max_tokens settings
try:
    _settings = get_settings()
    DEFAULT_PASS_MAX_TOKENS = min(_settings.ai.llm_max_response_tokens, 3000)  # Conservative for passes
except Exception:
    DEFAULT_PASS_MAX_TOKENS = 1000  # Fallback for config access issues

# EntityMatch is defined in the routes module, so we'll define it here too
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class EntityMatch(BaseModel):
    """Individual entity match result."""
    entity_type: str = Field(..., description="Type of legal entity or citation")
    text: str = Field(..., description="Extracted entity text")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    start_position: int = Field(..., description="Character start position in document")
    end_position: int = Field(..., description="Character end position in document")
    context: Optional[str] = Field(default=None, description="Surrounding context")
    extraction_method: str = Field(..., description="Method used: 'regex', 'ai', or 'hybrid'")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

logger = logging.getLogger(__name__)


class ExtractionPass(Enum):
    """Enumeration of the 8 extraction passes."""
    CITATIONS = 1  # Case citations and references
    STATUTES = 2   # Statutory citations and codes
    REGULATIONS = 3  # Regulatory citations
    ENTITIES = 4   # Named entities (persons, orgs)
    COURTS = 5     # Courts and judges
    TEMPORAL = 6   # Dates, times, deadlines
    CATCHALL = 7   # Catch-all for missed entities
    RELATIONSHIPS = 8  # Extract entity relationships


@dataclass
class PassConfiguration:
    """Configuration for a single extraction pass."""
    pass_type: ExtractionPass
    prompt_file: str
    entity_types: List[str]
    max_tokens: int = field(default_factory=lambda: DEFAULT_PASS_MAX_TOKENS)  # Uses config value
    temperature: float = 0.0
    timeout: float = 1200.0  # 20 minutes - increased for full document processing
    retry_count: int = 2
    priority: int = 1  # Lower is higher priority
    enabled: bool = True


@dataclass
class PassResult:
    """Results from a single extraction pass."""
    pass_type: ExtractionPass
    entities: List[EntityMatch]
    processing_time_ms: float
    token_usage: Dict[str, int]
    success: bool
    error_message: Optional[str] = None
    retry_count: int = 0


@dataclass
class MultiPassMetrics:
    """Metrics for multi-pass extraction."""
    total_passes_executed: int = 0
    successful_passes: int = 0
    failed_passes: int = 0
    total_entities_extracted: int = 0
    unique_entities: int = 0
    duplicates_removed: int = 0
    total_processing_time_ms: float = 0.0
    parallel_execution_time_ms: float = 0.0
    total_tokens_used: int = 0
    pass_metrics: Dict[ExtractionPass, Dict[str, Any]] = field(default_factory=dict)


class MultiPassExtractor:
    """
    Orchestrates multi-pass entity extraction with parallel processing.

    This extractor runs 8 specialized passes, with 7 entity extraction
    passes running in parallel followed by a relationship extraction pass.
    It manages parallelism, deduplication, error handling, and result aggregation.
    """
    
    # Default pass configurations
    DEFAULT_PASSES = {
        ExtractionPass.CITATIONS: PassConfiguration(
            pass_type=ExtractionPass.CITATIONS,
            prompt_file="pass1_comprehensive_discovery.md",  # Use new consolidated template
            entity_types=["case_citation", "case_reference", "docket_number"],
            # max_tokens uses default from PassConfiguration
            temperature=0.15,  # Slightly higher for better extraction
            priority=1
        ),
        ExtractionPass.STATUTES: PassConfiguration(
            pass_type=ExtractionPass.STATUTES,
            prompt_file="pass2to6_validation_enhancement.md",  # Pass 2 validation
            entity_types=["statute", "code_section", "legislative_act"],
            # max_tokens uses default from PassConfiguration
            temperature=0.15,  # Slightly higher for better extraction
            priority=2
        ),
        ExtractionPass.REGULATIONS: PassConfiguration(
            pass_type=ExtractionPass.REGULATIONS,
            prompt_file="pass2to6_validation_enhancement.md",  # Pass 3 enhancement
            entity_types=["regulation", "administrative_code", "executive_order"],
            # max_tokens uses default from PassConfiguration
            temperature=0.15,  # Slightly higher for better extraction
            priority=3
        ),
        ExtractionPass.ENTITIES: PassConfiguration(
            pass_type=ExtractionPass.ENTITIES,
            prompt_file="pass2to6_validation_enhancement.md",  # Pass 4 contextual
            entity_types=["person", "organization", "government_entity", "law_firm"],
            # max_tokens uses default from PassConfiguration
            temperature=0.15,  # Slightly higher for better extraction
            priority=1
        ),
        ExtractionPass.COURTS: PassConfiguration(
            pass_type=ExtractionPass.COURTS,
            prompt_file="pass2to6_validation_enhancement.md",  # Pass 5 specialized
            entity_types=["court", "judge", "justice", "magistrate"],
            # max_tokens uses default from PassConfiguration
            temperature=0.15,  # Slightly higher for better extraction
            priority=2
        ),
        ExtractionPass.TEMPORAL: PassConfiguration(
            pass_type=ExtractionPass.TEMPORAL,
            prompt_file="pass2to6_validation_enhancement.md",  # Pass 6 final validation
            entity_types=["date", "deadline", "time_period", "filing_date"],
            # max_tokens uses default from PassConfiguration
            temperature=0.15,  # Slightly higher for better extraction
            priority=3
        ),
        ExtractionPass.CATCHALL: PassConfiguration(
            pass_type=ExtractionPass.CATCHALL,
            prompt_file="pass7_final_sweep.md",  # Pass 7 comprehensive sweep
            entity_types=["legal_concept", "doctrine", "standard", "procedure", "other"],
            max_tokens=2000,  # Final pass gets more tokens for comprehensive sweep
            temperature=0.25,  # Higher for discovery
            priority=4
        ),
        ExtractionPass.RELATIONSHIPS: PassConfiguration(
            pass_type=ExtractionPass.RELATIONSHIPS,
            prompt_file="relationship_extraction.md",  # Pass 8 relationship extraction
            entity_types=["relationship"],  # Special marker for relationship extraction
            max_tokens=2000,  # Relationships need more context for evidence
            temperature=0.20,  # Higher for relationship discovery
            priority=5,  # Run AFTER entity extraction passes
            enabled=True
        )
    }
    
    def __init__(
        self,
        vllm_client,
        prompts_dir: str = "/srv/luris/be/entity-extraction-service/src/prompts",
        max_parallel_workers: int = 4,
        use_entity_registry: bool = True,
        registry: Optional[EntityRegistry] = None
    ):
        """
        Initialize the multi-pass extractor.
        
        Args:
            vllm_client: Client for vLLM service
            prompts_dir: Directory containing prompt templates
            max_parallel_workers: Maximum parallel extraction passes
            use_entity_registry: Whether to use entity registry for deduplication
            registry: Optional pre-initialized EntityRegistry
        """
        self.vllm_client = vllm_client
        self.prompts_dir = Path(prompts_dir)
        self.max_parallel_workers = max_parallel_workers
        self.use_entity_registry = use_entity_registry
        self.registry = registry  # Registry will be created per document when needed
        self.semaphore = asyncio.Semaphore(max_parallel_workers)
        self.pass_configs = self.DEFAULT_PASSES.copy()
        self.metrics = MultiPassMetrics()
        
        # Load prompt templates
        self.prompt_templates: Dict[ExtractionPass, str] = {}
        self._load_prompt_templates()
    
    def _load_prompt_templates(self):
        """Load all prompt templates from disk."""
        for pass_type, config in self.pass_configs.items():
            try:
                prompt_path = self.prompts_dir / config.prompt_file
                if prompt_path.exists():
                    with open(prompt_path, 'r') as f:
                        self.prompt_templates[pass_type] = f.read()
                    logger.info(f"Loaded prompt template for {pass_type.name}")
                else:
                    logger.warning(f"Prompt file not found: {prompt_path}")
                    # Use a default template
                    self.prompt_templates[pass_type] = self._get_default_prompt()
            except Exception as e:
                logger.error(f"Failed to load prompt for {pass_type.name}: {e}")
                self.prompt_templates[pass_type] = self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Get a default prompt template."""
        return """Extract all {{entity_types}} from the following text.
Return as JSON with format: {"entities": [{"type": "...", "text": "...", "confidence": 0.9, "start": 0, "end": 10}]}

Text: {{chunk_content}}"""
    
    async def extract_multi_pass(
        self,
        chunk_id: str,
        chunk_content: str,
        document_id: str,
        chunk_index: int,
        whole_document: Optional[str] = None,
        selected_passes: Optional[List[int]] = None,
        parallel_execution: bool = True,
        custom_configs: Optional[Dict[ExtractionPass, PassConfiguration]] = None
    ) -> Tuple[List[EntityMatch], MultiPassMetrics]:
        """
        Execute multi-pass extraction on a chunk.
        
        Args:
            chunk_id: Unique chunk identifier
            chunk_content: Content to extract entities from
            document_id: Document this chunk belongs to
            chunk_index: Index of chunk in document
            whole_document: Optional full document for context
            selected_passes: Optional list of pass numbers to execute (1-8)
            parallel_execution: Whether to run passes in parallel
            custom_configs: Optional custom pass configurations
            
        Returns:
            Tuple of (extracted entities, metrics)
        """
        start_time = time.time()
        
        # Determine which passes to execute
        passes_to_execute = self._determine_passes(selected_passes, custom_configs)
        
        # Reset metrics
        self.metrics = MultiPassMetrics()
        
        # Execute passes
        if parallel_execution:
            results = await self._execute_parallel(
                chunk_id, chunk_content, document_id, chunk_index,
                whole_document, passes_to_execute
            )
        else:
            results = await self._execute_sequential(
                chunk_id, chunk_content, document_id, chunk_index,
                whole_document, passes_to_execute
            )
        
        # Log intermediate results
        logger.info(f"Multi-pass extraction completed {len(results)} passes in {(time.time() - start_time) * 1000:.1f}ms")
        successful_passes = [r for r in results if r.success]
        failed_passes = [r for r in results if not r.success]
        logger.info(f"Successful passes: {len(successful_passes)}, Failed passes: {len(failed_passes)}")
        
        if failed_passes:
            for failed_pass in failed_passes:
                logger.warning(f"Failed pass: {failed_pass.pass_type.name} - {failed_pass.error_message}")
        
        # Aggregate and deduplicate results
        all_entities = await self._aggregate_results(results, chunk_id, document_id)
        
        # Update metrics
        self.metrics.parallel_execution_time_ms = (time.time() - start_time) * 1000
        self.metrics.unique_entities = len(all_entities)
        
        logger.info(f"Final result: {len(all_entities)} unique entities extracted in {self.metrics.parallel_execution_time_ms:.1f}ms")
        
        return all_entities, self.metrics
    
    def _determine_passes(
        self,
        selected_passes: Optional[List[int]],
        custom_configs: Optional[Dict[ExtractionPass, PassConfiguration]]
    ) -> List[PassConfiguration]:
        """Determine which passes to execute based on configuration."""
        passes = []
        
        # Apply custom configurations if provided
        if custom_configs:
            self.pass_configs.update(custom_configs)
        
        # Filter passes based on selection
        for pass_type, config in self.pass_configs.items():
            if not config.enabled:
                continue
            
            if selected_passes is None or pass_type.value in selected_passes:
                passes.append(config)
        
        # Sort by priority
        passes.sort(key=lambda x: x.priority)
        
        return passes
    
    async def _execute_parallel(
        self,
        chunk_id: str,
        chunk_content: str,
        document_id: str,
        chunk_index: int,
        whole_document: Optional[str],
        passes: List[PassConfiguration]
    ) -> List[PassResult]:
        """Execute passes in parallel with controlled concurrency."""

        # Separate RELATIONSHIPS pass (Pass 8) from other passes
        relationship_pass = None
        other_passes = []

        for config in passes:
            if config.pass_type == ExtractionPass.RELATIONSHIPS:
                relationship_pass = config
            else:
                other_passes.append(config)

        # Execute all non-relationship passes in parallel first
        tasks = []
        for config in other_passes:
            task = asyncio.create_task(
                self._execute_single_pass_with_semaphore(
                    config, chunk_id, chunk_content, document_id,
                    chunk_index, whole_document
                )
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Pass {other_passes[i].pass_type.name} failed: {result}")
                processed_results.append(
                    PassResult(
                        pass_type=other_passes[i].pass_type,
                        entities=[],
                        processing_time_ms=0,
                        token_usage={},
                        success=False,
                        error_message=str(result)
                    )
                )
            else:
                processed_results.append(result)

        # If relationship pass is enabled, execute it AFTER other passes
        if relationship_pass:
            # Collect all entities from previous passes
            all_entities = []
            for result in processed_results:
                if result.success:
                    all_entities.extend(result.entities)

            logger.info(f"Executing RELATIONSHIPS pass with {len(all_entities)} entities from previous passes")

            # Execute relationship pass with accumulated entities
            try:
                relationship_result = await self._execute_single_pass_with_semaphore(
                    relationship_pass, chunk_id, chunk_content, document_id,
                    chunk_index, whole_document, all_entities
                )
                processed_results.append(relationship_result)
            except Exception as e:
                logger.error(f"RELATIONSHIPS pass failed: {e}")
                processed_results.append(
                    PassResult(
                        pass_type=relationship_pass.pass_type,
                        entities=[],
                        processing_time_ms=0,
                        token_usage={},
                        success=False,
                        error_message=str(e)
                    )
                )

        return processed_results
    
    async def _execute_sequential(
        self,
        chunk_id: str,
        chunk_content: str,
        document_id: str,
        chunk_index: int,
        whole_document: Optional[str],
        passes: List[PassConfiguration]
    ) -> List[PassResult]:
        """Execute passes sequentially."""
        results = []
        all_entities = []

        for config in passes:
            # For RELATIONSHIPS pass, provide accumulated entities
            if config.pass_type == ExtractionPass.RELATIONSHIPS:
                logger.info(f"Executing RELATIONSHIPS pass with {len(all_entities)} entities from previous passes")
                result = await self._execute_single_pass(
                    config, chunk_id, chunk_content, document_id,
                    chunk_index, whole_document, all_entities
                )
            else:
                result = await self._execute_single_pass(
                    config, chunk_id, chunk_content, document_id,
                    chunk_index, whole_document
                )

            results.append(result)

            # Accumulate entities for future passes (especially RELATIONSHIPS)
            if result.success:
                all_entities.extend(result.entities)

        return results
    
    async def _execute_single_pass_with_semaphore(
        self,
        config: PassConfiguration,
        chunk_id: str,
        chunk_content: str,
        document_id: str,
        chunk_index: int,
        whole_document: Optional[str],
        extracted_entities: Optional[List[EntityMatch]] = None
    ) -> PassResult:
        """Execute a single pass with semaphore control."""
        async with self.semaphore:
            return await self._execute_single_pass(
                config, chunk_id, chunk_content, document_id,
                chunk_index, whole_document, extracted_entities
            )
    
    async def _execute_single_pass(
        self,
        config: PassConfiguration,
        chunk_id: str,
        chunk_content: str,
        document_id: str,
        chunk_index: int,
        whole_document: Optional[str],
        extracted_entities: Optional[List[EntityMatch]] = None
    ) -> PassResult:
        """Execute a single extraction pass with retry logic."""
        start_time = time.time()
        retry_count = 0
        last_error = None

        for attempt in range(config.retry_count + 1):
            try:
                # Build prompt
                prompt = self._build_prompt(
                    config, chunk_content, chunk_index, whole_document, extracted_entities
                )
                
                # Call vLLM service
                response = await asyncio.wait_for(
                    self._call_vllm(prompt, config),
                    timeout=config.timeout
                )
                
                # Parse response
                entities = self._parse_vllm_response(
                    response, config, chunk_id, document_id, chunk_index
                )
                
                # Calculate metrics
                processing_time = (time.time() - start_time) * 1000
                token_usage = response.get("usage", {})
                
                # Update metrics
                self.metrics.total_passes_executed += 1
                self.metrics.successful_passes += 1
                self.metrics.total_entities_extracted += len(entities)
                self.metrics.total_tokens_used += token_usage.get("total_tokens", 0)
                
                return PassResult(
                    pass_type=config.pass_type,
                    entities=entities,
                    processing_time_ms=processing_time,
                    token_usage=token_usage,
                    success=True,
                    retry_count=retry_count
                )
                
            except asyncio.TimeoutError:
                last_error = f"Timeout after {config.timeout}s"
                retry_count += 1
                logger.warning(f"Pass {config.pass_type.name} timed out (attempt {attempt + 1})")
                
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                logger.warning(f"Pass {config.pass_type.name} failed (attempt {attempt + 1}): {e}")
            
            # Wait before retry
            if attempt < config.retry_count:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # All attempts failed
        self.metrics.total_passes_executed += 1
        self.metrics.failed_passes += 1
        
        return PassResult(
            pass_type=config.pass_type,
            entities=[],
            processing_time_ms=(time.time() - start_time) * 1000,
            token_usage={},
            success=False,
            error_message=last_error,
            retry_count=retry_count
        )
    
    def _build_prompt(
        self,
        config: PassConfiguration,
        chunk_content: str,
        chunk_index: int,
        whole_document: Optional[str],
        extracted_entities: Optional[List[EntityMatch]] = None
    ) -> str:
        """Build the extraction prompt for a pass."""
        template = self.prompt_templates.get(config.pass_type, self._get_default_prompt())

        # Prepare entity types string
        entity_types = ", ".join(config.entity_types)

        # Truncate whole document if provided
        doc_context = ""
        if whole_document:
            # Take relevant context around the chunk
            doc_context = whole_document[:2000] + "..." if len(whole_document) > 2000 else whole_document

        # For relationship extraction (Pass 8), include entities from previous passes
        entities_json = ""
        if config.pass_type == ExtractionPass.RELATIONSHIPS and extracted_entities:
            entities_json = json.dumps([{
                "text": e.text,
                "entity_type": e.entity_type,
                "start": e.start_position,
                "end": e.end_position
            } for e in extracted_entities], indent=2)

        # Replace template variables
        prompt = template.replace("{{chunk_content}}", chunk_content)
        prompt = prompt.replace("{{entity_types}}", entity_types)
        prompt = prompt.replace("{{chunk_index}}", str(chunk_index))
        prompt = prompt.replace("{{whole_document}}", doc_context)
        prompt = prompt.replace("{{extraction_pass}}", config.pass_type.name)
        prompt = prompt.replace("{{entities_json}}", entities_json)

        return prompt
    
    async def _call_vllm(self, prompt: str, config: PassConfiguration) -> Dict:
        """Call the vLLM service for extraction."""
        from ..client.vllm_http_client import VLLMRequest
        
        request = VLLMRequest(
            messages=[
                {
                    "role": "system",
                    "content": "You are a legal entity extraction specialist. Extract entities accurately and return them in the specified JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            response_format="json"
        )
        
        logger.info(f"[{config.pass_type.name}] Sending request to vLLM: max_tokens={config.max_tokens}, temperature={config.temperature}")
        
        response = await self.vllm_client.generate_chat_completion(request)
        
        # Log raw response for debugging
        logger.info(f"[{config.pass_type.name}] Raw vLLM response type: {type(response)}")
        logger.debug(f"[{config.pass_type.name}] Raw vLLM response: {response}")
        
        # Extract content from VLLMResponse object
        if hasattr(response, 'content'):
            content = response.content
            logger.info(f"[{config.pass_type.name}] Response content type: {type(content)}, length: {len(content) if isinstance(content, str) else 'N/A'}")
            logger.debug(f"[{config.pass_type.name}] Response content: {content[:500] if isinstance(content, str) else content}...")
        else:
            logger.error(f"[{config.pass_type.name}] Response has no 'content' attribute: {dir(response)}")
            return {"entities": []}
        
        # Parse JSON response with comprehensive error handling
        try:
            if isinstance(content, str):
                # Try to parse the string as JSON
                parsed_json = json.loads(content)
                logger.info(f"[{config.pass_type.name}] Successfully parsed JSON response: {type(parsed_json)}")
                
                # Validate that it has the expected structure
                if isinstance(parsed_json, dict):
                    # Check if entities are directly accessible
                    entities = parsed_json.get("entities", [])
                    
                    # Check if entities are wrapped in extracted_text field (common with vLLM JSON repair)
                    if not entities and "extracted_text" in parsed_json:
                        try:
                            # extracted_text contains another JSON string
                            nested_json_str = parsed_json["extracted_text"]
                            if isinstance(nested_json_str, str):
                                logger.debug(f"[{config.pass_type.name}] Parsing nested JSON: {nested_json_str[:200]}...")
                                nested_json = json.loads(nested_json_str)
                                if isinstance(nested_json, dict):
                                    entities = nested_json.get("entities", [])
                                    logger.info(f"[{config.pass_type.name}] Found entities in nested extracted_text JSON")
                                    # Return the nested JSON structure directly
                                    parsed_json = nested_json
                        except json.JSONDecodeError as e:
                            logger.warning(f"[{config.pass_type.name}] Failed to parse nested extracted_text JSON: {e}")
                            logger.info(f"[{config.pass_type.name}] Attempting JSON repair on nested content")
                            
                            # Try to repair the malformed JSON with specific fixes
                            try:
                                logger.info(f"[{config.pass_type.name}] Attempting custom JSON repair on nested content")
                                logger.debug(f"[{config.pass_type.name}] Original malformed JSON: {nested_json_str[:500]}...")
                                
                                repaired_json_str = self._repair_json_content(nested_json_str)
                                
                                if repaired_json_str != nested_json_str:
                                    logger.info(f"[{config.pass_type.name}] Custom JSON repair applied, trying again")
                                    logger.debug(f"[{config.pass_type.name}] Repaired JSON: {repaired_json_str[:500]}...")
                                    nested_json = json.loads(repaired_json_str)
                                    if isinstance(nested_json, dict):
                                        entities = nested_json.get("entities", [])
                                        logger.info(f"[{config.pass_type.name}] Successfully parsed repaired JSON with {len(entities)} entities")
                                        if entities:
                                            logger.debug(f"[{config.pass_type.name}] Sample repaired entity: {entities[0]}")
                                        parsed_json = nested_json
                                else:
                                    logger.info(f"[{config.pass_type.name}] No JSON repair needed - content may have different issue")
                            except Exception as repair_error:
                                logger.warning(f"[{config.pass_type.name}] Custom JSON repair also failed: {repair_error}")
                                logger.debug(f"[{config.pass_type.name}] Original content that failed: {nested_json_str[:200]}...")
                    
                    logger.info(f"[{config.pass_type.name}] Found {len(entities)} entities in response")
                    if entities:
                        logger.debug(f"[{config.pass_type.name}] Sample entity: {entities[0] if entities else 'None'}")
                    return parsed_json
                else:
                    logger.warning(f"[{config.pass_type.name}] Parsed JSON is not a dict: {type(parsed_json)}")
                    return {"entities": []}
            elif isinstance(content, dict):
                # Content is already a dictionary
                logger.info(f"[{config.pass_type.name}] Response content is already a dict")
                entities = content.get("entities", [])
                logger.info(f"[{config.pass_type.name}] Found {len(entities)} entities in dict response")
                return content
            else:
                logger.error(f"[{config.pass_type.name}] Unexpected content type: {type(content)}")
                return {"entities": []}
                
        except json.JSONDecodeError as e:
            logger.error(f"[{config.pass_type.name}] JSON decode error: {e}")
            logger.error(f"[{config.pass_type.name}] Failed content: {content[:200] if isinstance(content, str) else content}...")
            
            # Try to extract JSON from content with fallback strategies
            if isinstance(content, str):
                fallback_result = self._extract_json_fallback(content, config.pass_type.name)
                return fallback_result
            
            return {"entities": []}
        except Exception as e:
            logger.error(f"[{config.pass_type.name}] Unexpected error parsing response: {e}")
            logger.error(f"[{config.pass_type.name}] Content causing error: {content[:200] if isinstance(content, str) else content}...")
            return {"entities": []}
    
    def _parse_vllm_response(
        self,
        response: Dict,
        config: PassConfiguration,
        chunk_id: str,
        document_id: str,
        chunk_index: int
    ) -> List[EntityMatch]:
        """Parse vLLM response into EntityMatch objects."""
        entities = []
        
        logger.info(f"[{config.pass_type.name}] Parsing response for EntityMatch objects")
        logger.debug(f"[{config.pass_type.name}] Response structure: {response}")
        
        entities_data = response.get("entities", [])
        logger.info(f"[{config.pass_type.name}] Found {len(entities_data)} entities to parse")
        
        if not entities_data:
            logger.warning(f"[{config.pass_type.name}] No entities found in response")
            return entities
        
        for i, entity_data in enumerate(entities_data):
            try:
                logger.debug(f"[{config.pass_type.name}] Parsing entity {i+1}: {entity_data}")

                # Handle both format variations (text/name and type/entity_type)
                entity_text = entity_data.get("text") or entity_data.get("name") or entity_data.get("entity_text")
                entity_type = entity_data.get("entity_type") or entity_data.get("type") or "unknown"

                # Validate required fields
                if not entity_text:
                    logger.warning(f"[{config.pass_type.name}] Entity {i+1} missing text/name field, skipping")
                    continue

                # Map common type variations to standard entity types
                type_mapping = {
                    "Legal Case": "CASE_CITATION",
                    "Case Citation": "CASE_CITATION",
                    "Person": "JUDGE",
                    "Year": "DATE",
                    "Date": "DATE",
                    "Court": "COURT",
                    "Attorney": "ATTORNEY",
                    "Party": "PARTY"
                }

                # Normalize entity type
                if entity_type in type_mapping:
                    entity_type = type_mapping[entity_type]
                elif not entity_type.isupper():
                    # Convert to uppercase if not already
                    entity_type = entity_type.upper().replace(" ", "_")

                entity = EntityMatch(
                    entity_type=entity_type,
                    text=entity_text,
                    confidence=float(entity_data.get("confidence", 0.8)),
                    start_position=int(entity_data.get("start", 0) or entity_data.get("start_position", 0)),
                    end_position=int(entity_data.get("end", 0) or entity_data.get("end_position", 0)),
                    context=entity_data.get("context"),
                    extraction_method=f"ai_multipass_{config.pass_type.name.lower()}",
                    metadata={
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "chunk_index": str(chunk_index),
                        "extraction_pass": str(config.pass_type.value),
                        "pass_name": config.pass_type.name
                    }
                )
                entities.append(entity)
                logger.debug(f"[{config.pass_type.name}] Successfully parsed entity {i+1}: {entity.entity_type} - {entity.text[:50]}...")
                
            except Exception as e:
                logger.warning(f"[{config.pass_type.name}] Failed to parse entity {i+1}: {e}")
                logger.debug(f"[{config.pass_type.name}] Problematic entity data: {entity_data}")
                continue
        
        logger.info(f"[{config.pass_type.name}] Successfully parsed {len(entities)} entities")
        return entities
    
    async def _aggregate_results(
        self,
        results: List[PassResult],
        chunk_id: str,
        document_id: str
    ) -> List[EntityMatch]:
        """Aggregate and deduplicate results from all passes."""
        all_entities = []
        entity_map: Dict[str, EntityMatch] = {}
        
        for result in results:
            if not result.success:
                continue
            
            # Update pass-specific metrics
            self.metrics.pass_metrics[result.pass_type] = {
                "entities_found": len(result.entities),
                "processing_time_ms": result.processing_time_ms,
                "token_usage": result.token_usage,
                "retry_count": result.retry_count
            }
            
            for entity in result.entities:
                # Create unique key for deduplication
                entity_key = f"{entity.entity_type}:{entity.text}:{entity.start_position}"
                
                if entity_key in entity_map:
                    # Merge confidence scores (take maximum)
                    existing = entity_map[entity_key]
                    if entity.confidence > existing.confidence:
                        entity_map[entity_key] = entity
                    self.metrics.duplicates_removed += 1
                else:
                    entity_map[entity_key] = entity
        
        # Use entity registry if enabled
        if self.use_entity_registry:
            # Create document-specific registry if not provided
            if not self.registry:
                # Create a registry for this specific document
                # We'll use basic defaults since we don't have full document info in this context
                try:
                    self.registry = EntityRegistry(
                        document_id=document_id,
                        document_name=f"Document_{document_id[:8]}" if document_id else "Unknown",
                        total_chunks=100,  # Default estimate, should be updated by caller
                        similarity_threshold=0.85,
                        enable_caching=True
                    )
                except Exception as e:
                    logger.warning(f"Could not create EntityRegistry: {e}. Proceeding without registry.")
                    self.registry = None
            
            if self.registry:
                # Note: EntityRegistry.register_entity has a different signature than expected
                # For now, we'll skip registry functionality and use simple deduplication
                logger.info(f"EntityRegistry available but not integrating in this version - using simple deduplication")
                all_entities = list(entity_map.values())
            else:
                all_entities = list(entity_map.values())
        else:
            all_entities = list(entity_map.values())
        
        # Sort by position
        all_entities.sort(key=lambda x: x.start_position)
        
        return all_entities
    
    def _repair_json_content(self, content: str) -> str:
        """Repair common JSON formatting issues in vLLM responses."""
        import re
        
        # Fix 1: Remove extra closing braces that cause parsing errors
        # Pattern: }}  or }}} at the end of entity objects
        content = re.sub(r'}+(?=\s*[,\]])', '}', content)
        
        # Fix 2: Fix malformed entity objects with extra braces
        # Look for pattern like: {"key": "value"}}} and fix to {"key": "value"}
        content = re.sub(r'(\})\}+', r'\1', content)
        
        # Fix 3: Fix unclosed JSON objects
        open_braces = content.count('{') - content.count('}')
        if open_braces > 0:
            content += '}' * open_braces
        
        # Fix 4: Fix unclosed arrays
        open_brackets = content.count('[') - content.count(']')
        if open_brackets > 0:
            content += ']' * open_brackets
        
        # Fix 5: Remove trailing commas before closing brackets/braces
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        
        # Fix 6: Ensure proper JSON structure for entities
        if 'entities' not in content and '{' in content:
            # Wrap in entities array if it looks like a standalone entity
            content = f'{{"entities": [{content}]}}'
        
        return content
    
    def _extract_json_fallback(self, content: str, pass_name: str) -> Dict:
        """Fallback strategies to extract JSON from malformed content."""
        logger.info(f"[{pass_name}] Attempting fallback JSON extraction")
        
        # Strategy 1: Look for JSON within the content
        import re
        json_pattern = r'\{[^{}]*"entities"[^{}]*\[[^\]]*\][^{}]*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                result = json.loads(match)
                logger.info(f"[{pass_name}] Fallback strategy 1 successful: found {len(result.get('entities', []))} entities")
                return result
            except json.JSONDecodeError:
                continue
        
        # Strategy 2: Look for entities array
        entities_pattern = r'"entities"\s*:\s*(\[[^\]]*\])'
        entities_matches = re.findall(entities_pattern, content, re.DOTALL)
        
        for match in entities_matches:
            try:
                entities_list = json.loads(match)
                result = {"entities": entities_list}
                logger.info(f"[{pass_name}] Fallback strategy 2 successful: found {len(entities_list)} entities")
                return result
            except json.JSONDecodeError:
                continue
        
        # Strategy 3: Use the vLLM client's JSON repair function
        try:
            from ..client.vllm_http_client import VLLMLocalClient
            # Create a temporary instance to access the repair method
            temp_client = VLLMLocalClient()
            repaired_content = temp_client._repair_json_if_needed(content)
            
            if repaired_content != content:
                parsed = json.loads(repaired_content)
                logger.info(f"[{pass_name}] Fallback strategy 3 (JSON repair) successful")
                # If repaired JSON doesn't have entities structure, wrap it
                if isinstance(parsed, dict) and "entities" in parsed:
                    return parsed
                else:
                    return {"entities": []}
        except Exception as e:
            logger.debug(f"[{pass_name}] JSON repair fallback failed: {e}")
        
        logger.warning(f"[{pass_name}] All fallback strategies failed")
        return {"entities": []}
    
    def get_metrics(self) -> MultiPassMetrics:
        """Get current extraction metrics."""
        return self.metrics
    
    def configure_pass(self, pass_type: ExtractionPass, config: PassConfiguration):
        """Configure a specific extraction pass."""
        self.pass_configs[pass_type] = config
        # Reload prompt if needed
        if pass_type in self.pass_configs:
            self._load_prompt_templates()
    
    def enable_passes(self, pass_numbers: List[int]):
        """Enable specific passes by number."""
        for pass_type, config in self.pass_configs.items():
            config.enabled = pass_type.value in pass_numbers
    
    def disable_passes(self, pass_numbers: List[int]):
        """Disable specific passes by number."""
        for pass_type, config in self.pass_configs.items():
            if pass_type.value in pass_numbers:
                config.enabled = False