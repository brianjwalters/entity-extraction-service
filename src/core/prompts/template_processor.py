"""
Template Processor for Enhanced Prompt Generation with Schema Compliance

This module processes template files and injects examples from the PatternLoader
system to create enhanced prompts for both unified and multipass strategies.
Enforces LurisEntityV2 schema compliance for all outputs.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from jinja2 import Template, Environment, FileSystemLoader

from .dynamic_prompt_builder import DynamicPromptBuilder, PromptConfiguration
from ..schema import (
    LurisEntityV2, 
    ExtractionResultV2, 
    validate_result_schema,
    SchemaEnforcer,
    convert_result_to_v2
)

logger = logging.getLogger(__name__)


class SchemaCompliantTemplateProcessor:
    """
    Enhanced template processor that enforces LurisEntityV2 schema compliance
    for all prompt outputs and result processing.
    """
    
    def __init__(self, config: PromptConfiguration = None, enforce_schema: bool = True):
        """
        Initialize schema-compliant template processor.
        
        Args:
            config: Prompt configuration
            enforce_schema: Whether to enforce strict schema compliance
        """
        self.config = config or PromptConfiguration()
        self.prompt_builder = DynamicPromptBuilder(self.config)
        self.enforce_schema = enforce_schema
        self.schema_enforcer = SchemaEnforcer(strict_mode=enforce_schema, auto_fix=True)
        
        # Set up Jinja2 environment
        template_dir = Path(__file__).parent.parent.parent / "prompts"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Multipass template mapping (updated for V2 templates)
        self.multipass_templates = {
            1: "strategies/multipass/pass_1_core_legal_entities_v2.md",
            2: "strategies/multipass/pass_2_legal_citations_v2.md", 
            3: "strategies/multipass/pass_3_case_information_v2.md",
            4: "strategies/multipass/pass_4_dates_deadlines_v2.md",
            5: "strategies/multipass/pass_5_financial_elements_v2.md",
            6: "strategies/multipass/pass_6_legal_professionals_v2.md",
            7: "strategies/multipass/pass_7_geographic_misc_v2.md"
        }
        
        # Pass configurations
        self.pass_configs = {
            1: {
                "name": "Core Legal Entities",
                "entity_types": ["CASE_CITATION", "STATUTE_CITATION", "PARTY", "ATTORNEY", "COURT", "JUDGE"],
                "confidence_threshold": 0.85,
                "examples_per_type": 4
            },
            2: {
                "name": "Legal Citations & References", 
                "entity_types": ["USC_CITATION", "CFR_CITATION", "STATE_STATUTE_CITATION", "CONSTITUTIONAL_CITATION"],
                "confidence_threshold": 0.85,
                "examples_per_type": 4
            },
            3: {
                "name": "Case Information & Procedural Elements",
                "entity_types": ["CASE_NUMBER", "DOCKET_NUMBER", "MOTION", "BRIEF", "PROCEDURAL_RULE"],
                "confidence_threshold": 0.8,
                "examples_per_type": 3
            },
            4: {
                "name": "Dates, Deadlines & Temporal Information",
                "entity_types": ["DATE", "FILING_DATE", "DEADLINE", "HEARING_DATE", "TRIAL_DATE"],
                "confidence_threshold": 0.85,
                "examples_per_type": 3
            },
            5: {
                "name": "Financial & Monetary Elements",
                "entity_types": ["MONETARY_AMOUNT", "DAMAGES", "FINE", "FEE", "AWARD"],
                "confidence_threshold": 0.8,
                "examples_per_type": 3
            },
            6: {
                "name": "Legal Professionals & Organizations",
                "entity_types": ["LAW_FIRM", "PROSECUTOR", "PUBLIC_DEFENDER", "GOVERNMENT_ENTITY"],
                "confidence_threshold": 0.75,
                "examples_per_type": 2
            },
            7: {
                "name": "Geographic & Miscellaneous Entities",
                "entity_types": ["ADDRESS", "EMAIL", "PHONE_NUMBER", "BAR_NUMBER", "CORPORATION"],
                "confidence_threshold": 0.7,
                "examples_per_type": 2
            }
        }
        
        logger.info(f"Schema-compliant template processor initialized (enforce_schema: {enforce_schema})")
    
    async def process_unified_template_v2(
        self,
        document_text: str,
        target_entities: Optional[List[str]] = None,
        confidence_threshold: float = 0.7
    ) -> str:
        """
        Process the enhanced unified template with LurisEntityV2 schema compliance.
        
        Args:
            document_text: Document to extract entities from
            target_entities: Specific entity types to focus on
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            Enhanced prompt with schema compliance instructions
        """
        try:
            # Load the enhanced unified template
            template = self.jinja_env.get_template("strategies/unified/unified_extraction_enhanced.md")
            
            # Get pattern examples using the dynamic prompt builder
            pattern_examples = await self._build_pattern_examples_section(
                target_entities, document_text
            )
            
            # Render the template with LurisEntityV2 schema instructions
            rendered_prompt = template.render(
                document_text=document_text,
                confidence_threshold=confidence_threshold,
                pattern_examples=pattern_examples,
                schema_version="LurisEntityV2",
                enforce_schema=True
            )
            
            return rendered_prompt
            
        except Exception as e:
            logger.error(f"Error processing unified template v2: {e}")
            # Fallback to dynamic prompt builder
            return await self.prompt_builder.build_enhanced_prompt(
                document_text=document_text,
                strategy="unified",
                target_entities=target_entities
            )
    
    async def process_multipass_template_v2(
        self,
        document_text: str,
        pass_number: int,
        previous_results: Optional[List[Dict]] = None,
        confidence_threshold: Optional[float] = None
    ) -> str:
        """
        Process a multipass template with LurisEntityV2 schema compliance.
        
        Args:
            document_text: Document to extract entities from
            pass_number: Which pass (1-7) to process
            previous_results: Results from previous passes
            confidence_threshold: Override confidence threshold
            
        Returns:
            Enhanced prompt for the specific pass with schema compliance
        """
        if pass_number not in self.multipass_templates:
            raise ValueError(f"Invalid pass number: {pass_number}. Must be 1-7")
        
        try:
            # Get pass configuration
            pass_config = self.pass_configs[pass_number]
            template_path = self.multipass_templates[pass_number]
            
            # Load the V2 template
            template = self.jinja_env.get_template(template_path)
            
            # Get pattern examples for this pass's entity types
            pattern_examples = await self._build_pattern_examples_section(
                pass_config["entity_types"], document_text
            )
            
            # Format previous results for context
            previous_results_text = self._format_previous_results(previous_results)
            
            # Use pass-specific confidence threshold if not overridden
            threshold = confidence_threshold or pass_config["confidence_threshold"]
            
            # Render the template
            rendered_prompt = template.render(
                text_chunk=document_text,
                pattern_examples=pattern_examples,
                previous_results=previous_results_text,
                confidence_threshold=threshold,
                pass_number=pass_number,
                pass_name=pass_config["name"],
                target_entity_types=pass_config["entity_types"]
            )
            
            return rendered_prompt
            
        except Exception as e:
            logger.error(f"Error processing multipass template v2 (pass {pass_number}): {e}")
            # Fallback to dynamic prompt builder
            return await self.prompt_builder.build_enhanced_prompt(
                document_text=document_text,
                strategy="multipass",
                pass_number=pass_number,
                previous_results=previous_results
            )
    
    def validate_and_enforce_result(self, result: Any) -> ExtractionResultV2:
        """
        Validate and enforce schema compliance on extraction results.
        
        Args:
            result: Raw extraction result from LLM
            
        Returns:
            Schema-compliant ExtractionResultV2 object
        """
        try:
            # Parse JSON if string
            if isinstance(result, str):
                result = json.loads(result)
            
            # Convert to ExtractionResultV2
            if self.enforce_schema:
                standardized_result = self.schema_enforcer.enforce_result_schema(result)
            else:
                standardized_result = convert_result_to_v2(result)
            
            # Validate the result
            validation_result = validate_result_schema(standardized_result)
            
            if not validation_result.is_valid:
                logger.warning(f"Schema validation failed: {validation_result.errors}")
                if self.enforce_schema:
                    # Try to fix common issues
                    standardized_result = self._auto_fix_result_issues(standardized_result, validation_result.errors)
            
            if validation_result.warnings:
                logger.info(f"Schema validation warnings: {validation_result.warnings}")
            
            return standardized_result
            
        except Exception as e:
            logger.error(f"Failed to validate/enforce result schema: {e}")
            # Return minimal valid result
            return ExtractionResultV2(
                entities=[],
                success=False,
                errors=[f"Schema enforcement failed: {str(e)}"]
            )
    
    def _auto_fix_result_issues(self, result: ExtractionResultV2, errors: List[str]) -> ExtractionResultV2:
        """Automatically fix common result validation issues."""
        # Fix entity validation issues
        fixed_entities = []
        for entity in result.entities:
            try:
                fixed_entity = self.schema_enforcer.enforce_entity_schema(entity)
                fixed_entities.append(fixed_entity)
            except Exception as e:
                logger.warning(f"Could not fix entity {entity.text}: {e}")
                # Skip invalid entities
                continue
        
        result.entities = fixed_entities
        result.citations = [e for e in result.entities if "CITATION" in e.entity_type]
        
        # Recalculate derived fields
        result.__post_init__()
        
        return result
    
    async def _build_pattern_examples_section(
        self, 
        target_entities: Optional[List[str]], 
        document_text: str
    ) -> str:
        """Build pattern examples section for template injection."""
        try:
            # Use the dynamic prompt builder to get examples
            examples = await self.prompt_builder.get_pattern_examples(
                target_entities or [],
                max_examples_per_type=3
            )
            
            if not examples:
                return "No pattern examples available for the requested entity types."
            
            # Format examples for template injection
            examples_text = "## Pattern Examples from YAML Files\n\n"
            
            for entity_type, type_examples in examples.items():
                examples_text += f"### {entity_type} Examples:\n"
                for i, example in enumerate(type_examples[:3], 1):
                    examples_text += f"{i}. **Pattern:** `{example.get('pattern', '')}`\n"
                    examples_text += f"   **Example:** {example.get('example', '')}\n"
                    if 'description' in example:
                        examples_text += f"   **Description:** {example['description']}\n"
                    examples_text += "\n"
                examples_text += "\n"
            
            return examples_text
            
        except Exception as e:
            logger.error(f"Error building pattern examples section: {e}")
            return "Pattern examples temporarily unavailable."
    
    def _format_previous_results(self, previous_results: Optional[List[Dict]]) -> str:
        """Format previous results for context in multipass extraction."""
        if not previous_results:
            return "No previous results available."
        
        try:
            formatted = "### Entities Found in Previous Passes:\n\n"
            
            for result in previous_results:
                if isinstance(result, dict) and 'entities' in result:
                    entities = result['entities']
                    if entities:
                        formatted += f"**Pass {result.get('pass_number', '?')}:** {len(entities)} entities found\n"
                        # Show sample entities
                        for entity in entities[:3]:
                            entity_text = entity.get('text', '')
                            entity_type = entity.get('entity_type', 'UNKNOWN')
                            formatted += f"- {entity_text} ({entity_type})\n"
                        if len(entities) > 3:
                            formatted += f"- ... and {len(entities) - 3} more\n"
                        formatted += "\n"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting previous results: {e}")
            return "Previous results formatting error."
    
    def get_pass_configuration(self, pass_number: int) -> Dict[str, Any]:
        """Get configuration for a specific multipass pass."""
        return self.pass_configs.get(pass_number, {})
    
    def get_supported_passes(self) -> List[int]:
        """Get list of supported multipass pass numbers."""
        return list(self.multipass_templates.keys())


class TemplateProcessor:
    """
    Processes template files and injects examples from PatternLoader to create
    enhanced prompts for entity extraction.
    """
    
    def __init__(self, config: PromptConfiguration = None):
        self.config = config or PromptConfiguration()
        self.prompt_builder = DynamicPromptBuilder(self.config)
        
        # Set up Jinja2 environment
        template_dir = Path(__file__).parent.parent.parent / "prompts"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    async def process_unified_template(
        self,
        document_text: str,
        target_entities: Optional[List[str]] = None,
        confidence_threshold: float = 0.7
    ) -> str:
        """
        Process the enhanced unified template with pattern examples.
        
        Args:
            document_text: Document to extract entities from
            target_entities: Specific entity types to focus on
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            Enhanced prompt with injected examples
        """
        try:
            # Load the enhanced unified template
            template = self.jinja_env.get_template("strategies/unified/unified_extraction_enhanced.md")
            
            # Use the dynamic prompt builder to get entity examples
            entity_examples_section = await self._build_entity_examples_section(
                target_entities, document_text
            )
            
            # Render the template with examples
            rendered_prompt = template.render(
                document_text=document_text,
                confidence_threshold=confidence_threshold,
                entity_examples_section=entity_examples_section
            )
            
            return rendered_prompt
            
        except Exception as e:
            logger.error(f"Error processing unified template: {e}")
            # Fallback to dynamic prompt builder
            return await self.prompt_builder.build_enhanced_prompt(
                document_text=document_text,
                strategy="unified",
                target_entities=target_entities
            )
    
    async def process_multipass_template(
        self,
        document_text: str,
        pass_number: int,
        previous_results: Optional[List[Dict]] = None
    ) -> str:
        """
        Process a multipass template with targeted examples for a specific pass.
        
        Args:
            document_text: Document to extract entities from
            pass_number: Which pass (1-7) to process
            previous_results: Results from previous passes
            
        Returns:
            Enhanced prompt for the specific pass
        """
        try:
            # Use the dynamic prompt builder for multipass prompts
            enhanced_prompt = await self.prompt_builder.build_enhanced_prompt(
                document_text=document_text,
                strategy="multipass",
                pass_number=pass_number
            )
            
            # Add previous results context if available
            if previous_results:
                enhanced_prompt = self._add_previous_results_context(
                    enhanced_prompt, previous_results
                )
            
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Error processing multipass template for pass {pass_number}: {e}")
            raise
    
    async def _build_entity_examples_section(
        self,
        target_entities: Optional[List[str]],
        document_text: str
    ) -> str:
        """
        Build the entity examples section for template injection.
        """
        try:
            from .dynamic_prompt_builder import PromptPatternEnhancer
            
            async with PromptPatternEnhancer(self.config) as enhancer:
                # Get entity examples
                if target_entities:
                    entity_examples = await enhancer.get_entity_examples_for_prompt(
                        entity_types=target_entities,
                        max_examples_per_type=3,
                        include_pattern_context=True
                    )
                else:
                    # Get all entity types with examples
                    all_entity_data = await enhancer.get_all_entity_types_with_examples()
                    # Limit to most relevant entities to avoid token overflow
                    entity_examples = {k: v for k, v in list(all_entity_data.items())[:30]}
                
                # Build examples section
                examples_section = "## Entity Types with Pattern Examples\n\n"
                examples_section += "Use these real examples from the pattern library to guide extraction:\n\n"
                
                # Group entities by category
                entity_clusters = self._cluster_entities_for_display(entity_examples.keys())
                
                for cluster_name, cluster_entities in entity_clusters.items():
                    if cluster_entities:
                        examples_section += f"### {cluster_name}\n\n"
                        
                        for entity_type in cluster_entities:
                            if entity_type in entity_examples:
                                entity_info = entity_examples[entity_type]
                                examples = entity_info.get("examples", [])
                                
                                if examples:
                                    examples_section += f"**{entity_type}**:\n"
                                    for i, example in enumerate(examples[:3], 1):
                                        examples_section += f"{i}. \"{example}\"\n"
                                    
                                    # Add pattern hints if available
                                    hints = entity_info.get("pattern_hints", [])
                                    if hints:
                                        examples_section += f"   *Pattern hints: {hints[0]}*\n"
                                    
                                    examples_section += "\n"
                        
                        examples_section += "\n"
                
                return examples_section
                
        except Exception as e:
            logger.error(f"Error building entity examples section: {e}")
            return "## Entity Examples\n\nPattern examples are currently unavailable.\n\n"
    
    def _cluster_entities_for_display(self, entity_types: List[str]) -> Dict[str, List[str]]:
        """
        Group entity types for better display organization.
        """
        clusters = {
            "Core Legal Entities": [],
            "Citations & References": [],
            "Court & Procedural": [],
            "Financial & Temporal": [],
            "Parties & Organizations": [],
            "Contact & Geographic": []
        }
        
        for entity_type in entity_types:
            entity_upper = entity_type.upper()
            
            if any(term in entity_upper for term in ["CITATION", "USC", "CFR", "STATUTE", "CONSTITUTIONAL"]):
                clusters["Citations & References"].append(entity_type)
            elif any(term in entity_upper for term in ["COURT", "JUDGE", "MOTION", "BRIEF", "PROCEDURAL"]):
                clusters["Court & Procedural"].append(entity_type)
            elif any(term in entity_upper for term in ["CASE_LAW", "PARTY", "ATTORNEY", "PLAINTIFF", "DEFENDANT"]):
                clusters["Core Legal Entities"].append(entity_type)
            elif any(term in entity_upper for term in ["MONETARY", "DATE", "DEADLINE", "AMOUNT", "FINE", "FEE"]):
                clusters["Financial & Temporal"].append(entity_type)
            elif any(term in entity_upper for term in ["ORGANIZATION", "FIRM", "AGENCY", "CORPORATION", "GOVERNMENT"]):
                clusters["Parties & Organizations"].append(entity_type)
            elif any(term in entity_upper for term in ["ADDRESS", "EMAIL", "PHONE", "JURISDICTION", "VENUE"]):
                clusters["Contact & Geographic"].append(entity_type)
            else:
                # Default to Core Legal Entities
                clusters["Core Legal Entities"].append(entity_type)
        
        # Remove empty clusters and limit size
        filtered_clusters = {}
        for name, entities in clusters.items():
            if entities:
                # Limit each cluster to avoid token overflow
                filtered_clusters[name] = entities[:8]
        
        return filtered_clusters
    
    def _add_previous_results_context(
        self,
        prompt: str,
        previous_results: List[Dict]
    ) -> str:
        """
        Add context from previous pass results to the current pass prompt.
        """
        if not previous_results:
            return prompt
        
        context_section = "\n## Previous Pass Results\n"
        context_section += "The following entities were found in previous passes (use for context, don't re-extract):\n\n"
        
        # Group results by entity type
        results_by_type = {}
        for result in previous_results[:20]:  # Limit to avoid bloat
            entity_type = result.get("entity_type", "UNKNOWN")
            if entity_type not in results_by_type:
                results_by_type[entity_type] = []
            results_by_type[entity_type].append(result.get("text", ""))
        
        # Format the context
        for entity_type, texts in results_by_type.items():
            context_section += f"- **{entity_type}**: {', '.join(f'\"{text[:30]}...\"' for text in texts[:3])}\n"
        
        context_section += "\n"
        
        # Insert before the document text section
        insertion_point = prompt.find("## Document Text to")
        if insertion_point != -1:
            return prompt[:insertion_point] + context_section + prompt[insertion_point:]
        else:
            # Fallback: append before document text
            return prompt + context_section
    
    async def get_available_templates(self) -> Dict[str, List[str]]:
        """
        Get list of available template files for both strategies.
        
        Returns:
            Dict mapping strategy names to available template files
        """
        templates = {
            "unified": [],
            "multipass": []
        }
        
        try:
            prompts_dir = Path(__file__).parent.parent.parent / "prompts" / "strategies"
            
            # Check unified templates
            unified_dir = prompts_dir / "unified"
            if unified_dir.exists():
                templates["unified"] = [f.name for f in unified_dir.glob("*.md")]
            
            # Check multipass templates
            multipass_dir = prompts_dir / "multipass"
            if multipass_dir.exists():
                templates["multipass"] = [f.name for f in multipass_dir.glob("*.md")]
            
        except Exception as e:
            logger.error(f"Error getting available templates: {e}")
        
        return templates


class EnhancedPromptService:
    """
    Main service for creating enhanced prompts using both template processing
    and dynamic prompt building capabilities.
    """
    
    def __init__(self, config: PromptConfiguration = None):
        self.config = config or PromptConfiguration()
        self.template_processor = TemplateProcessor(self.config)
        self.prompt_builder = DynamicPromptBuilder(self.config)
    
    async def create_extraction_prompt(
        self,
        document_text: str,
        strategy: str = "unified",
        pass_number: Optional[int] = None,
        target_entities: Optional[List[str]] = None,
        previous_results: Optional[List[Dict]] = None,
        confidence_threshold: float = 0.7
    ) -> str:
        """
        Create an enhanced extraction prompt using pattern examples.
        
        Args:
            document_text: Document to extract entities from
            strategy: "unified" or "multipass"
            pass_number: Pass number for multipass strategy (1-7)
            target_entities: Specific entity types to focus on
            previous_results: Results from previous passes (multipass only)
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            Enhanced prompt with pattern examples
        """
        try:
            if strategy == "multipass":
                if pass_number is None:
                    raise ValueError("pass_number required for multipass strategy")
                
                return await self.template_processor.process_multipass_template(
                    document_text=document_text,
                    pass_number=pass_number,
                    previous_results=previous_results
                )
            
            else:  # unified strategy
                return await self.template_processor.process_unified_template(
                    document_text=document_text,
                    target_entities=target_entities,
                    confidence_threshold=confidence_threshold
                )
                
        except Exception as e:
            logger.error(f"Error creating extraction prompt: {e}")
            # Fallback to basic dynamic prompt builder
            return await self.prompt_builder.build_enhanced_prompt(
                document_text=document_text,
                strategy=strategy,
                pass_number=pass_number,
                target_entities=target_entities
            )
    
    async def validate_prompt_quality(self, prompt: str) -> Dict[str, Any]:
        """
        Validate the quality of a generated prompt.
        
        Returns:
            Dict with quality metrics and validation results
        """
        try:
            metrics = {
                "length": len(prompt),
                "has_examples": "examples" in prompt.lower(),
                "has_instructions": "instructions" in prompt.lower(),
                "has_output_format": "output format" in prompt.lower(),
                "has_entity_types": any(
                    entity_type in prompt.upper() 
                    for entity_type in ["CASE_CITATION", "JUDGE", "COURT", "ATTORNEY"]
                ),
                "estimated_tokens": len(prompt.split()) * 1.3,  # Rough estimate
                "validation_passed": True
            }
            
            # Check for critical components
            if metrics["estimated_tokens"] > 100000:
                metrics["validation_passed"] = False
                metrics["warning"] = "Prompt too long, may exceed token limits"
            
            if not metrics["has_examples"]:
                metrics["validation_passed"] = False
                metrics["warning"] = "Prompt missing pattern examples"
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error validating prompt quality: {e}")
            return {"validation_passed": False, "error": str(e)}