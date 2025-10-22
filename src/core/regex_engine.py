"""
Regex Engine for Entity Extraction Service - Stage 1 Pattern-Based Extraction

This module implements the RegexEngine class for high-performance pattern-based entity 
extraction from legal documents. Provides comprehensive regex pattern execution with 
confidence scoring, conflict resolution, and proper Entity/Citation object creation.

Features:
- Async pattern loading and compilation with caching
- Federal and state jurisdiction pattern support  
- Confidence-based scoring and conflict resolution
- Position tracking and context extraction
- Entity and Citation object creation
- Performance monitoring and error handling
- Pattern priority management
"""

import re
import time
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict, namedtuple
from functools import lru_cache
import concurrent.futures
from pathlib import Path

from ..models.entities import (
    Entity, Citation, EntityType, CitationType, ExtractionMethod, 
    TextPosition, EntityAttributes, CitationComponents
)
from ..utils.pattern_loader import PatternLoader, CompiledPattern, PatternGroup
from ..core.config import get_settings


@dataclass
class ExtractionMatch:
    """Raw extraction match before Entity/Citation creation."""
    pattern_name: str
    match_text: str
    start_pos: int
    end_pos: int
    confidence: float
    components: Dict[str, str]
    pattern_type: str
    entity_type: Optional[str] = None
    context: Optional[str] = None
    match_groups: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExtractionContext:
    """Context information for extraction operations."""
    document_id: Optional[str] = None
    content_type: str = "text/plain"
    jurisdiction: Optional[str] = None
    court_level: Optional[str] = None
    extraction_mode: str = "hybrid"
    confidence_threshold: float = 0.7
    max_matches_per_pattern: int = 1000
    include_context: bool = True
    context_window: int = 100
    text_preview: Optional[str] = None  # Preview of text for smart pattern filtering


@dataclass
class ConflictResolution:
    """Configuration for handling overlapping matches."""
    strategy: str = "highest_confidence"  # highest_confidence, pattern_priority, merge
    merge_threshold: float = 0.8
    overlap_tolerance: int = 0  # Set to 0 to only filter exact overlaps, not nearby matches
    max_conflicts_per_position: int = 3


class RegexEngineError(Exception):
    """Custom exception for RegexEngine errors."""
    pass


class RegexEngine:
    """
    High-performance regex engine for legal entity extraction.
    
    Implements Stage 1 of the hybrid extraction pipeline, providing:
    - Comprehensive pattern-based extraction
    - Federal and state jurisdiction support
    - Confidence scoring and conflict resolution
    - Entity and Citation object creation
    - Performance optimization and caching
    """
    
    def __init__(
        self,
        pattern_loader: Optional[PatternLoader] = None,
        patterns_dir: Optional[str] = None,
        enable_caching: bool = True,
        cache_size: int = 1000,
        enable_performance_monitoring: bool = True,
        max_workers: int = 4
    ):
        """
        Initialize RegexEngine.
        
        Args:
            patterns_dir: Directory containing pattern files
            enable_caching: Enable pattern compilation caching
            cache_size: Maximum cache size for compiled patterns
            enable_performance_monitoring: Enable performance metrics
            max_workers: Maximum worker threads for parallel processing
        """
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()
        
        # Configuration
        self.enable_caching = enable_caching
        self.cache_size = cache_size
        self.enable_performance_monitoring = enable_performance_monitoring
        self.max_workers = max_workers
        
        # Initialize pattern loader (prefer provided loader to avoid dual loading)
        if pattern_loader is not None:
            self.logger.info("Using provided PatternLoader for unified pattern loading")
            self.pattern_loader = pattern_loader
        else:
            self.logger.info("Creating new PatternLoader (fallback mode)")
            self.pattern_loader = PatternLoader(
                patterns_dir=patterns_dir,
                enable_caching=enable_caching,
                cache_size=cache_size,
                enable_validation=True,
                enable_compilation=True,
                enable_threading=True,
                max_workers=max_workers
            )
        
        # Performance metrics
        self._performance_metrics = {
            "total_extractions": 0,
            "total_matches": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "pattern_executions": defaultdict(int),
            "entity_type_counts": defaultdict(int),
            "confidence_distribution": defaultdict(int)
        }
        
        # Pattern priority mapping (higher number = higher priority)
        self._pattern_priorities = {
            "case_citations": 95,
            "statute_citations": 90,
            "constitutional": 92,
            "justices": 88,
            "courts": 85,
            "procedural": 80,
            "short_forms": 75,
            "dates": 70,
            "monetary_amounts": 65,
            "parties": 85,
            "attorneys": 82
        }
        
        # Thread pool for parallel processing
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        
        self.logger.info(f"RegexEngine initialized with {len(self.pattern_loader.get_pattern_names())} patterns")
    
    async def extract_entities(
        self,
        text: str,
        context: Optional[ExtractionContext] = None,
        conflict_resolution: Optional[ConflictResolution] = None
    ) -> Tuple[List[Entity], List[Citation]]:
        """
        Extract entities and citations from text using regex patterns.
        
        Args:
            text: Input text to extract from
            context: Extraction context and configuration
            conflict_resolution: Configuration for handling conflicts
            
        Returns:
            Tuple[List[Entity], List[Citation]]: Extracted entities and citations
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not text or not text.strip():
                return [], []
            
            # Apply defaults
            if context is None:
                context = ExtractionContext()
            if conflict_resolution is None:
                conflict_resolution = ConflictResolution()
            
            # Set text preview for smart pattern filtering
            if not context.text_preview:
                context.text_preview = text
            
            # Execute pattern matching
            self.logger.info(f"About to execute patterns for text length: {len(text)}")
            raw_matches = await self._execute_patterns(text, context)
            self.logger.info(f"Pattern execution completed, found {len(raw_matches)} raw matches")
            
            # Resolve conflicts
            resolved_matches = await self._resolve_conflicts(raw_matches, conflict_resolution)
            
            # Create entities and citations
            entities, citations = await self._create_objects(resolved_matches, text, context)
            
            # Update performance metrics
            if self.enable_performance_monitoring:
                self._update_metrics(start_time, len(raw_matches), len(entities), len(citations))
            
            self.logger.debug(
                f"Extracted {len(entities)} entities and {len(citations)} citations "
                f"from {len(text)} characters in {time.time() - start_time:.3f}s"
            )
            
            return entities, citations
            
        except Exception as e:
            self.logger.error(f"Entity extraction failed: {e}")
            raise RegexEngineError(f"Entity extraction failed: {e}")
    
    async def _execute_patterns(
        self,
        text: str,
        context: ExtractionContext
    ) -> List[ExtractionMatch]:
        """Execute all applicable patterns against the text using batched processing."""
        matches = []
        
        # Get applicable patterns based on context
        self.logger.info("Getting applicable patterns...")
        patterns = await self._get_applicable_patterns(context)
        self.logger.info(f"Found {len(patterns)} applicable patterns")
        
        if not patterns:
            self.logger.warning("No applicable patterns found for extraction context")
            return matches
        
        # Use batched execution for better performance and stability
        self.logger.info(f"Executing {len(patterns)} patterns using batched processing")
        pattern_results = await self._execute_patterns_batched(patterns, text, context)
        
        for result in pattern_results:
            if isinstance(result, Exception):
                self.logger.error(f"Pattern execution failed: {result}")
                continue
            
            if isinstance(result, list):
                matches.extend(result)
        
        self.logger.debug(f"Executed {len(patterns)} patterns, found {len(matches)} matches")
        
        return matches
    
    async def _execute_patterns_batched(
        self,
        patterns: List[CompiledPattern],
        text: str,
        context: ExtractionContext,
        batch_size: int = 50,
        max_concurrent: int = 10
    ) -> List[Union[List[ExtractionMatch], Exception]]:
        """Execute patterns in batches with concurrency control to prevent hanging.
        
        Args:
            patterns: List of compiled patterns to execute
            text: Text to process
            context: Extraction context
            batch_size: Number of patterns per batch (default 50)
            max_concurrent: Maximum concurrent pattern executions (default 10)
            
        Returns:
            List of results (either match lists or exceptions)
        """
        all_results = []
        
        # Create a semaphore to limit concurrent executions
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(pattern: CompiledPattern) -> Union[List[ExtractionMatch], Exception]:
            """Execute a single pattern with semaphore control and timeout."""
            async with semaphore:
                try:
                    # Add timeout to prevent hanging (500ms per pattern - increased for complex patterns)
                    result = await asyncio.wait_for(
                        self._execute_single_pattern(pattern, text, context),
                        timeout=0.5  # 500ms timeout - increased from 100ms
                    )
                    return result
                except asyncio.TimeoutError:
                    self.logger.warning(f"Pattern '{pattern.name}' timed out after 500ms")
                    if self.enable_performance_monitoring:
                        self._performance_metrics.setdefault("pattern_timeouts", {})
                        self._performance_metrics["pattern_timeouts"][pattern.name] = \
                            self._performance_metrics["pattern_timeouts"].get(pattern.name, 0) + 1
                    return []
                except Exception as e:
                    self.logger.error(f"Pattern '{pattern.name}' failed: {e}")
                    return e
        
        # Process patterns in batches
        total_batches = (len(patterns) + batch_size - 1) // batch_size
        self.logger.info(f"Starting batched processing: {len(patterns)} patterns in {total_batches} batches")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(patterns))
            batch_patterns = patterns[start_idx:end_idx]
            
            self.logger.info(f"Processing batch {batch_num + 1}/{total_batches} "
                            f"({len(batch_patterns)} patterns)")
            
            # Create tasks for this batch with semaphore control
            batch_tasks = []
            for pattern in batch_patterns:
                task = asyncio.create_task(execute_with_semaphore(pattern))
                batch_tasks.append(task)
            
            # Execute batch with gather
            try:
                self.logger.debug(f"Gathering {len(batch_tasks)} tasks for batch {batch_num + 1}")
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                self.logger.debug(f"Batch {batch_num + 1} gather completed")
                all_results.extend(batch_results)
                
                # Log batch completion
                successful_results = sum(1 for r in batch_results 
                                       if isinstance(r, list) and len(r) > 0)
                self.logger.debug(f"Batch {batch_num + 1} completed: "
                                f"{successful_results} patterns with matches")
                
            except Exception as e:
                self.logger.error(f"Batch {batch_num + 1} failed catastrophically: {e}")
                # Add empty results for failed batch
                all_results.extend([e] * len(batch_patterns))
            
            # Small delay between batches to prevent resource exhaustion
            if batch_num < total_batches - 1:
                await asyncio.sleep(0.01)  # 10ms delay between batches
        
        return all_results
    
    async def _execute_single_pattern(
        self,
        pattern: CompiledPattern,
        text: str,
        context: ExtractionContext
    ) -> List[ExtractionMatch]:
        """Execute a single pattern against text."""
        matches = []
        
        try:
            # Track pattern execution
            if self.enable_performance_monitoring:
                self._performance_metrics["pattern_executions"][pattern.name] += 1
            
            # Execute regex pattern
            regex_matches = pattern.compiled_regex.finditer(text)
            
            # Debug: Check if we have a match for judge patterns
            if 'judge' in pattern.name.lower() or 'justice' in pattern.name.lower():
                test_match = pattern.compiled_regex.search(text)
                self.logger.info(f"Judge/Justice pattern '{pattern.name}': pattern='{pattern.pattern}', text='{text[:50]}...', match={test_match.group() if test_match else 'None'}")
            
            match_count = 0
            for match in regex_matches:
                if match_count >= context.max_matches_per_pattern:
                    break
                
                # Debug: Log match processing for judge patterns
                if 'judge' in pattern.name.lower() or 'justice' in pattern.name.lower():
                    self.logger.info(f"Processing match for pattern '{pattern.name}': match='{match.group()}'")
                
                # Create extraction match
                extraction_match = await self._create_extraction_match(
                    pattern, match, text, context
                )
                
                # Debug: Log extraction match result for judge patterns
                if 'judge' in pattern.name.lower() or 'justice' in pattern.name.lower():
                    if extraction_match:
                        self.logger.info(f"Created extraction match for '{pattern.name}': confidence={extraction_match.confidence}, threshold={context.confidence_threshold}")
                    else:
                        self.logger.info(f"Failed to create extraction match for '{pattern.name}'")
                
                if extraction_match and extraction_match.confidence >= context.confidence_threshold:
                    matches.append(extraction_match)
                    # Debug: Log successful match addition for judge patterns
                    if 'judge' in pattern.name.lower() or 'justice' in pattern.name.lower():
                        self.logger.info(f"Added extraction match for '{pattern.name}' to results")
                    match_count += 1
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Pattern execution failed for {pattern.name}: {e}")
            return []
    
    async def _create_extraction_match(
        self,
        pattern: CompiledPattern,
        regex_match: re.Match,
        text: str,
        context: ExtractionContext
    ) -> Optional[ExtractionMatch]:
        """Create an ExtractionMatch from a regex match."""
        try:
            # Extract match information
            match_text = regex_match.group(0)
            start_pos = regex_match.start()
            end_pos = regex_match.end()
            
            # Extract named groups
            match_groups = regex_match.groupdict()
            
            # Calculate confidence based on pattern confidence and match quality
            confidence = await self._calculate_match_confidence(
                pattern, regex_match, match_text
            )
            
            # Debug: Log confidence calculation for judge patterns
            if 'judge' in pattern.name.lower() or 'justice' in pattern.name.lower():
                self.logger.info(f"Confidence calculation for '{pattern.name}': base_confidence={pattern.confidence}, final_confidence={confidence}")
            
            # Extract context if requested
            context_snippet = None
            if context.include_context:
                context_snippet = await self._extract_context(
                    text, start_pos, end_pos, context.context_window
                )
            
            # Determine pattern type and entity type
            pattern_type = self._determine_pattern_type(pattern.name)
            entity_type = pattern.entity_type
            
            return ExtractionMatch(
                pattern_name=pattern.name,
                match_text=match_text,
                start_pos=start_pos,
                end_pos=end_pos,
                confidence=confidence,
                components=pattern.components,
                pattern_type=pattern_type,
                entity_type=entity_type,
                context=context_snippet,
                match_groups=match_groups
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create extraction match: {e}")
            return None
    
    async def _calculate_match_confidence(
        self,
        pattern: CompiledPattern,
        regex_match: re.Match,
        match_text: str
    ) -> float:
        """
        Calculate confidence score for a pattern match.
        
        Optimized for legal patterns with synchronous calculations to avoid
        async issues that were causing 0.0 confidence scores.
        """
        base_confidence = pattern.confidence
        
        # Initialize confidence with base value
        final_confidence = base_confidence
        
        # Apply synchronous adjustments for legal patterns
        
        # 1. Match completeness adjustment (synchronous)
        if hasattr(regex_match, 'groupdict'):
            groups = regex_match.groupdict()
            if groups:
                filled_groups = sum(1 for v in groups.values() if v is not None)
                total_groups = len(groups)
                if total_groups > 0:
                    completeness_ratio = filled_groups / total_groups
                    # Boost confidence for complete matches, slight penalty for partial
                    completeness_factor = 0.9 + (0.1 * completeness_ratio)
                    final_confidence *= completeness_factor
        
        # 2. Match length adjustment for legal entities (synchronous)
        if len(match_text) >= 3:  # Minimum reasonable length for legal entities
            if len(match_text) < 10:
                length_factor = 0.95  # Short matches (e.g., "J. Doe")
            elif len(match_text) < 25:
                length_factor = 1.0   # Normal matches (e.g., "Justice Roberts")
            else:
                length_factor = 1.02  # Long matches (e.g., full case citations)
            
            final_confidence *= length_factor
        else:
            # Very short matches get a penalty
            final_confidence *= 0.85
        
        # 3. Legal entity type boost (synchronous)
        legal_entity_boosts = {
            'CHIEF_JUSTICE': 1.05,
            'ASSOCIATE_JUSTICE': 1.03,
            'JUDGE': 1.02,
            'DISTRICT_JUDGE': 1.02,
            'CIRCUIT_JUDGE': 1.02,
            'COURT': 1.01,
            'CASE_CITATION': 1.04,
            'STATUTE_CITATION': 1.03,
            'CONSTITUTIONAL_CITATION': 1.04
        }
        
        if pattern.entity_type and pattern.entity_type.upper() in legal_entity_boosts:
            entity_boost = legal_entity_boosts[pattern.entity_type.upper()]
            final_confidence *= entity_boost
        
        # 4. High-priority pattern boost (synchronous)
        high_priority_patterns = [
            'chief_justice', 'case_citation', 'statute_citation', 
            'supreme_court', 'federal_court', 'district_court'
        ]
        
        pattern_name_lower = pattern.name.lower()
        if any(hp in pattern_name_lower for hp in high_priority_patterns):
            final_confidence *= 1.02
        
        # 5. Apply simple validation rules (synchronous, avoiding async calls)
        if pattern.validation_rules:
            # Quick validation checks without async operations
            validation_penalty = 1.0
            
            # Year validation (if present in groups)
            if hasattr(regex_match, 'groupdict'):
                groups = regex_match.groupdict()
                if 'year' in groups and groups['year']:
                    try:
                        year = int(groups['year'])
                        if year < 1600 or year > 2030:
                            validation_penalty *= 0.7  # Unlikely year
                    except (ValueError, TypeError):
                        validation_penalty *= 0.9
            
            final_confidence *= validation_penalty
        
        # Cap confidence at 1.0 and ensure minimum threshold
        final_confidence = min(1.0, max(0.5, final_confidence))
        
        # Debug logging for judge/justice patterns
        if 'judge' in pattern_name_lower or 'justice' in pattern_name_lower:
            self.logger.debug(
                f"Optimized confidence for '{pattern.name}': "
                f"base={base_confidence:.3f}, final={final_confidence:.3f}, "
                f"match='{match_text}'"
            )
        
        return final_confidence
    
    async def _validate_match_against_rules(
        self,
        pattern: CompiledPattern,
        regex_match: re.Match,
        match_text: str
    ) -> float:
        """Validate match against pattern-specific rules."""
        if not pattern.validation_rules:
            return 1.0
        
        validation_score = 1.0
        
        try:
            # Year validation
            if 'year_range' in pattern.validation_rules:
                year_range = pattern.validation_rules['year_range']
                groups = regex_match.groupdict()
                
                if 'year' in groups and groups['year']:
                    year = int(groups['year'])
                    min_year = year_range.get('min_year', 1600)
                    max_year = year_range.get('max_year', 2030)
                    
                    if not (min_year <= year <= max_year):
                        validation_score *= 0.5
            
            # Volume validation
            if 'volume_ranges' in pattern.validation_rules:
                volume_ranges = pattern.validation_rules['volume_ranges']
                groups = regex_match.groupdict()
                
                if 'volume' in groups and groups['volume']:
                    volume = int(groups['volume'])
                    
                    # Check against relevant reporter
                    if 'reporter' in groups:
                        reporter = groups['reporter'].lower()
                        for reporter_key, range_info in volume_ranges.items():
                            if reporter_key.replace('_', ' ') in reporter:
                                min_vol = range_info.get('min_volume', 1)
                                max_vol = range_info.get('max_volume', 999)
                                
                                if not (min_vol <= volume <= max_vol):
                                    validation_score *= 0.7
                                break
            
            # Page validation
            if 'page_validation' in pattern.validation_rules:
                page_val = pattern.validation_rules['page_validation']
                groups = regex_match.groupdict()
                
                if 'page' in groups and groups['page']:
                    page = int(groups['page'])
                    min_page = page_val.get('min_page', 1)
                    max_page = page_val.get('max_page', 9999)
                    
                    if not (min_page <= page <= max_page):
                        validation_score *= 0.8
            
        except (ValueError, KeyError) as e:
            self.logger.debug(f"Validation rule error: {e}")
            validation_score *= 0.9
        
        return validation_score
    
    async def _get_applicable_patterns(self, context: ExtractionContext) -> List[CompiledPattern]:
        """Get patterns applicable to the extraction context with smart filtering."""
        all_patterns = []
        
        # Get all pattern groups
        pattern_groups = self.pattern_loader.get_pattern_groups()
        
        for group_name, pattern_group in pattern_groups.items():
            # Filter by jurisdiction if specified
            if context.jurisdiction:
                if (pattern_group.metadata.jurisdiction != 'all' and
                    pattern_group.metadata.jurisdiction != context.jurisdiction):
                    continue
            
            # Filter by court level if specified
            if context.court_level:
                if (pattern_group.metadata.court_level and
                    pattern_group.metadata.court_level != context.court_level):
                    continue
            
            # Add patterns from this group
            for pattern in pattern_group.patterns.values():
                # Apply confidence threshold
                if pattern.confidence >= context.confidence_threshold:
                    all_patterns.append(pattern)
        
        # Smart Pattern Filtering: Analyze text to prioritize relevant patterns
        if hasattr(context, 'text_preview') and context.text_preview:
            # Score patterns based on text relevance
            scored_patterns = []
            for pattern in all_patterns:
                relevance_score = self._calculate_pattern_relevance(
                    pattern, 
                    context.text_preview[:1000]  # Use first 1000 chars for relevance scoring
                )
                scored_patterns.append((pattern, relevance_score))
            
            # Sort by relevance score, then priority, then confidence
            scored_patterns.sort(
                key=lambda p: (
                    p[1],  # relevance score
                    self._get_pattern_priority(p[0].name),
                    p[0].confidence
                ),
                reverse=True
            )
            
            # Use ALL patterns for maximum coverage with 150+ entity types
            # No limit to ensure all entity types are properly extracted
            filtered_patterns = [p[0] for p in scored_patterns]
            
            if len(scored_patterns) != len(all_patterns):
                self.logger.info(
                    f"Smart filtering prioritized {len(scored_patterns)} patterns"
                )
            
            return filtered_patterns
        else:
            # Fallback: Sort by priority and confidence, limit to 300
            all_patterns.sort(
                key=lambda p: (
                    self._get_pattern_priority(p.name),
                    p.confidence
                ),
                reverse=True
            )
            
            # No pattern limit - use all patterns for comprehensive extraction
            # With 150+ entity types and 90+ citation types, we need all patterns
            self.logger.info(
                f"Using all {len(all_patterns)} patterns for comprehensive extraction"
            )
            
            return all_patterns
    
    def _calculate_pattern_relevance(self, pattern: CompiledPattern, text_preview: str) -> float:
        """
        Calculate relevance score for a pattern based on text content.
        
        Enhanced for legal document analysis with better pattern matching
        and legal terminology detection.
        
        Args:
            pattern: The compiled pattern to score
            text_preview: Preview of text to analyze for relevance
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        relevance_score = 0.0
        text_lower = text_preview.lower()
        pattern_name_lower = pattern.name.lower()
        
        # Enhanced legal pattern indicators with more comprehensive terms
        pattern_indicators = {
            'judge': [
                'judge', 'justice', 'chief justice', 'associate justice',
                'honorable', 'j.', 'magistrate', 'presiding', 'circuit judge',
                'district judge', 'appellate judge'
            ],
            'attorney': [
                'attorney', 'lawyer', 'counsel', 'esq', 'esquire', 
                'represented by', 'law firm', 'llp', 'p.c.', 'bar no.',
                'counsel for', 'attorney for'
            ],
            'party': [
                'plaintiff', 'defendant', 'petitioner', 'respondent', 
                'appellant', 'appellee', 'movant', 'claimant', 'debtor',
                'creditor', 'intervenor'
            ],
            'case': [
                'v.', 'versus', 'v ', ' v ', 'u.s.', 'f.2d', 'f.3d', 
                'f. supp', 'n.y.', 'cal.', 's. ct.', 'l. ed.', 
                'f.4th', 'p.2d', 'p.3d', 'a.2d', 'a.3d', 'n.e.', 's.e.',
                'n.w.', 's.w.', 'so.', 'so.2d', 'so.3d'
            ],
            'statute': [
                '§', 'section', 'u.s.c.', 'usc', 'rcw', 'code', 'statute',
                'title', 'chapter', 'subsection', 'paragraph', 'clause',
                'cfr', 'c.f.r.', 'pursuant to', 'under'
            ],
            'court': [
                'supreme court', 'district court', 'circuit', 'appellate',
                'court of appeals', 'bankruptcy court', 'tax court',
                'magistrate', 'tribunal', 'board', 'commission',
                'ninth circuit', 'second circuit', 'federal court'
            ],
            'procedural': [
                'motion', 'order', 'judgment', 'decree', 'ruling',
                'opinion', 'decision', 'verdict', 'plea', 'complaint',
                'answer', 'brief', 'memorandum', 'affidavit', 'deposition'
            ],
            'date': [
                'january', 'february', 'march', 'april', 'may', 'june', 
                'july', 'august', 'september', 'october', 'november', 'december',
                'jan.', 'feb.', 'mar.', 'apr.', 'jun.', 'jul.', 'aug.',
                'sept.', 'oct.', 'nov.', 'dec.', 'filed', 'dated', 'decided'
            ],
            'docket': [
                'no.', 'case no', 'docket', 'cause no', 'civil action',
                'criminal no.', 'cv-', 'cr-', 'case number', 'file no.'
            ]
        }
        
        # Calculate base relevance from pattern-text matches
        max_indicator_boost = 0.0
        for pattern_type, indicators in pattern_indicators.items():
            if pattern_type in pattern_name_lower:
                # Count how many indicators are present
                indicator_count = sum(1 for indicator in indicators if indicator in text_lower)
                if indicator_count > 0:
                    # More indicators = higher relevance (diminishing returns)
                    type_boost = min(0.4, 0.15 * indicator_count)
                    max_indicator_boost = max(max_indicator_boost, type_boost)
        
        relevance_score += max_indicator_boost
        
        # Legal document type detection bonus
        legal_doc_indicators = [
            'in the united states', 'court of', 'opinion of the court',
            'case no.', 'civil action', 'criminal case', 'appeal from',
            'argued', 'decided', 'filed', 'before:', 'per curiam',
            'syllabus', 'held:', 'reversed', 'affirmed', 'remanded'
        ]
        
        legal_doc_count = sum(1 for indicator in legal_doc_indicators if indicator in text_lower)
        if legal_doc_count >= 3:
            relevance_score += 0.25  # Strong legal document indicator
        elif legal_doc_count >= 1:
            relevance_score += 0.15  # Some legal document indicators
        
        # Pattern confidence boost (high-confidence patterns are more reliable)
        if pattern.confidence >= 0.95:
            relevance_score += 0.25
        elif pattern.confidence >= 0.9:
            relevance_score += 0.2
        elif pattern.confidence >= 0.85:
            relevance_score += 0.15
        elif pattern.confidence >= 0.8:
            relevance_score += 0.1
        elif pattern.confidence >= 0.75:
            relevance_score += 0.05
        
        # Critical legal pattern types get additional boost
        critical_patterns = [
            'chief_justice', 'case_citation', 'statute_citation',
            'supreme_court', 'federal_court', 'constitutional'
        ]
        
        for critical in critical_patterns:
            if critical in pattern_name_lower:
                relevance_score += 0.15
                break
        
        # Entity type priority boost
        if pattern.entity_type:
            entity_type_upper = pattern.entity_type.upper()
            priority_entity_types = [
                'CHIEF_JUSTICE', 'ASSOCIATE_JUSTICE', 'JUDGE',
                'CASE_CITATION', 'STATUTE_CITATION', 'COURT'
            ]
            if entity_type_upper in priority_entity_types:
                relevance_score += 0.1
        
        # Cap relevance score at 1.0
        return min(1.0, relevance_score)
    
    def _get_pattern_priority(self, pattern_name: str) -> int:
        """Get priority for a pattern name."""
        # Extract pattern type from name
        for pattern_type, priority in self._pattern_priorities.items():
            if pattern_type in pattern_name.lower():
                return priority
        
        return 50  # Default priority
    
    def _determine_pattern_type(self, pattern_name: str) -> str:
        """Determine pattern type from pattern name."""
        name_lower = pattern_name.lower()
        
        if 'citation' in name_lower:
            return 'citation'
        elif 'justice' in name_lower or 'judge' in name_lower:
            return 'person'
        elif 'court' in name_lower:
            return 'court'
        elif 'procedural' in name_lower:
            return 'procedural'
        elif 'constitutional' in name_lower:
            return 'constitutional'
        else:
            return 'entity'
    
    async def _extract_context(
        self,
        text: str,
        start_pos: int,
        end_pos: int,
        window_size: int
    ) -> str:
        """Extract context around a match."""
        # Calculate context boundaries
        context_start = max(0, start_pos - window_size)
        context_end = min(len(text), end_pos + window_size)
        
        # Extract context
        context = text[context_start:context_end]
        
        # Clean up context (remove excessive whitespace)
        context = ' '.join(context.split())
        
        return context
    
    async def _resolve_conflicts(
        self,
        matches: List[ExtractionMatch],
        resolution: ConflictResolution
    ) -> List[ExtractionMatch]:
        """Resolve overlapping matches using configured strategy."""
        if not matches:
            return matches
        
        # Sort matches by position
        sorted_matches = sorted(matches, key=lambda m: (m.start_pos, m.end_pos))
        
        # Group overlapping matches
        conflict_groups = []
        current_group = [sorted_matches[0]]
        
        for match in sorted_matches[1:]:
            # Check if this match overlaps with the current group
            if self._matches_overlap(current_group[-1], match, resolution.overlap_tolerance):
                current_group.append(match)
            else:
                # No overlap, start a new group
                conflict_groups.append(current_group)
                current_group = [match]
        
        # Don't forget the last group
        if current_group:
            conflict_groups.append(current_group)
        
        # Resolve conflicts in each group
        resolved_matches = []
        for group in conflict_groups:
            if len(group) == 1:
                resolved_matches.extend(group)
            else:
                resolved = await self._resolve_conflict_group(group, resolution)
                resolved_matches.extend(resolved)
        
        return resolved_matches
    
    def _matches_overlap(
        self,
        match1: ExtractionMatch,
        match2: ExtractionMatch,
        tolerance: int
    ) -> bool:
        """Check if two matches overlap within tolerance.
        
        Only consider matches as overlapping if they have significant overlap,
        not just if they're close to each other. This prevents filtering out
        legitimate adjacent entities.
        """
        # Check for actual character overlap
        overlap_start = max(match1.start_pos, match2.start_pos)
        overlap_end = min(match1.end_pos, match2.end_pos)
        
        # Only consider it an overlap if there's actual character overlap
        if overlap_end > overlap_start:
            # But also check if they're different entity types - if so, allow both
            if match1.entity_type != match2.entity_type:
                # Different entity types can coexist even if overlapping
                return False
            return True
        
        # If tolerance is set, check for near overlap (but only for same entity types)
        if tolerance > 0 and match1.entity_type == match2.entity_type:
            if abs(match1.end_pos - match2.start_pos) <= tolerance:
                return True
            if abs(match2.end_pos - match1.start_pos) <= tolerance:
                return True
        
        return False
    
    async def _resolve_conflict_group(
        self,
        group: List[ExtractionMatch],
        resolution: ConflictResolution
    ) -> List[ExtractionMatch]:
        """Resolve conflicts within a group of overlapping matches."""
        if resolution.strategy == "highest_confidence":
            # Return the match with highest confidence
            best_match = max(group, key=lambda m: m.confidence)
            return [best_match]
        
        elif resolution.strategy == "pattern_priority":
            # Return the match with highest pattern priority
            best_match = max(group, key=lambda m: self._get_pattern_priority(m.pattern_name))
            return [best_match]
        
        elif resolution.strategy == "merge":
            # Try to merge compatible matches above threshold
            high_conf_matches = [
                m for m in group if m.confidence >= resolution.merge_threshold
            ]
            
            if len(high_conf_matches) <= 1:
                return high_conf_matches
            
            # For now, return highest confidence (merging is complex)
            best_match = max(high_conf_matches, key=lambda m: m.confidence)
            return [best_match]
        
        else:
            # Default: return highest confidence
            best_match = max(group, key=lambda m: m.confidence)
            return [best_match]
    
    async def _create_objects(
        self,
        matches: List[ExtractionMatch],
        text: str,
        context: ExtractionContext
    ) -> Tuple[List[Entity], List[Citation]]:
        """Create Entity and Citation objects from extraction matches."""
        entities = []
        citations = []
        
        for match in matches:
            try:
                if match.pattern_type == 'citation':
                    citation = await self._create_citation(match, text, context)
                    if citation:
                        citations.append(citation)
                else:
                    entity = await self._create_entity(match, text, context)
                    if entity:
                        entities.append(entity)
                        
            except Exception as e:
                self.logger.error(f"Failed to create object from match: {e}")
                continue
        
        return entities, citations
    
    async def _create_entity(
        self,
        match: ExtractionMatch,
        text: str,
        context: ExtractionContext
    ) -> Optional[Entity]:
        """Create an Entity object from an extraction match."""
        try:
            # Determine entity type
            entity_type = self._map_to_entity_type(match.entity_type, match.pattern_name)
            
            # Create position
            position = TextPosition(
                start=match.start_pos,
                end=match.end_pos,
                context_start=max(0, match.start_pos - 50),
                context_end=min(len(text), match.end_pos + 50)
            )
            
            # Create attributes
            attributes = await self._create_entity_attributes(match)
            
            # Create entity
            entity = Entity(
                text=match.match_text,
                cleaned_text=match.match_text.strip(),
                entity_type=entity_type,
                entity_subtype=match.pattern_name,
                confidence_score=match.confidence,
                extraction_method=ExtractionMethod.REGEX_ONLY,
                position=position,
                attributes=attributes,
                context_snippet=match.context,
                ai_enhancements=[],
                validation_notes=[]
            )
            
            return entity
            
        except Exception as e:
            self.logger.error(f"Failed to create entity: {e}")
            return None
    
    async def _create_citation(
        self,
        match: ExtractionMatch,
        text: str,
        context: ExtractionContext
    ) -> Optional[Citation]:
        """Create a Citation object from an extraction match."""
        try:
            # Determine citation type
            citation_type = self._map_to_citation_type(match.pattern_name)
            
            # Create position
            position = TextPosition(
                start=match.start_pos,
                end=match.end_pos,
                context_start=max(0, match.start_pos - 50),
                context_end=min(len(text), match.end_pos + 50)
            )
            
            # Create citation components
            components = await self._create_citation_components(match)
            
            # Create citation
            citation = Citation(
                original_text=match.match_text,
                cleaned_citation=match.match_text.strip(),
                citation_type=citation_type,
                confidence_score=match.confidence,
                extraction_method=ExtractionMethod.REGEX_ONLY,
                position=position,
                components=components,
                bluebook_compliant=await self._check_bluebook_compliance(match),
                parallel_citations=[],
                ai_enhancements=[],
                validation_notes=[]
            )
            
            return citation
            
        except Exception as e:
            self.logger.error(f"Failed to create citation: {e}")
            return None
    
    def _map_to_entity_type(self, entity_type: Optional[str], pattern_name: str) -> EntityType:
        """Map pattern entity type to EntityType enum with comprehensive coverage for 150+ types."""
        
        # First, try direct entity_type mapping from pattern metadata
        if entity_type:
            entity_upper = entity_type.upper()
            
            # Direct enum mapping - try exact match first
            for et in EntityType:
                if et.value == entity_upper:
                    return et
            
            # Handle variations and aliases with comprehensive type mappings
            type_mappings = {
                # Courts and Judicial variations
                'CHIEF_JUSTICE': EntityType.JUDGE,
                'ASSOCIATE_JUSTICE': EntityType.JUDGE,
                'JUSTICE': EntityType.JUDGE,
                'DISTRICT_JUDGE': EntityType.JUDGE,
                'CIRCUIT_JUDGE': EntityType.JUDGE,
                'BANKRUPTCY_JUDGE': EntityType.JUDGE,
                'TAX_COURT_JUDGE': EntityType.JUDGE,
                'ADMINISTRATIVE_JUDGE': EntityType.JUDGE,
                'MAGISTRATE_JUDGE': EntityType.MAGISTRATE,
                'MAGISTRATE': EntityType.MAGISTRATE,
                'ARBITRATOR': EntityType.ARBITRATOR,
                'MEDIATOR': EntityType.MEDIATOR,
                'SPECIAL_MASTER': EntityType.SPECIAL_MASTER,
                'CLERK': EntityType.COURT_CLERK,
                'REPORTER': EntityType.COURT_REPORTER,
                
                # Specific Party type variations
                'PLAINTIFF': EntityType.PLAINTIFF,
                'DEFENDANT': EntityType.DEFENDANT,
                'APPELLANT': EntityType.APPELLANT,
                'APPELLEE': EntityType.APPELLEE,
                'PETITIONER': EntityType.PETITIONER,
                'RESPONDENT': EntityType.RESPONDENT,
                'INTERVENOR': EntityType.INTERVENOR,
                'AMICUS': EntityType.AMICUS_CURIAE,
                'AMICUS_CURIAE': EntityType.AMICUS_CURIAE,
                'THIRD_PARTY': EntityType.THIRD_PARTY,
                'CLASS_REP': EntityType.CLASS_REPRESENTATIVE,
                'CLASS_REPRESENTATIVE': EntityType.CLASS_REPRESENTATIVE,
                'PARTY': EntityType.PARTY,  # Generic party last
                
                # Legal Professional variations
                'ATTORNEY': EntityType.ATTORNEY,
                'LAWYER': EntityType.ATTORNEY,
                'COUNSEL': EntityType.ATTORNEY,
                'ATTORNEY_GENERAL': EntityType.PROSECUTOR,
                'AG': EntityType.PROSECUTOR,
                'PROSECUTOR': EntityType.PROSECUTOR,
                'DISTRICT_ATTORNEY': EntityType.PROSECUTOR,
                'DA': EntityType.PROSECUTOR,
                'US_ATTORNEY': EntityType.PROSECUTOR,
                'PUBLIC_DEFENDER': EntityType.PUBLIC_DEFENDER,
                'LEGAL_AID': EntityType.LEGAL_AID,
                'PARALEGAL': EntityType.PARALEGAL,
                'EXPERT': EntityType.EXPERT_WITNESS,
                'EXPERT_WITNESS': EntityType.EXPERT_WITNESS,
                'WITNESS': EntityType.LAY_WITNESS,
                'LAY_WITNESS': EntityType.LAY_WITNESS,
                
                # Government and Agency variations
                'GOVERNMENT': EntityType.GOVERNMENT_ENTITY,
                'GOVT': EntityType.GOVERNMENT_ENTITY,
                'GOVERNMENT_ENTITY': EntityType.GOVERNMENT_ENTITY,
                'FEDERAL_AGENCY': EntityType.FEDERAL_AGENCY,
                'FEDERAL': EntityType.FEDERAL_AGENCY,
                'STATE_AGENCY': EntityType.STATE_AGENCY,
                'LOCAL_AGENCY': EntityType.LOCAL_AGENCY,
                'MUNICIPAL': EntityType.LOCAL_AGENCY,
                'AGENCY': EntityType.FEDERAL_AGENCY,
                'DEPARTMENT': EntityType.FEDERAL_AGENCY,
                'BUREAU': EntityType.FEDERAL_AGENCY,
                'COMMISSION': EntityType.REGULATORY_BODY,
                'BOARD': EntityType.REGULATORY_BODY,
                'REGULATORY': EntityType.REGULATORY_BODY,
                'LEGISLATURE': EntityType.LEGISLATIVE_BODY,
                'CONGRESS': EntityType.LEGISLATIVE_BODY,
                'EXECUTIVE': EntityType.EXECUTIVE_OFFICE,
                
                # Date and Time variations
                'DATE': EntityType.DATE,
                'FILING_DATE': EntityType.FILING_DATE,
                'SERVICE_DATE': EntityType.SERVICE_DATE,
                'HEARING_DATE': EntityType.HEARING_DATE,
                'TRIAL_DATE': EntityType.TRIAL_DATE,
                'DECISION_DATE': EntityType.DECISION_DATE,
                'DEADLINE': EntityType.DEADLINE,
                
                # Financial variations
                'MONEY': EntityType.MONETARY_AMOUNT,
                'MONETARY': EntityType.MONETARY_AMOUNT,
                'AMOUNT': EntityType.MONETARY_AMOUNT,
                'DAMAGES': EntityType.DAMAGES,
                'COMPENSATORY': EntityType.COMPENSATORY_DAMAGES,
                'PUNITIVE': EntityType.PUNITIVE_DAMAGES,
                'FEE': EntityType.FEE,
                'FINE': EntityType.FINE,
                'PENALTY': EntityType.PENALTY,
                'AWARD': EntityType.AWARD,
                'COST': EntityType.COST,
                'BOND': EntityType.BOND,
                
                # Legal authority variations
                'LAW': EntityType.STATUTE,
                'ACT': EntityType.STATUTE,
                'CODE': EntityType.STATUTE,
                'REGULATION': EntityType.REGULATION,
                'RULE': EntityType.PROCEDURAL_RULE,
                'ORDINANCE': EntityType.ORDINANCE,
                'TREATY': EntityType.TREATY,
            }
            
            if entity_upper in type_mappings:
                return type_mappings[entity_upper]
        
        # Fallback to pattern name analysis with comprehensive keyword mapping
        pattern_lower = pattern_name.lower()
        
        # Comprehensive pattern name keyword mapping (order matters - specific before generic)
        keyword_mappings = [
            # Courts and Judicial (check specific types first)
            (['magistrate'], EntityType.MAGISTRATE),
            (['arbitrator'], EntityType.ARBITRATOR),
            (['mediator'], EntityType.MEDIATOR),
            (['special_master', 'master'], EntityType.SPECIAL_MASTER),
            (['court_clerk', 'clerk'], EntityType.COURT_CLERK),
            (['court_reporter', 'reporter'], EntityType.COURT_REPORTER),
            (['judge', 'justice'], EntityType.JUDGE),
            (['court'], EntityType.COURT),
            
            # Specific party types (check before generic PARTY)
            (['plaintiff'], EntityType.PLAINTIFF),
            (['defendant'], EntityType.DEFENDANT),
            (['appellant'], EntityType.APPELLANT),
            (['appellee'], EntityType.APPELLEE),
            (['petitioner'], EntityType.PETITIONER),
            (['respondent'], EntityType.RESPONDENT),
            (['intervenor'], EntityType.INTERVENOR),
            (['amicus'], EntityType.AMICUS_CURIAE),
            (['third_party'], EntityType.THIRD_PARTY),
            (['class_representative'], EntityType.CLASS_REPRESENTATIVE),
            (['party', 'parties'], EntityType.PARTY),  # Generic last
            
            # Legal professionals
            (['prosecutor', 'district_attorney', 'attorney_general'], EntityType.PROSECUTOR),
            (['public_defender'], EntityType.PUBLIC_DEFENDER),
            (['legal_aid'], EntityType.LEGAL_AID),
            (['paralegal'], EntityType.PARALEGAL),
            (['expert_witness'], EntityType.EXPERT_WITNESS),
            (['witness'], EntityType.LAY_WITNESS),
            (['attorney', 'lawyer', 'counsel'], EntityType.ATTORNEY),
            (['law_firm', 'firm'], EntityType.LAW_FIRM),
            
            # Government
            (['federal_agency', 'federal'], EntityType.FEDERAL_AGENCY),
            (['state_agency'], EntityType.STATE_AGENCY),
            (['local_agency', 'municipal'], EntityType.LOCAL_AGENCY),
            (['regulatory', 'regulator', 'commission', 'board'], EntityType.REGULATORY_BODY),
            (['legislative', 'legislature', 'congress'], EntityType.LEGISLATIVE_BODY),
            (['executive'], EntityType.EXECUTIVE_OFFICE),
            (['government', 'agency', 'department'], EntityType.GOVERNMENT_ENTITY),
            
            # Documents
            (['motion'], EntityType.MOTION),
            (['brief'], EntityType.BRIEF),
            (['complaint'], EntityType.COMPLAINT),
            (['answer'], EntityType.ANSWER),
            (['discovery'], EntityType.DISCOVERY_DOCUMENT),
            (['deposition'], EntityType.DEPOSITION),
            (['interrogatory'], EntityType.INTERROGATORY),
            (['affidavit'], EntityType.AFFIDAVIT),
            (['declaration'], EntityType.DECLARATION),
            (['exhibit'], EntityType.EXHIBIT),
            (['transcript'], EntityType.TRANSCRIPT),
            (['order'], EntityType.ORDER),
            (['judgment'], EntityType.JUDGMENT),
            (['verdict'], EntityType.VERDICT),
            (['settlement'], EntityType.SETTLEMENT),
            (['contract'], EntityType.CONTRACT),
            (['agreement'], EntityType.AGREEMENT),
            (['document'], EntityType.DOCUMENT),
            
            # Dates (specific before generic)
            (['filing_date'], EntityType.FILING_DATE),
            (['service_date'], EntityType.SERVICE_DATE),
            (['hearing_date'], EntityType.HEARING_DATE),
            (['trial_date'], EntityType.TRIAL_DATE),
            (['decision_date'], EntityType.DECISION_DATE),
            (['deadline'], EntityType.DEADLINE),
            (['statute_of_limitations', 'limitation'], EntityType.STATUTE_OF_LIMITATIONS),
            (['date'], EntityType.DATE),
            
            # Financial (specific before generic)
            (['compensatory'], EntityType.COMPENSATORY_DAMAGES),
            (['punitive'], EntityType.PUNITIVE_DAMAGES),
            (['statutory_damage'], EntityType.STATUTORY_DAMAGES),
            (['liquidated'], EntityType.LIQUIDATED_DAMAGES),
            (['nominal'], EntityType.NOMINAL_DAMAGES),
            (['damage'], EntityType.DAMAGES),
            (['fee'], EntityType.FEE),
            (['fine'], EntityType.FINE),
            (['penalty'], EntityType.PENALTY),
            (['award'], EntityType.AWARD),
            (['cost'], EntityType.COST),
            (['bond'], EntityType.BOND),
            (['monetary', 'money', 'amount', 'dollar'], EntityType.MONETARY_AMOUNT),
            
            # Jurisdictions
            (['federal_jurisdiction'], EntityType.FEDERAL_JURISDICTION),
            (['state_jurisdiction'], EntityType.STATE_JURISDICTION),
            (['venue'], EntityType.VENUE),
            (['forum'], EntityType.FORUM),
            (['district'], EntityType.DISTRICT),
            (['circuit'], EntityType.CIRCUIT),
            (['jurisdiction'], EntityType.JURISDICTION),
            
            # Legal authority
            (['statute', 'statutory'], EntityType.STATUTE),
            (['regulation', 'regulatory'], EntityType.REGULATION),
            (['case_law', 'precedent'], EntityType.CASE_LAW),
            (['constitutional'], EntityType.CONSTITUTIONAL_PROVISION),
            (['ordinance'], EntityType.ORDINANCE),
            (['executive_order'], EntityType.EXECUTIVE_ORDER),
            (['treaty'], EntityType.TREATY),
            
            # Procedural
            (['civil_procedure'], EntityType.CIVIL_PROCEDURE),
            (['criminal_procedure'], EntityType.CRIMINAL_PROCEDURE),
            (['appellate_procedure'], EntityType.APPELLATE_PROCEDURE),
            (['local_rule'], EntityType.LOCAL_RULE),
            (['standing_order'], EntityType.STANDING_ORDER),
            (['procedure', 'procedural'], EntityType.PROCEDURAL_RULE),
            
            # Evidence
            (['evidence'], EntityType.EVIDENCE_TYPE),
            
            # Claims and causes
            (['cause_of_action'], EntityType.CAUSE_OF_ACTION),
            (['counterclaim'], EntityType.COUNTERCLAIM),
            (['cross_claim'], EntityType.CROSS_CLAIM),
            (['affirmative_defense'], EntityType.AFFIRMATIVE_DEFENSE),
            (['defense'], EntityType.DEFENSE),
            (['claim'], EntityType.CLAIM),
            (['charge'], EntityType.CHARGE),
            
            # Remedies
            (['injunction'], EntityType.INJUNCTION),
            (['relief'], EntityType.RELIEF_REQUESTED),
            
            # Organizations
            (['corporation', 'corp', 'inc'], EntityType.CORPORATION),
            (['llc'], EntityType.LLC),
            (['partnership'], EntityType.PARTNERSHIP),
            (['nonprofit'], EntityType.NONPROFIT),
            (['trust'], EntityType.TRUST),
            (['estate'], EntityType.ESTATE),
            (['union'], EntityType.UNION),
            (['association'], EntityType.ASSOCIATION),
            
            # Case information
            (['case_number'], EntityType.CASE_NUMBER),
            (['docket'], EntityType.DOCKET_NUMBER),
            (['caption'], EntityType.CASE_CAPTION),
            
            # Criminal law
            (['felony'], EntityType.FELONY),
            (['misdemeanor'], EntityType.MISDEMEANOR),
            (['offense', 'crime'], EntityType.OFFENSE),
            (['sentence'], EntityType.SENTENCE),
            (['probation'], EntityType.PROBATION),
            (['parole'], EntityType.PAROLE),
            
            # IP
            (['patent'], EntityType.PATENT),
            (['trademark'], EntityType.TRADEMARK),
            (['copyright'], EntityType.COPYRIGHT),
            (['trade_secret'], EntityType.TRADE_SECRET),
            
            # Contact
            (['address'], EntityType.ADDRESS),
            (['email'], EntityType.EMAIL),
            (['phone'], EntityType.PHONE_NUMBER),
            (['bar_number'], EntityType.BAR_NUMBER),
            
            # Legal concepts (most generic - check last)
            (['doctrine'], EntityType.LEGAL_DOCTRINE),
            (['principle'], EntityType.PRINCIPLE),
            (['theory'], EntityType.LEGAL_THEORY),
            (['term'], EntityType.LEGAL_TERM),
            (['citation'], EntityType.LEGAL_CITATION),
        ]
        
        # Check each keyword mapping
        for keywords, entity_type in keyword_mappings:
            if any(keyword in pattern_lower for keyword in keywords):
                return entity_type
        
        # Ultimate fallback - but this should rarely happen with 150+ types
        return EntityType.LEGAL_CONCEPT
    
    def _map_to_citation_type(self, pattern_name: str) -> CitationType:
        """Map pattern name to CitationType enum with comprehensive coverage for 90+ types."""
        name_lower = pattern_name.lower()
        
        # Comprehensive citation keyword mapping (check specific before generic)
        citation_mappings = [
            # Case citations (most specific first)
            (['supreme_court'], CitationType.SUPREME_COURT_CITATION),
            (['appellate_court', 'appeals_court', 'circuit_court'], CitationType.APPELLATE_COURT_CITATION),
            (['district_court'], CitationType.DISTRICT_COURT_CITATION),
            (['bankruptcy_court'], CitationType.BANKRUPTCY_COURT_CITATION),
            (['tax_court'], CitationType.TAX_COURT_CITATION),
            (['military_court'], CitationType.MILITARY_COURT_CITATION),
            (['administrative_court'], CitationType.ADMINISTRATIVE_COURT_CITATION),
            (['federal_case'], CitationType.FEDERAL_CASE_CITATION),
            (['state_case'], CitationType.STATE_CASE_CITATION),
            (['unpublished', 'unreported'], CitationType.UNPUBLISHED_CASE_CITATION),
            (['parallel'], CitationType.PARALLEL_CITATION),
            (['short_form', 'short_cite'], CitationType.SHORT_FORM_CITATION),
            (['case'], CitationType.CASE_CITATION),  # Generic case last
            
            # Statute citations
            (['u.s.c.', 'usc', 'united_states_code'], CitationType.USC_CITATION),
            (['u.s.c.a.', 'usca'], CitationType.USCA_CITATION),
            (['state_code', 'state_statute'], CitationType.STATE_CODE_CITATION),
            (['session_law'], CitationType.SESSION_LAW_CITATION),
            (['public_law', 'pub_l'], CitationType.PUBLIC_LAW_CITATION),
            (['private_law', 'priv_l'], CitationType.PRIVATE_LAW_CITATION),
            (['federal_statute'], CitationType.FEDERAL_STATUTE_CITATION),
            (['state_statute'], CitationType.STATE_STATUTE_CITATION),
            (['statute', 'statutory'], CitationType.STATUTE_CITATION),
            
            # Regulatory citations
            (['c.f.r.', 'cfr', 'code_federal'], CitationType.CFR_CITATION),
            (['federal_register', 'fed_reg', 'fr'], CitationType.FEDERAL_REGISTER_CITATION),
            (['state_regulation', 'state_reg'], CitationType.STATE_REGULATION_CITATION),
            (['administrative_code', 'admin_code'], CitationType.ADMINISTRATIVE_CODE_CITATION),
            (['executive_order', 'exec_order', 'eo'], CitationType.EXECUTIVE_ORDER_CITATION),
            (['agency_decision', 'agency_ruling'], CitationType.AGENCY_DECISION_CITATION),
            (['administrative_ruling', 'admin_ruling'], CitationType.ADMINISTRATIVE_RULING_CITATION),
            (['regulation', 'regulatory'], CitationType.REGULATION_CITATION),
            (['administrative'], CitationType.ADMINISTRATIVE_CITATION),
            
            # Constitutional citations
            (['u.s._const', 'us_constitution', 'federal_constitution'], CitationType.US_CONSTITUTION_CITATION),
            (['state_constitution', 'state_const'], CitationType.STATE_CONSTITUTION_CITATION),
            (['amendment', 'amend'], CitationType.AMENDMENT_CITATION),
            (['constitutional', 'const'], CitationType.CONSTITUTIONAL_CITATION),
            
            # Court rules
            (['frcp', 'fed_r_civ_p', 'federal_rules_civil'], CitationType.FRCP_CITATION),
            (['frcrp', 'fed_r_crim_p', 'federal_rules_criminal'], CitationType.FRCRP_CITATION),
            (['fre', 'fed_r_evid', 'federal_rules_evidence'], CitationType.FRE_CITATION),
            (['frap', 'fed_r_app_p', 'federal_rules_appellate'], CitationType.FRAP_CITATION),
            (['frbp', 'fed_r_bankr_p', 'federal_rules_bankruptcy'], CitationType.FRBP_CITATION),
            (['local_rule', 'local_rules'], CitationType.LOCAL_RULE_CITATION),
            (['standing_order'], CitationType.STANDING_ORDER_CITATION),
            (['court_rule'], CitationType.COURT_RULE_CITATION),
            
            # Secondary sources
            (['law_review'], CitationType.LAW_REVIEW_CITATION),
            (['law_journal'], CitationType.LAW_JOURNAL_CITATION),
            (['treatise'], CitationType.TREATISE_CITATION),
            (['hornbook'], CitationType.HORNBOOK_CITATION),
            (['practice_guide'], CitationType.PRACTICE_GUIDE_CITATION),
            (['legal_encyclopedia'], CitationType.LEGAL_ENCYCLOPEDIA_CITATION),
            (['alr', 'a.l.r.', 'american_law_reports'], CitationType.ALR_CITATION),
            (['restatement'], CitationType.RESTATEMENT_CITATION),
            (['uniform_law', 'uniform_act'], CitationType.UNIFORM_LAW_CITATION),
            (['model_code', 'model_rule'], CitationType.MODEL_CODE_CITATION),
            (['book'], CitationType.BOOK_CITATION),
            
            # News and media
            (['newspaper', 'news_article'], CitationType.NEWSPAPER_CITATION),
            (['magazine'], CitationType.MAGAZINE_CITATION),
            (['press_release'], CitationType.PRESS_RELEASE_CITATION),
            (['news_wire', 'wire_service'], CitationType.NEWS_WIRE_CITATION),
            
            # Electronic sources
            (['westlaw', 'wl'], CitationType.WESTLAW_CITATION),
            (['lexis', 'lexisnexis'], CitationType.LEXIS_CITATION),
            (['bloomberg_law', 'bloomberg'], CitationType.BLOOMBERG_LAW_CITATION),
            (['blog'], CitationType.BLOG_CITATION),
            (['social_media', 'twitter', 'facebook'], CitationType.SOCIAL_MEDIA_CITATION),
            (['database'], CitationType.DATABASE_CITATION),
            (['web', 'website', 'url', 'http'], CitationType.WEB_CITATION),
            
            # Legislative materials
            (['congressional_record', 'cong_rec'], CitationType.CONGRESSIONAL_RECORD_CITATION),
            (['house_report', 'h.r._rep'], CitationType.HOUSE_REPORT_CITATION),
            (['senate_report', 's._rep'], CitationType.SENATE_REPORT_CITATION),
            (['committee_report'], CitationType.COMMITTEE_REPORT_CITATION),
            (['hearing_transcript', 'hearing'], CitationType.HEARING_TRANSCRIPT_CITATION),
            (['bill', 'h.r.', 's.'], CitationType.BILL_CITATION),
            (['resolution'], CitationType.RESOLUTION_CITATION),
            
            # International sources
            (['treaty'], CitationType.TREATY_CITATION),
            (['international_agreement'], CitationType.INTERNATIONAL_AGREEMENT_CITATION),
            (['foreign_law'], CitationType.FOREIGN_LAW_CITATION),
            (['un_document', 'united_nations'], CitationType.UN_DOCUMENT_CITATION),
            (['icj', 'international_court_justice'], CitationType.ICJ_CITATION),
            (['international_court'], CitationType.INTERNATIONAL_COURT_CITATION),
            
            # Practice materials
            (['brief'], CitationType.BRIEF_CITATION),
            (['motion'], CitationType.MOTION_CITATION),
            (['memorandum', 'memo'], CitationType.MEMORANDUM_CITATION),
            (['opinion_letter'], CitationType.OPINION_LETTER_CITATION),
            
            # Record citations
            (['transcript'], CitationType.TRANSCRIPT_CITATION),
            (['deposition', 'depo'], CitationType.DEPOSITION_CITATION),
            (['trial_record'], CitationType.TRIAL_RECORD_CITATION),
            (['appellate_record'], CitationType.APPELLATE_RECORD_CITATION),
            (['exhibit'], CitationType.EXHIBIT_CITATION),
            
            # Specialized citations
            (['patent'], CitationType.PATENT_CITATION),
            (['trademark'], CitationType.TRADEMARK_CITATION),
            (['copyright'], CitationType.COPYRIGHT_CITATION),
            (['sec_filing', 'securities'], CitationType.SEC_FILING_CITATION),
            (['irs', 'internal_revenue'], CitationType.IRS_CITATION),
            
            # Cross-references
            (['supra'], CitationType.SUPRA_CITATION),
            (['infra'], CitationType.INFRA_CITATION),
            (['id.', ' id ', 'idem'], CitationType.ID_CITATION),
            (['ibid'], CitationType.IBID_CITATION),
            
            # Parenthetical citations
            (['explanatory_parenthetical'], CitationType.EXPLANATORY_PARENTHETICAL),
            (['weight_of_authority'], CitationType.WEIGHT_OF_AUTHORITY_PARENTHETICAL),
            (['parenthetical'], CitationType.PARENTHETICAL_CITATION),
            
            # Signal citations
            (['see_also'], CitationType.SEE_ALSO_CITATION),
            (['see_generally'], CitationType.SEE_GENERALLY_CITATION),
            (['cf.', ' cf '], CitationType.CF_CITATION),
            (['compare'], CitationType.COMPARE_CITATION),
            (['contra'], CitationType.CONTRA_CITATION),
            (['but_see'], CitationType.BUT_SEE_CITATION),
            (['accord'], CitationType.ACCORD_CITATION),
            (['see'], CitationType.SEE_CITATION),
            
            # Pinpoint citations
            (['paragraph', 'para'], CitationType.PARAGRAPH_CITATION),
            (['section', 'sec'], CitationType.SECTION_CITATION),
            (['footnote', 'fn'], CitationType.FOOTNOTE_CITATION),
            (['line'], CitationType.LINE_CITATION),
            (['page', 'pg'], CitationType.PAGE_CITATION),
        ]
        
        # Check each mapping
        for keywords, citation_type in citation_mappings:
            if any(keyword in name_lower for keyword in keywords):
                return citation_type
        
        # Default fallback to case citation
        return CitationType.CASE_CITATION
    
    async def _create_entity_attributes(self, match: ExtractionMatch) -> EntityAttributes:
        """Create EntityAttributes from match groups."""
        attributes = EntityAttributes()
        
        # Map common groups to attributes
        if 'name' in match.match_groups:
            if 'justice' in match.pattern_name.lower():
                attributes.judge_title = match.match_groups.get('justice_title', 'Justice')
            elif 'attorney' in match.pattern_name.lower():
                attributes.attorney_name = match.match_groups['name']
            elif 'party' in match.pattern_name.lower():
                attributes.party_name = match.match_groups['name']
        
        if 'court_name' in match.match_groups:
            attributes.court_name = match.match_groups['court_name']
        
        if 'jurisdiction' in match.match_groups:
            attributes.jurisdiction = match.match_groups['jurisdiction']
        
        # Store additional attributes
        for key, value in match.match_groups.items():
            if value is not None:
                attributes.additional_attributes[key] = value
        
        return attributes
    
    async def _create_citation_components(self, match: ExtractionMatch) -> CitationComponents:
        """Create CitationComponents from match groups."""
        components = CitationComponents()
        
        # Map groups to citation components
        group_mapping = {
            'case_name': 'case_name',
            'volume': 'volume',
            'reporter': 'reporter',
            'page': 'page',
            'pinpoint': 'pincite',
            'court': 'court',
            'year': 'year',
            'title': 'title',
            'code': 'code',
            'section': 'section',
            'subsection': 'subsection',
            'author': 'author',
            'article_title': 'article_title',
            'journal': 'journal',
            'url': 'url'
        }
        
        for group_key, component_key in group_mapping.items():
            if group_key in match.match_groups and match.match_groups[group_key]:
                setattr(components, component_key, match.match_groups[group_key])
        
        # Store additional components
        for key, value in match.match_groups.items():
            if value is not None and key not in group_mapping:
                components.additional_components[key] = value
        
        return components
    
    async def _check_bluebook_compliance(self, match: ExtractionMatch) -> bool:
        """Check if citation meets basic Bluebook compliance."""
        # Basic compliance checks based on pattern
        if 'bluebook_compliance' in match.components:
            return match.components['bluebook_compliance'].lower() in ['true', 'yes', '22nd_edition']
        
        # Pattern-based heuristics
        if 'case' in match.pattern_name.lower():
            # Case citations should have volume, reporter, page
            required_components = ['volume', 'reporter', 'page']
            return all(comp in match.match_groups for comp in required_components)
        
        return True  # Default to compliant
    
    def _update_metrics(
        self,
        start_time: float,
        raw_matches_count: int,
        entities_count: int,
        citations_count: int
    ) -> None:
        """Update performance metrics."""
        processing_time = time.time() - start_time
        
        self._performance_metrics["total_extractions"] += 1
        self._performance_metrics["total_matches"] += raw_matches_count
        self._performance_metrics["total_processing_time"] += processing_time
        self._performance_metrics["average_processing_time"] = (
            self._performance_metrics["total_processing_time"] / 
            self._performance_metrics["total_extractions"]
        )
        
        # Update entity type counts
        self._performance_metrics["entity_type_counts"]["entities"] += entities_count
        self._performance_metrics["entity_type_counts"]["citations"] += citations_count
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self._performance_metrics.copy()
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get pattern statistics from the loader."""
        return self.pattern_loader.get_pattern_statistics()
    
    async def reload_patterns(self) -> None:
        """Reload all patterns from disk."""
        self.logger.info("Reloading patterns...")
        self.pattern_loader.reload_patterns()
        self.logger.info(f"Reloaded {len(self.pattern_loader.get_pattern_names())} patterns")
    
    async def validate_pattern_dependencies(self) -> Dict[str, List[str]]:
        """Validate pattern dependencies."""
        return self.pattern_loader.validate_pattern_dependencies()
    
    def __repr__(self) -> str:
        """String representation of RegexEngine."""
        return (
            f"RegexEngine("
            f"patterns={len(self.pattern_loader.get_pattern_names())}, "
            f"extractions={self._performance_metrics['total_extractions']}, "
            f"avg_time={self._performance_metrics['average_processing_time']:.3f}s"
            f")"
        )