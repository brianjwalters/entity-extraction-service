"""
Prompt Manager for Document Intelligence Service v2.0.0

Manages loading, caching, and retrieval of consolidated prompt templates
for single-pass and 4-wave extraction strategies (Waves 1-3: entities, Wave 4: relationships).
"""

import logging
import time
import json
from pathlib import Path
from typing import Dict, Optional, Any, List
from functools import lru_cache
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class PromptTemplate:
    """Represents a single prompt template with metadata."""

    def __init__(self, name: str, content: str, file_path: str):
        self.name = name
        self.content = content
        self.file_path = file_path
        self.loaded_at = datetime.now()
        self.token_count = len(content) // 4  # Rough estimate: 4 chars per token

    def __repr__(self) -> str:
        return f"PromptTemplate(name={self.name}, tokens≈{self.token_count}, loaded={self.loaded_at})"


class PromptManager:
    """
    Manages consolidated prompt templates for Document Intelligence Service.

    Features:
    - Lazy loading of prompt templates
    - In-memory caching with LRU eviction
    - Support for single-pass and 4-wave extraction strategies
    - Automatic prompt reloading on file changes (optional)
    - Dynamic content injection (pattern examples, previous results)

    Prompt Files (in src/prompts/wave/):
    - single_pass.md - For very small documents (<5K chars)
    - wave1.md - Wave 1: Actors, legal citations, temporal (15 entity types)
    - wave2.md - Wave 2: Procedural, financial, organizations (14 entity types)
    - wave3.md - Wave 3: Supporting types + relationships (5 entity types)
    - wave4.md - Wave 4: Entity relationships (34 relationship types)
    """

    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialize PromptManager.

        Args:
            prompts_dir: Directory containing prompt .md files
                        Defaults to entity-extraction-service/src/prompts/wave/
        """
        if prompts_dir is None:
            # Use service-local prompts directory
            import os
            current_file = Path(__file__)
            service_root = current_file.parent.parent  # From core/ up to src/
            prompts_dir = str(service_root / "prompts" / "wave")

        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, PromptTemplate] = {}

        # API pattern cache (1 hour TTL)
        self._pattern_cache: Optional[Dict[str, Any]] = None
        self._pattern_cache_time: float = 0
        self._pattern_cache_ttl: int = 3600  # 1 hour in seconds
        self._pattern_api_url: str = "http://10.10.0.87:8007/api/v1/patterns?format=detailed"

        # Validate prompts directory exists
        if not self.prompts_dir.exists():
            raise FileNotFoundError(
                f"Prompts directory not found: {self.prompts_dir}\n"
                f"Expected prompt files at: {self.prompts_dir}"
            )

        logger.info(f"PromptManager initialized with prompts_dir: {self.prompts_dir}")

    def _load_prompt_file(self, filename: str) -> str:
        """
        Load prompt content from file.

        Args:
            filename: Name of prompt file (e.g., 'single_pass_consolidated_prompt.md')

        Returns:
            Prompt content as string

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        file_path = self.prompts_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {file_path}\n"
                f"Available files: {list(self.prompts_dir.glob('*.md'))}"
            )

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            logger.debug(f"Loaded prompt from {file_path} ({len(content)} chars)")
            return content

        except Exception as e:
            logger.error(f"Failed to load prompt file {file_path}: {e}")
            raise

    def _fetch_patterns_from_api(self) -> Dict[str, Any]:
        """
        Fetch patterns from Entity Extraction Service API with 1-hour caching.

        Returns:
            Dictionary containing patterns_by_category or empty dict on failure
        """
        # Check cache first
        current_time = time.time()
        if (self._pattern_cache is not None and
            current_time - self._pattern_cache_time < self._pattern_cache_ttl):
            logger.debug("Using cached API pattern data")
            return self._pattern_cache

        try:
            # Fetch from API with short timeout
            logger.info(f"Fetching patterns from API: {self._pattern_api_url}")
            response = requests.get(self._pattern_api_url, timeout=5.0)
            response.raise_for_status()

            data = response.json()
            self._pattern_cache = data
            self._pattern_cache_time = current_time

            logger.info(f"Cached {data.get('total_patterns', 0)} patterns from API")
            return data

        except Exception as e:
            logger.warning(f"Failed to fetch patterns from API: {e}")
            # Return stale cache if available
            if self._pattern_cache is not None:
                logger.info("Using stale pattern cache as fallback")
                return self._pattern_cache
            # Return empty fallback
            return {"total_patterns": 0, "patterns_by_category": {}}

    def _build_pattern_examples_for_wave(self, wave: int) -> str:
        """
        Build pattern examples section for specific wave from API data.

        Args:
            wave: Wave number (1, 2, 3, or 4)

        Returns:
            Formatted markdown string with pattern examples and negative examples
        """
        # Wave 4 uses relationship patterns (handled separately)
        if wave == 4:
            return self._build_relationship_pattern_examples()

        # Define entity types per wave
        wave_entity_types = {
            1: ["CASE_CITATION", "STATUTE_CITATION", "PARTY", "ATTORNEY", "COURT", "JUDGE",
                "USC_CITATION", "CFR_CITATION", "STATE_STATUTE_CITATION", "CONSTITUTIONAL_CITATION",
                "DATE", "FILING_DATE", "DEADLINE", "HEARING_DATE", "TRIAL_DATE"],
            2: ["CASE_NUMBER", "DOCKET_NUMBER", "MOTION", "BRIEF", "PROCEDURAL_RULE",
                "MONETARY_AMOUNT", "DAMAGES", "FINE", "FEE", "AWARD",
                "LAW_FIRM", "PROSECUTOR", "PUBLIC_DEFENDER", "GOVERNMENT_ENTITY"],
            3: ["ADDRESS", "EMAIL", "PHONE_NUMBER", "BAR_NUMBER", "CORPORATION"]
        }

        patterns_data = self._fetch_patterns_from_api()
        patterns_by_category = patterns_data.get("patterns_by_category", {})

        if not patterns_by_category:
            # Fallback to basic message
            return "**Pattern examples will be loaded from API when service is accessible.**\n"

        # Build markdown output
        output = ["### Pattern Examples from Entity Extraction Service API\n"]
        entity_types = wave_entity_types.get(wave, [])

        # Extract examples for each entity type from API patterns
        for entity_type in entity_types:
            examples_found = []

            # Search through all categories for this entity type
            for category, patterns in patterns_by_category.items():
                for pattern in patterns:
                    if pattern.get("entity_type") == entity_type:
                        pattern_examples = pattern.get("examples", [])
                        examples_found.extend(pattern_examples[:3])  # Take first 3
                        if len(examples_found) >= 5:  # Limit to 5 examples per type
                            break
                if len(examples_found) >= 5:
                    break

            if examples_found:
                output.append(f"\n#### {entity_type}")
                output.append("**DO EXTRACT:**")
                for example in examples_found[:5]:
                    output.append(f"- {example}")

                # Add negative examples
                negative = self._build_negative_examples(entity_type)
                if negative:
                    output.append(negative)

        return "\n".join(output)

    def _build_negative_examples(self, entity_type: str) -> str:
        """
        Generate negative examples (anti-patterns) for an entity type.

        These fix the 7 extraction errors identified in testing.

        Args:
            entity_type: Entity type to generate negative examples for

        Returns:
            Formatted markdown string with negative examples
        """
        negative_examples = {
            "CASE_CITATION": """
**DO NOT EXTRACT:**
- ❌ Filenames: "Rahimi.md", "document.pdf", "case_brief.docx"
- ❌ Generic names without citation format: "Bruen" (unless in context like "in Bruen")
- ❌ URLs or file paths: "/docs/Rahimi.pdf", "https://example.com/cases"
- ❌ Document titles without proper citation components
**VALIDATION**: Must have volume + reporter + page OR be in legal citation context""",

            "STATUTE_CITATION": """
**DO NOT EXTRACT:**
- ❌ Bare section symbols: "§922(g)(8)" without "U.S.C." or state code
- ❌ Statute references misidentified as procedural rules
**VALIDATION**: Require full format like "18 U.S.C. § 922(g)(8)" """,

            "PROCEDURAL_RULE": """
**DO NOT EXTRACT:**
- ❌ USC statute citations: "18 U.S.C. § 922(g)(8)" is a STATUTE, not procedural rule
- ❌ State statutes as procedural rules
**VALIDATION**: Only extract "Rule X", "Fed. R. Civ. P. X", "FRCP X" formats""",

            "CASE_NUMBER": """
**DO NOT EXTRACT:**
- ❌ Case names as case numbers: "Bruen" is a case name (CASE_CITATION), not a number
- ❌ Years: "2024" alone is not a case number
**VALIDATION**: Must match format like "No. 22-6640", "Case No. 1:20-cv-12345" """,

            "PARTY": """
**DO NOT EXTRACT:**
- ❌ Generic terms: "intimate partner", "domestic partner", "the victim"
- ❌ Legal roles without names: "plaintiff", "defendant", "appellant"
- ❌ Generic descriptors: "defendant's spouse", "a person subject to"
**VALIDATION**: Must be specific named individual or entity (proper noun)""",

            "DATE": """
**CONTEXT REQUIRED:**
- Extract dates WITH legal significance context
- "June 21, 2024" alone → check for context:
  - "filed on June 21, 2024" → FILING_DATE
  - "heard on June 21, 2024" → HEARING_DATE
  - "decided June 21, 2024" → Use specific temporal type
**VALIDATION**: Prefer specific date types (FILING_DATE, HEARING_DATE) over generic DATE""",

            "ATTORNEY": """
**DO NOT EXTRACT:**
- ❌ Legal references: "John Blackstone" from "Blackstone's Commentaries"
- ❌ Historical legal scholars: "Blackstone", "Coke", "Prosser" (unless modern attorney)
- ❌ Generic titles: "Attorney General", "Counsel for the United States" (without name)
**VALIDATION**: Require name + attorney indicator (Attorney, Esq., Counsel)""",
        }

        return negative_examples.get(entity_type, "")

    def _build_relationship_pattern_examples(self) -> str:
        """
        Build pattern examples for Wave 4 relationship extraction.

        Returns:
            Formatted markdown string with relationship pattern examples
        """
        # Relationship patterns for Wave 4 (34 types across 8 categories)
        relationship_examples = """
### Relationship Pattern Examples

Wave 4 extracts **34 relationship types** across 8 categories. Focus on explicit textual evidence.

#### Case-to-Case Relationships (5 types)
**CITES_CASE**: "In Roe v. Wade, the Court cited Griswold v. Connecticut"
**OVERRULES_CASE**: "Dobbs expressly overrules Roe v. Wade"
**DISTINGUISHES_CASE**: "Brown is distinguishable from Plessy because..."
**FOLLOWS_CASE**: "Miranda follows the precedent established in Escobedo"
**QUESTIONS_CASE**: "The majority questions the reasoning in Lochner"

#### Statute Relationships (4 types)
**CITES_STATUTE**: "The complaint alleges violations of 42 U.S.C. § 1983"
**INTERPRETS_STATUTE**: "The Court interprets Title VII to include..."
**APPLIES_STATUTE**: "Applying the Administrative Procedure Act, the Court finds..."
**INVALIDATES_STATUTE**: "The Supreme Court invalidates Section 4 of the VRA"

#### Party Relationships (4 types)
**PARTY_VS_PARTY**: "John Smith brings this action against Acme Corporation"
**REPRESENTS**: "Sarah Johnson represents the plaintiff, Mary Williams"
**EMPLOYED_BY**: "Michael Chen, partner at Chen & Associates"
**MEMBER_OF**: "Named plaintiffs, members of the proposed class"

#### Procedural Relationships (4 types)
**APPEALS_FROM**: "This case comes to us on appeal from the SDNY"
**REMANDS_TO**: "We reverse and remand to the District Court"
**CONSOLIDATES_WITH**: "Smith v. Acme is consolidated with Jones v. Acme"
**RELATES_TO**: "This matter is related to Case No. 21-cv-12345"

#### Document Relationships (4 types)
**REFERENCES_DOCUMENT**: "The Complaint references Exhibit A"
**INCORPORATES_BY_REFERENCE**: "This Agreement incorporates by reference the MSA"
**AMENDS**: "First Amendment to Lease amends the Original Lease"
**SUPERSEDES**: "This Restated Agreement supersedes all prior agreements"

#### Contractual Relationships (4 types)
**CONTRACTS_WITH**: "Acme entered into an agreement with TechCo"
**OBLIGATED_TO**: "The Contractor is obligated to deliver to Client"
**BENEFITS**: "The indemnification clause benefits TechCo"
**GUARANTEES**: "Parent Company guarantees obligations of Subsidiary"

#### Judicial Relationships (6 types)
**DECIDED_BY**: "Decided by a three-judge panel consisting of..."
**AUTHORED_BY**: "Chief Justice Roberts delivered the opinion"
**JOINED_BY**: "Justice Kagan's dissent, in which Sotomayor joined"
**DISSENTED_BY**: "Justice Breyer filed a dissenting opinion"
**CONCURRED_BY**: "Justice Thomas filed a concurring opinion"
**RECUSED_FROM**: "Justice Sotomayor recused herself from this case"

#### Temporal Relationships (3 types)
**OCCURRED_BEFORE**: "Agreement signed on Jan 15 before the act on Mar 3"
**OCCURRED_AFTER**: "Plaintiff filed suit after receiving right-to-sue letter"
**OCCURRED_DURING**: "Harassment occurred during plaintiff's employment"

**Critical**: All relationships MUST reference entities from Waves 1-3 results (provided in previous_results).
"""
        return relationship_examples

    def _format_previous_results(self, entities: List[Dict[str, Any]]) -> str:
        """
        Format entities from Waves 1-3 for Wave 4 relationship extraction.

        Args:
            entities: List of entity dictionaries from previous waves

        Returns:
            Formatted JSON string with entity data for relationship extraction
        """
        formatted_entities = []

        for entity in entities:
            formatted_entities.append({
                'id': entity.get('id'),
                'entity_type': entity.get('entity_type'),
                'text': entity.get('text'),
                'start_pos': entity.get('start_pos'),
                'end_pos': entity.get('end_pos'),
                'wave_number': entity.get('wave_number'),
                'subtype': entity.get('subtype'),
                'category': entity.get('category')
            })

        # Count entities by type for summary
        entity_types_available = {}
        for e in formatted_entities:
            entity_type = e.get('entity_type', 'UNKNOWN')
            entity_types_available[entity_type] = entity_types_available.get(entity_type, 0) + 1

        # Format as readable JSON for LLM
        return json.dumps({
            'total_entities': len(formatted_entities),
            'entities': formatted_entities,
            'entity_types_available': entity_types_available
        }, indent=2)

    def get_single_pass_prompt(self) -> PromptTemplate:
        """
        Get single-pass consolidated prompt for very small documents.

        Use for: Documents < 5K characters
        Strategy: All entity types in one prompt
        Expected tokens: ~1,800

        Returns:
            PromptTemplate with single-pass consolidated prompt
        """
        cache_key = "single_pass"

        if cache_key not in self._cache:
            content = self._load_prompt_file("single_pass.md")
            self._cache[cache_key] = PromptTemplate(
                name="single_pass",
                content=content,
                file_path=str(self.prompts_dir / "single_pass.md")
            )
            logger.info(f"Cached single-pass prompt: {self._cache[cache_key]}")

        return self._cache[cache_key]

    def get_three_wave_prompt(
        self,
        wave: int,
        previous_results: Optional[List[Dict[str, Any]]] = None
    ) -> PromptTemplate:
        """
        Get prompt for specific wave of 4-wave extraction system with API pattern injection.

        Wave 1: Actors, legal citations, temporal entities (15 entity types)
        Wave 2: Procedural, financial, organizations (14 entity types)
        Wave 3: Supporting types (5 entity types)
        Wave 4: Entity relationships (34 relationship types)

        Use for: Documents 5K - 150K characters
        Strategy: 4 sequential LLM calls for comprehensive extraction
        Expected tokens per wave: ~7,000 - 10,000

        Args:
            wave: Wave number (1, 2, 3, or 4)
            previous_results: Entities from previous waves (required for Wave 4)

        Returns:
            PromptTemplate for specified wave with pattern examples injected

        Raises:
            ValueError: If wave is not 1, 2, 3, or 4
        """
        if wave not in (1, 2, 3, 4):
            raise ValueError(f"Wave must be 1, 2, 3, or 4, got: {wave}")

        # Wave 4 requires previous_results validation
        if wave == 4 and not previous_results:
            logger.warning("Wave 4 called without previous_results - relationships may be limited")

        cache_key = f"wave{wave}"

        # Wave 4 cannot be cached with static content (depends on previous_results)
        # For Waves 1-3, use caching
        if cache_key not in self._cache or wave == 4:
            filename = f"wave{wave}.md"
            content = self._load_prompt_file(filename)

            # Fetch API data and inject pattern examples
            pattern_examples = self._build_pattern_examples_for_wave(wave)

            # Replace {{pattern_examples}} placeholder with actual examples from API
            content = content.replace("{{pattern_examples}}", pattern_examples)

            # Wave 4: Inject previous_results (entities from Waves 1-3)
            if wave == 4:
                if previous_results:
                    previous_results_json = self._format_previous_results(previous_results)
                    content = content.replace("{{previous_results}}", previous_results_json)
                    logger.info(f"Wave 4 prompt: Injected {len(previous_results)} entities from Waves 1-3")
                else:
                    # Provide empty structure if no previous results
                    content = content.replace("{{previous_results}}", '{"total_entities": 0, "entities": [], "entity_types_available": {}}')
                    logger.warning("Wave 4 prompt: No previous_results provided - using empty entity set")

            # Cache for Waves 1-3 only (Wave 4 is dynamic)
            if wave != 4:
                self._cache[cache_key] = PromptTemplate(
                    name=f"wave{wave}",
                    content=content,
                    file_path=str(self.prompts_dir / filename)
                )
                logger.info(f"Cached Wave {wave} prompt with {len(pattern_examples)} chars of API pattern examples")
            else:
                # For Wave 4, return ephemeral PromptTemplate (not cached)
                logger.info(f"Generated Wave 4 prompt (not cached) with {len(pattern_examples)} chars of relationship pattern examples")
                return PromptTemplate(
                    name=f"wave{wave}",
                    content=content,
                    file_path=str(self.prompts_dir / filename)
                )

        return self._cache[cache_key]

    def get_all_three_wave_prompts(self) -> Dict[int, PromptTemplate]:
        """
        Get all entity extraction wave prompts (Waves 1-3) at once.

        Note: Wave 4 is excluded as it requires previous_results parameter.
        Use get_three_wave_prompt(4, previous_results=...) for Wave 4.

        Useful for pre-caching all prompts during service startup.

        Returns:
            Dictionary mapping wave number to PromptTemplate (Waves 1-3 only)
        """
        return {
            1: self.get_three_wave_prompt(1),
            2: self.get_three_wave_prompt(2),
            3: self.get_three_wave_prompt(3)
        }

    def clear_cache(self) -> None:
        """
        Clear all cached prompts.

        Useful for forcing reload of prompts after file changes.
        """
        old_size = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared prompt cache ({old_size} entries)")

    def reload_prompt(self, prompt_name: str) -> PromptTemplate:
        """
        Force reload a specific prompt from disk.

        Args:
            prompt_name: Name of prompt to reload
                        ('single_pass' or 'three_wave_wave1/2/3')

        Returns:
            Reloaded PromptTemplate
        """
        # Remove from cache
        if prompt_name in self._cache:
            del self._cache[prompt_name]
            logger.debug(f"Removed {prompt_name} from cache")

        # Reload based on name
        if prompt_name == "single_pass":
            return self.get_single_pass_prompt()
        elif prompt_name.startswith("wave"):
            wave = int(prompt_name[-1])
            return self.get_three_wave_prompt(wave)
        else:
            raise ValueError(f"Unknown prompt name: {prompt_name}")

    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get statistics about prompt cache.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "cached_prompts": len(self._cache),
            "prompts": {
                name: {
                    "token_count": prompt.token_count,
                    "loaded_at": prompt.loaded_at.isoformat(),
                    "file_path": prompt.file_path
                }
                for name, prompt in self._cache.items()
            },
            "prompts_dir": str(self.prompts_dir)
        }

    def warmup_cache(self) -> None:
        """
        Pre-load all prompts into cache during service startup.

        Reduces first-request latency by loading all prompts upfront.
        Note: Wave 4 is not cached as it requires dynamic previous_results injection.
        Recommended for production deployments.
        """
        logger.info("Warming up prompt cache...")

        start_time = datetime.now()

        # Load single-pass prompt
        self.get_single_pass_prompt()

        # Load all entity extraction wave prompts (Waves 1-3)
        self.get_all_three_wave_prompts()

        duration = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"Prompt cache warmed up: {len(self._cache)} prompts loaded in {duration:.2f}s (Waves 1-3 + single-pass)"
        )


# Global prompt manager instance (singleton pattern)
_prompt_manager_instance: Optional[PromptManager] = None


def get_prompt_manager(prompts_dir: Optional[str] = None) -> PromptManager:
    """
    Get global PromptManager instance (singleton).

    Args:
        prompts_dir: Directory containing prompt files (only used on first call)

    Returns:
        Global PromptManager instance
    """
    global _prompt_manager_instance

    if _prompt_manager_instance is None:
        _prompt_manager_instance = PromptManager(prompts_dir=prompts_dir)
        logger.info("Initialized global PromptManager instance")

    return _prompt_manager_instance


def reset_prompt_manager() -> None:
    """
    Reset global PromptManager instance.

    Useful for testing or forcing re-initialization.
    """
    global _prompt_manager_instance
    _prompt_manager_instance = None
    logger.info("Reset global PromptManager instance")
