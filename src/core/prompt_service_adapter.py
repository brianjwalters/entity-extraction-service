"""
Prompt Service Adapter for Intelligent Template Optimization

This adapter fetches templates from the Prompt Service and optimizes them
to fit within model context windows while preserving all entity types.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
import httpx

# Get config settings for max tokens
try:
    from src.core.config import get_settings
    _settings = get_settings()
    DEFAULT_TEMPLATE_MAX_TOKENS = _settings.ai.prompt_template_max_tokens
except Exception:
    DEFAULT_TEMPLATE_MAX_TOKENS = 50000

logger = logging.getLogger(__name__)


@dataclass
class TemplateSection:
    """Represents a section of the template."""
    content: str
    token_estimate: int
    priority: int
    entity_types: List[str]


class PromptServiceAdapter:
    """
    Adapter for intelligently using Prompt Service templates within context limits.
    
    This adapter:
    - Fetches comprehensive templates from Prompt Service
    - Optimizes them to fit within model context windows
    - Preserves all 275 entity types
    - Dynamically adapts based on document content
    """
    
    def __init__(
        self,
        prompt_service_url: str = "http://10.10.0.87:8003",
        max_template_tokens: int = None,  # Will use config default
        chars_per_token: float = 4.0  # Approximate
    ):
        """
        Initialize the Prompt Service Adapter.
        
        Args:
            prompt_service_url: Base URL of the Prompt Service
            max_template_tokens: Maximum tokens to use for template (uses config default if None)
            chars_per_token: Average characters per token for estimation
        """
        self.prompt_service_url = prompt_service_url
        self.max_template_tokens = max_template_tokens or DEFAULT_TEMPLATE_MAX_TOKENS
        self.chars_per_token = chars_per_token
        self.max_template_chars = int(max_template_tokens * chars_per_token)
        
        # Cache for templates
        self._template_cache = {}
        
        # Entity type relationships for intelligent grouping
        self.entity_type_groups = {
            "COURT_RELATED": ["COURT", "JUDGE", "MAGISTRATE", "ARBITRATOR", "MEDIATOR", "SPECIAL_MASTER", "COURT_CLERK", "COURT_REPORTER"],
            "PARTY_RELATED": ["PARTY", "PLAINTIFF", "DEFENDANT", "APPELLANT", "APPELLEE", "PETITIONER", "RESPONDENT", "INTERVENOR", "AMICUS_CURIAE"],
            "LEGAL_PROFESSIONALS": ["ATTORNEY", "LAW_FIRM", "PROSECUTOR", "PUBLIC_DEFENDER", "LEGAL_AID", "PARALEGAL"],
            "CITATIONS": ["CASE_CITATION", "STATUTE_CITATION", "USC_CITATION", "CFR_CITATION", "CONSTITUTIONAL_CITATION", "BILL_CITATION"],
            "DOCUMENTS": ["DOCUMENT", "MOTION", "BRIEF", "COMPLAINT", "ANSWER", "DISCOVERY_DOCUMENT", "DEPOSITION", "EXHIBIT"],
            "LEGAL_CONCEPTS": ["LEGAL_CONCEPT", "LEGAL_DOCTRINE", "PRECEDENT", "PRINCIPLE", "LEGAL_THEORY", "LEGAL_TERM"],
            "PROCEDURAL": ["PROCEDURAL_RULE", "CIVIL_PROCEDURE", "CRIMINAL_PROCEDURE", "APPELLATE_PROCEDURE", "LOCAL_RULE"],
            "DAMAGES": ["DAMAGES", "COMPENSATORY_DAMAGES", "PUNITIVE_DAMAGES", "STATUTORY_DAMAGES", "LIQUIDATED_DAMAGES"],
            "DATES": ["DATE", "FILING_DATE", "SERVICE_DATE", "HEARING_DATE", "TRIAL_DATE", "DECISION_DATE", "DEADLINE"],
            "MONETARY": ["MONETARY_AMOUNT", "FINANCIAL_AMOUNT", "SETTLEMENT_AMOUNT", "AWARD_AMOUNT", "FINE_AMOUNT"]
        }
        
        logger.info(f"Initialized PromptServiceAdapter with max {max_template_tokens} tokens for templates")
    
    async def get_full_template(self, template_name: str) -> Optional[str]:
        """
        Fetch the full template from Prompt Service.
        
        Args:
            template_name: Name of the template to fetch
            
        Returns:
            Full template content or None if error
        """
        if template_name in self._template_cache:
            return self._template_cache[template_name]
        
        try:
            async with httpx.AsyncClient(timeout=2700.0) as client:
                response = await client.get(f"{self.prompt_service_url}/api/v1/templates/{template_name}")
                
                if response.status_code == 200:
                    template_data = response.json()
                    template_content = template_data.get('content', '')
                    self._template_cache[template_name] = template_content
                    logger.info(f"Fetched template '{template_name}' from Prompt Service: {len(template_content)} chars")
                    return template_content
                else:
                    logger.warning(f"Failed to fetch template '{template_name}': HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching template '{template_name}': {e}")
            return None
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return len(text) // int(self.chars_per_token)
    
    def extract_entity_types_from_template(self, template: str) -> Set[str]:
        """
        Extract all entity types mentioned in a template.
        
        Args:
            template: Template content
            
        Returns:
            Set of entity type names found
        """
        entity_types = set()
        
        # Look for entity type patterns in various formats
        patterns = [
            r'EntityType\.(\w+)',  # Python enum format
            r'"entity_type":\s*"(\w+)"',  # JSON format
            r'type:\s*(\w+)',  # YAML format
            r'### (\w+_\w+)',  # Markdown headers
            r'- (\w+)(?:\s|:)',  # List items
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, template)
            entity_types.update(matches)
        
        # Also check for known entity types
        from ..models.entities import EntityType, CitationType
        
        for entity_type in EntityType:
            if entity_type.value in template:
                entity_types.add(entity_type.value)
        
        for citation_type in CitationType:
            if citation_type.value in template:
                entity_types.add(citation_type.value)
        
        return entity_types
    
    def get_related_entity_types(self, found_types: List[str]) -> Set[str]:
        """
        Get related entity types based on what was found.
        
        Args:
            found_types: Entity types found in document
            
        Returns:
            Set of related entity types to include
        """
        related = set(found_types)
        
        for found_type in found_types:
            # Add all types from same group
            for group_name, group_types in self.entity_type_groups.items():
                if found_type in group_types:
                    related.update(group_types)
        
        return related
    
    async def get_optimized_template(
        self,
        template_name: str,
        context: Dict[str, Any] = None,
        found_entity_types: List[str] = None,
        task_type: str = "general"
    ) -> str:
        """
        Get an optimized version of the template that fits within context limits.
        
        Args:
            template_name: Name of template to fetch
            context: Additional context for optimization
            found_entity_types: Entity types already found in document
            task_type: Type of task (discovery, validation, enhancement, relationship)
            
        Returns:
            Optimized template that fits within context window
        """
        # Fetch full template
        full_template = await self.get_full_template(template_name)
        if not full_template:
            logger.warning(f"Could not fetch template '{template_name}', returning empty")
            return ""
        
        # Check if full template fits
        full_tokens = self.estimate_tokens(full_template)
        logger.info(f"Template size: {len(full_template)} chars, estimated {full_tokens} tokens (limit: {self.max_template_tokens})")
        
        if full_tokens <= self.max_template_tokens:
            logger.info(f"Full template fits within limit ({full_tokens} tokens)")
            return full_template
        
        # Need to optimize - different strategies based on task
        logger.info(f"Template too large ({full_tokens} tokens), optimizing for {task_type} task")
        
        if task_type == "discovery":
            return self._optimize_for_discovery(full_template, found_entity_types)
        elif task_type == "validation":
            return self._optimize_for_validation(full_template, found_entity_types)
        elif task_type == "enhancement":
            return self._optimize_for_enhancement(full_template)
        elif task_type == "relationship":
            return self._optimize_for_relationships(full_template, found_entity_types)
        else:
            return self._optimize_general(full_template, found_entity_types)
    
    def _optimize_for_discovery(self, template: str, found_types: List[str] = None) -> str:
        """
        Optimize template for entity discovery task.
        Focus on entity types NOT yet found.
        """
        lines = template.split('\n')
        optimized_lines = []
        current_size = 0
        
        # Always keep header/instructions (first 50 lines or until first entity type)
        for i, line in enumerate(lines[:50]):
            optimized_lines.append(line)
            current_size += len(line) + 1
        
        # Get entity types to focus on
        template_types = self.extract_entity_types_from_template(template)
        if found_types:
            # Focus on types not yet found
            focus_types = template_types - set(found_types)
            # Also include related types
            related = self.get_related_entity_types(found_types)
            focus_types.update(related)
        else:
            # Include all common types
            focus_types = template_types
        
        # Add sections for focus entity types
        in_relevant_section = False
        for line in lines[50:]:
            # Check if this line mentions a focus entity type
            line_relevant = any(etype in line for etype in focus_types)
            
            if line_relevant:
                in_relevant_section = True
            elif line.startswith('###') or line.startswith('---'):
                in_relevant_section = False
            
            if in_relevant_section or line_relevant:
                if current_size + len(line) > self.max_template_chars:
                    optimized_lines.append("... [Template truncated for context limit] ...")
                    break
                optimized_lines.append(line)
                current_size += len(line) + 1
        
        result = '\n'.join(optimized_lines)
        logger.info(f"Optimized discovery template from {len(template)} to {len(result)} chars")
        return result
    
    def _optimize_for_validation(self, template: str, found_types: List[str] = None) -> str:
        """
        Optimize template for entity validation task.
        Focus on entity types that were found.
        """
        if not found_types:
            return self._optimize_general(template, found_types)
        
        lines = template.split('\n')
        optimized_lines = []
        current_size = 0
        
        # Keep header
        for i, line in enumerate(lines[:30]):
            optimized_lines.append(line)
            current_size += len(line) + 1
        
        # Get types to focus on (found + related)
        focus_types = self.get_related_entity_types(found_types)
        
        # Add validation rules for focus types
        in_relevant_section = False
        for line in lines[30:]:
            line_relevant = any(etype in line for etype in focus_types)
            
            if line_relevant:
                in_relevant_section = True
            elif line.startswith('###'):
                in_relevant_section = False
            
            if in_relevant_section or line_relevant:
                if current_size + len(line) > self.max_template_chars:
                    break
                optimized_lines.append(line)
                current_size += len(line) + 1
        
        result = '\n'.join(optimized_lines)
        logger.info(f"Optimized validation template from {len(template)} to {len(result)} chars")
        return result
    
    def _optimize_for_enhancement(self, template: str) -> str:
        """
        Optimize template for citation enhancement task.
        Focus on citation-specific content.
        """
        lines = template.split('\n')
        optimized_lines = []
        current_size = 0
        
        citation_keywords = ['citation', 'bluebook', 'reference', 'cite', 'USC', 'CFR', 'statute', 'case']
        
        for line in lines:
            # Keep citation-related content
            if any(keyword.lower() in line.lower() for keyword in citation_keywords):
                if current_size + len(line) > self.max_template_chars:
                    break
                optimized_lines.append(line)
                current_size += len(line) + 1
        
        result = '\n'.join(optimized_lines)
        logger.info(f"Optimized enhancement template from {len(template)} to {len(result)} chars")
        return result
    
    def _optimize_for_relationships(self, template: str, found_types: List[str] = None) -> str:
        """
        Optimize template for relationship extraction task.
        Focus on relationship patterns and found entities.
        """
        lines = template.split('\n')
        optimized_lines = []
        current_size = 0
        
        relationship_keywords = ['relationship', 'between', 'relates', 'represents', 'filed by', 
                                'decided by', 'cited in', 'authority', 'precedent']
        
        for line in lines:
            # Keep relationship-related content
            if any(keyword.lower() in line.lower() for keyword in relationship_keywords):
                if current_size + len(line) > self.max_template_chars:
                    break
                optimized_lines.append(line)
                current_size += len(line) + 1
        
        result = '\n'.join(optimized_lines)
        logger.info(f"Optimized relationship template from {len(template)} to {len(result)} chars")
        return result
    
    def _optimize_general(self, template: str, found_types: List[str] = None) -> str:
        """
        General optimization strategy - create a focused, concise template.
        """
        # For general extraction, use a simple, effective template
        optimized_template = """You are a legal entity extraction expert. Extract all legal entities from the text.

Focus on these key entity types:
- CASE_CITATION: Legal case citations (e.g., "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020)")
- STATUTE_CITATION: Statutory citations (e.g., "42 U.S.C. § 1983", "Cal. Civ. Code § 1234")
- PARTY: Parties in legal matters (plaintiffs, defendants, petitioners, respondents)
- ATTORNEY: Attorneys and legal representatives
- LAW_FIRM: Law firms and legal organizations
- COURT: Courts and judicial bodies
- JUDGE: Judges, justices, and judicial officers
- DATE: Important dates and deadlines
- DOCKET_NUMBER: Case docket numbers
- MONETARY_AMOUNT: Financial amounts, damages, settlements

For each entity found, provide:
1. entity_type: The type of entity
2. text: The exact text of the entity
3. confidence: Your confidence score (0.0 to 1.0)
4. start_position: Character position where entity starts
5. end_position: Character position where entity ends

Return your response as valid JSON in this format:
{
  "entities": [
    {
      "entity_type": "CASE_CITATION",
      "text": "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020)",
      "confidence": 0.95,
      "start_position": 100,
      "end_position": 145
    }
  ]
}

Extract entities from this text:"""
        
        # If we have found types, add a note about focusing on related types
        if found_types:
            related = self.get_related_entity_types(found_types)
            if related and len(related) > len(found_types):
                optimized_template += f"\n\nNote: Pay special attention to these related entity types: {', '.join(sorted(related)[:10])}"
        
        logger.info(f"Created optimized general template: {len(optimized_template)} chars (was {len(template)} chars)")
        return optimized_template
    
    def get_template_stats(self, template: str) -> Dict[str, Any]:
        """
        Get statistics about a template.
        
        Args:
            template: Template content
            
        Returns:
            Dictionary with template statistics
        """
        entity_types = self.extract_entity_types_from_template(template)
        
        return {
            "total_chars": len(template),
            "estimated_tokens": self.estimate_tokens(template),
            "entity_types_found": len(entity_types),
            "entity_types": sorted(list(entity_types)),
            "fits_in_context": self.estimate_tokens(template) <= self.max_template_tokens
        }