"""
Pattern Loading Utility for Entity Extraction Service.

Comprehensive pattern loader that handles YAML pattern files, validation,
compilation, caching, and retrieval with sophisticated error handling.
"""

import re
import time
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from functools import lru_cache
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import threading
from collections import defaultdict

# Disabled - modules don't exist yet
# from .pattern_validator import PatternValidator
# from .pattern_compiler import PatternCompiler


@dataclass
class PatternMetadata:
    """Metadata for a loaded pattern."""
    pattern_type: str
    jurisdiction: str
    court_level: Optional[str] = None
    bluebook_compliance: Optional[str] = None
    pattern_version: str = "1.0"
    created_date: Optional[str] = None
    last_updated: Optional[str] = None
    description: Optional[str] = None
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    load_time: Optional[float] = None


@dataclass
class CompiledPattern:
    """A compiled pattern with metadata and compiled regex."""
    name: str
    pattern: str
    compiled_regex: re.Pattern
    confidence: float
    components: Dict[str, str]
    examples: List[str]
    metadata: PatternMetadata
    entity_type: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    validation_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternGroup:
    """A group of related patterns."""
    group_name: str
    patterns: Dict[str, CompiledPattern]
    metadata: PatternMetadata
    dependencies: List[str] = field(default_factory=list)
    confidence_threshold: float = 0.7


class PatternLoadError(Exception):
    """Custom exception for pattern loading errors."""


class PatternLoader:
    """
    Comprehensive pattern loader for YAML-based entity extraction patterns.
    
    Features:
    - Loads all YAML files from patterns directory
    - Validates pattern syntax and metadata
    - Compiles regex patterns with optimization
    - Provides caching and pattern retrieval methods
    - Supports pattern confidence scoring
    - Handles pattern dependencies and inheritance
    - Thread-safe operations
    - Performance monitoring
    """
    
    def __init__(
        self,
        patterns_dir: Optional[str] = None,
        enable_caching: bool = True,
        cache_size: int = 1000,
        enable_validation: bool = True,
        enable_compilation: bool = True,
        enable_threading: bool = True,
        max_workers: int = 4
    ):
        """
        Initialize PatternLoader.
        
        Args:
            patterns_dir: Directory containing pattern files
            enable_caching: Enable pattern caching
            cache_size: Maximum cache size
            enable_validation: Enable pattern validation
            enable_compilation: Enable pattern compilation
            enable_threading: Enable threaded loading
            max_workers: Maximum worker threads
        """
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        if patterns_dir is None:
            # Default to patterns directory relative to this file
            current_dir = Path(__file__).parent.parent
            self.patterns_dir = current_dir / "patterns"
        else:
            self.patterns_dir = Path(patterns_dir)
            
        self.enable_caching = enable_caching
        self.cache_size = cache_size
        self.enable_validation = enable_validation
        self.enable_compilation = enable_compilation
        self.enable_threading = enable_threading
        self.max_workers = max_workers
        
        # Initialize components
        # Disabled - modules don't exist yet
        self.validator = None  # PatternValidator() if enable_validation else None
        self.compiler = None  # PatternCompiler(cache_size=cache_size) if enable_compilation else None
        
        # Storage
        self._patterns: Dict[str, PatternGroup] = {}
        self._pattern_index: Dict[str, Tuple[str, str]] = {}  # pattern_name -> (group_name, pattern_key)
        self._entity_type_index: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self._mapped_entity_type_index: Dict[str, List[Tuple[str, str]]] = defaultdict(list)  # Mapped types
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._file_hashes: Dict[str, str] = {}
        self._aggregated_examples: Dict[str, List[str]] = {}  # entity_type -> aggregated examples from patterns
        
        # Load entity type mappings
        self._entity_type_mappings = self._load_entity_type_mappings()
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Metrics
        self._load_metrics = {
            "files_loaded": 0,
            "patterns_loaded": 0,
            "load_errors": 0,
            "last_load_time": None,
            "total_load_time": 0.0
        }
        
        # Load patterns on initialization
        self.load_all_patterns()
    
    def _load_entity_type_mappings(self) -> Dict[str, str]:
        """Load entity type mappings from configuration file."""
        mappings = {}
        config_path = Path(__file__).parent.parent / "config" / "entity_type_mappings.json"
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    mappings = config.get("entity_type_mappings", {})
                    self.logger.info(f"Loaded {len(mappings)} entity type mappings from {config_path}")
            else:
                self.logger.warning(f"Entity type mappings file not found: {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to load entity type mappings: {e}")
        
        return mappings
    
    def _map_entity_type(self, entity_type: str) -> str:
        """Map a pattern entity type to the canonical EntityType enum value."""
        if not entity_type:
            return entity_type
        
        # Check if mapping exists
        mapped = self._entity_type_mappings.get(entity_type, entity_type)
        
        # Log mapping if different
        if mapped != entity_type:
            self.logger.debug(f"Mapped entity type: {entity_type} -> {mapped}")
        
        return mapped
    
    def load_all_patterns(self) -> None:
        """Load all pattern files from the patterns directory."""
        start_time = time.time()
        
        try:
            if not self.patterns_dir.exists():
                self.logger.warning(f"Patterns directory does not exist: {self.patterns_dir}")
                return
            
            self.logger.info(f"Loading patterns from: {self.patterns_dir}")
            
            # Find all YAML files
            yaml_files = list(self.patterns_dir.rglob("*.yaml")) + list(self.patterns_dir.rglob("*.yml"))
            
            if not yaml_files:
                self.logger.warning(f"No YAML pattern files found in: {self.patterns_dir}")
                return
            
            self.logger.info(f"Found {len(yaml_files)} pattern files")
            
            # Load files
            if self.enable_threading and len(yaml_files) > 1:
                self._load_patterns_threaded(yaml_files)
            else:
                self._load_patterns_sequential(yaml_files)
            
            # Build indexes
            self._build_indexes()
            
            # Aggregate examples from loaded patterns
            self._aggregate_examples_from_patterns()

            # Calculate metrics
            end_time = time.time()
            load_time = end_time - start_time
            
            with self._lock:
                self._load_metrics["last_load_time"] = end_time
                self._load_metrics["total_load_time"] += load_time
            
            self.logger.info(
                f"Pattern loading completed in {load_time:.2f}s. "
                f"Loaded {self._load_metrics['patterns_loaded']} patterns "
                f"from {self._load_metrics['files_loaded']} files "
                f"with {self._load_metrics['load_errors']} errors"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load patterns: {e}")
            raise PatternLoadError(f"Pattern loading failed: {e}")
    
    def _load_patterns_threaded(self, yaml_files: List[Path]) -> None:
        """Load patterns using multiple threads."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all files
            future_to_file = {
                executor.submit(self._load_pattern_file, file_path): file_path
                for file_path in yaml_files
            }
            
            # Process results
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    pattern_group = future.result()
                    if pattern_group:
                        with self._lock:
                            self._patterns[pattern_group.group_name] = pattern_group
                            self._load_metrics["files_loaded"] += 1
                            self._load_metrics["patterns_loaded"] += len(pattern_group.patterns)
                except Exception as e:
                    self.logger.error(f"Error loading pattern file {file_path}: {e}")
                    with self._lock:
                        self._load_metrics["load_errors"] += 1
    
    def _load_patterns_sequential(self, yaml_files: List[Path]) -> None:
        """Load patterns sequentially."""
        for file_path in yaml_files:
            try:
                pattern_group = self._load_pattern_file(file_path)
                if pattern_group:
                    self._patterns[pattern_group.group_name] = pattern_group
                    self._load_metrics["files_loaded"] += 1
                    self._load_metrics["patterns_loaded"] += len(pattern_group.patterns)
            except Exception as e:
                self.logger.error(f"Error loading pattern file {file_path}: {e}")
                self._load_metrics["load_errors"] += 1
    
    def _load_pattern_file(self, file_path: Path) -> Optional[PatternGroup]:
        """
        Load a single pattern file.

        Args:
            file_path: Path to the pattern file

        Returns:
            Optional[PatternGroup]: Loaded pattern group or None if failed
        """
        try:
            # Calculate file hash
            file_hash = self._calculate_file_hash(file_path)

            # Check if file has changed
            if str(file_path) in self._file_hashes:
                if self._file_hashes[str(file_path)] == file_hash:
                    self.logger.debug(f"File unchanged, skipping: {file_path}")
                    return None

            # Load YAML content with error handling
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
            except yaml.YAMLError as e:
                self.logger.warning(f"YAML parsing error in {file_path}: {e}")
                return None
            except Exception as e:
                self.logger.warning(f"Error reading file {file_path}: {e}")
                return None

            if not content:
                self.logger.debug(f"Empty pattern file: {file_path}")
                return None

            if not isinstance(content, dict):
                self.logger.warning(f"Invalid YAML structure in {file_path}: expected dict, got {type(content)}")
                return None
            
            # Extract metadata
            metadata = self._extract_metadata(content, file_path, file_hash)
            
            # Validate if enabled
            if self.validator:
                validation_result = self.validator.validate_pattern_file(content, str(file_path))
                if not validation_result.is_valid:
                    self.logger.error(f"Pattern validation failed for {file_path}: {validation_result.errors}")
                    return None
            
            # Create pattern group
            group_name = self._generate_group_name(file_path, metadata)

            # Extract dependencies safely
            dependencies = []
            deps_data = content.get('dependencies', {})
            if isinstance(deps_data, dict):
                dependencies = deps_data.get('requires', [])
            elif isinstance(deps_data, list):
                dependencies = deps_data

            pattern_group = PatternGroup(
                group_name=group_name,
                patterns={},
                metadata=metadata,
                dependencies=dependencies
            )
            
            # Load individual patterns
            self._load_patterns_from_content(content, pattern_group, metadata)
            
            # Store file hash
            self._file_hashes[str(file_path)] = file_hash
            
            self.logger.debug(f"Loaded pattern group '{group_name}' with {len(pattern_group.patterns)} patterns")
            
            return pattern_group
            
        except Exception as e:
            import traceback
            self.logger.error(f"Failed to load pattern file {file_path}: {e}")
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"Traceback:\n{traceback.format_exc()}")
            return None
    
    def _extract_metadata(
        self,
        content: Dict[str, Any],
        file_path: Path,
        file_hash: str
    ) -> PatternMetadata:
        """Extract metadata from pattern file content."""
        metadata_dict = content.get('metadata', {})

        # Handle case where metadata might not be a dict
        if not isinstance(metadata_dict, dict):
            self.logger.warning(f"Invalid metadata format in {file_path}: expected dict, got {type(metadata_dict)}")
            metadata_dict = {}

        return PatternMetadata(
            pattern_type=metadata_dict.get('pattern_type', 'unknown'),
            jurisdiction=metadata_dict.get('jurisdiction', 'unknown'),
            court_level=metadata_dict.get('court_level'),
            bluebook_compliance=metadata_dict.get('bluebook_compliance'),
            pattern_version=metadata_dict.get('pattern_version', '1.0'),
            created_date=metadata_dict.get('created_date'),
            last_updated=metadata_dict.get('last_updated'),
            description=metadata_dict.get('description'),
            file_path=str(file_path),
            file_hash=file_hash,
            load_time=time.time()
        )
    
    def _load_patterns_from_content(
        self,
        content: Dict[str, Any],
        pattern_group: PatternGroup,
        metadata: PatternMetadata
    ) -> None:
        """Load individual patterns from file content."""
        # Get entity types - handle both list and dict formats
        entity_types = {}
        entity_types_raw = content.get('entity_types', [])

        # Handle different formats for entity_types
        if isinstance(entity_types_raw, list):
            # If it's a list of dicts with 'name' field
            for et in entity_types_raw:
                if isinstance(et, dict) and 'name' in et:
                    entity_types[et['name']] = et
        elif isinstance(entity_types_raw, dict):
            # If it's already a dict, use it directly
            entity_types = entity_types_raw
        else:
            # Log unexpected format
            if entity_types_raw:
                self.logger.debug(f"Unexpected entity_types format: {type(entity_types_raw)}")
        
        # Check if content has a flat 'patterns' list (new format)
        if 'patterns' in content and isinstance(content['patterns'], list):
            # Handle flat pattern list format
            for idx, pattern_data in enumerate(content['patterns']):
                if not isinstance(pattern_data, dict):
                    continue

                try:
                    # Use pattern name or generate one
                    pattern_name = pattern_data.get('name', f'pattern_{idx}')

                    # Compile the pattern
                    compiled_pattern = self._compile_pattern(
                        'patterns',  # Use 'patterns' as section name for flat structure
                        pattern_name,
                        pattern_data,
                        metadata,
                        entity_types
                    )

                    if compiled_pattern:
                        pattern_group.patterns[pattern_name] = compiled_pattern

                except Exception as e:
                    self.logger.error(f"Failed to compile pattern {pattern_name}: {e}")

        # Also process pattern sections (nested format)
        for section_name, section_content in content.items():
            if section_name in ['metadata', 'entity_types', 'validation', 'quality_metrics',
                              'dependencies', 'testing', 'patterns', 'entity_patterns', 'generic_state']:  # Skip 'patterns' as it's handled above
                continue

            if not isinstance(section_content, dict):
                continue

            # Load patterns from section
            for pattern_name, pattern_data in section_content.items():
                try:
                    compiled_pattern = self._compile_pattern(
                        section_name,
                        pattern_name,
                        pattern_data,
                        metadata,
                        entity_types
                    )

                    if compiled_pattern:
                        full_pattern_name = f"{section_name}.{pattern_name}"
                        pattern_group.patterns[full_pattern_name] = compiled_pattern

                except Exception as e:
                    self.logger.error(f"Failed to compile pattern {section_name}.{pattern_name}: {e}")
    
    def _compile_pattern(
        self,
        section_name: str,
        pattern_name: str,
        pattern_data: Dict[str, Any],
        metadata: PatternMetadata,
        entity_types: Dict[str, Dict[str, Any]]
    ) -> Optional[CompiledPattern]:
        """Compile a single pattern."""
        if not isinstance(pattern_data, dict) or 'pattern' not in pattern_data:
            return None
        
        try:
            # Extract pattern information
            pattern_string = pattern_data['pattern']
            confidence = pattern_data.get('confidence', 0.7)
            components = pattern_data.get('components', {})
            examples = pattern_data.get('examples', [])
            
            # Determine entity type from pattern data
            entity_type = None
            pattern_entity_types = pattern_data.get('entity_types', [])
            if pattern_entity_types:
                # Use the first entity type from the list
                if isinstance(pattern_entity_types, list) and pattern_entity_types:
                    entity_type = pattern_entity_types[0].upper()
                elif isinstance(pattern_entity_types, str):
                    entity_type = pattern_entity_types.upper()
            
            # Fallback to section name if no entity type specified
            if not entity_type:
                # Map section names to entity types - comprehensive mapping for all pattern sections
                section_to_entity = {
                    # Legal professionals and parties
                    'attorneys': 'ATTORNEY',
                    'judges': 'JUDGE', 
                    'justices': 'JUDGE',
                    'courts': 'COURT',
                    'parties': 'PARTY',
                    
                    # Citation patterns - map to specific citation types
                    'case_citations': 'CASE_CITATION',
                    'citations': 'LEGAL_CITATION',
                    'federal_citations': 'FEDERAL_CASE_CITATION',
                    'state_citations': 'STATE_CASE_CITATION',
                    'statute_citations': 'STATUTE_CITATION',
                    'regulation_citations': 'REGULATION_CITATION',
                    'constitutional_citations': 'CONSTITUTIONAL_CITATION',
                    
                    # Court and district patterns
                    'districts': 'DISTRICT',
                    'jurisdictions': 'JURISDICTION',
                    'venues': 'VENUE',
                    
                    # Document and filing patterns  
                    'documents': 'DOCUMENT',
                    'motions': 'MOTION',
                    'briefs': 'BRIEF',
                    'orders': 'ORDER',
                    'judgments': 'JUDGMENT',
                    
                    # Other entity types
                    'dates': 'DATE',
                    'monetary': 'MONETARY_AMOUNT',
                    'procedural': 'PROCEDURAL_RULE',
                    'organizations': 'ORGANIZATION',
                    'locations': 'LOCATION'
                }
                entity_type = section_to_entity.get(section_name.lower(), section_name.upper())
            
            # Compile regex with error handling
            compiled_regex = None
            try:
                if self.compiler:
                    compiled_regex = self.compiler.compile_pattern(
                        pattern_string,
                        pattern_name=f"{section_name}.{pattern_name}"
                    )
                else:
                    # Don't use IGNORECASE - patterns should be case-sensitive for legal text
                    compiled_regex = re.compile(pattern_string, re.MULTILINE)
            except re.error as e:
                self.logger.warning(f"Invalid regex pattern in {section_name}.{pattern_name}: {e}")
                return None
            except Exception as e:
                self.logger.warning(f"Error compiling pattern {section_name}.{pattern_name}: {e}")
                return None
            
            return CompiledPattern(
                name=f"{section_name}.{pattern_name}",
                pattern=pattern_string,
                compiled_regex=compiled_regex,
                confidence=confidence,
                components=components,
                examples=examples,
                metadata=metadata,
                entity_type=entity_type,
                dependencies=pattern_data.get('dependencies', []),
                validation_rules=pattern_data.get('validation', {})
            )
            
        except Exception as e:
            self.logger.error(f"Failed to compile pattern {section_name}.{pattern_name}: {e}")
            return None
    
    def _build_indexes(self) -> None:
        """Build internal indexes for fast pattern lookup."""
        with self._lock:
            self._pattern_index.clear()
            self._entity_type_index.clear()
            self._mapped_entity_type_index.clear()
            self._dependency_graph.clear()
            
            for group_name, pattern_group in self._patterns.items():
                for pattern_name, compiled_pattern in pattern_group.patterns.items():
                    # Pattern name index
                    self._pattern_index[pattern_name] = (group_name, pattern_name)
                    
                    # Entity type index (original)
                    if compiled_pattern.entity_type:
                        self._entity_type_index[compiled_pattern.entity_type].append(
                            (group_name, pattern_name)
                        )
                        
                        # Also index by mapped entity type
                        mapped_type = self._map_entity_type(compiled_pattern.entity_type)
                        if mapped_type and mapped_type != compiled_pattern.entity_type:
                            self._mapped_entity_type_index[mapped_type].append(
                                (group_name, pattern_name)
                            )
                    
                    # Dependency graph
                    for dep in compiled_pattern.dependencies:
                        self._dependency_graph[pattern_name].add(dep)
                    for dep in pattern_group.dependencies:
                        self._dependency_graph[pattern_name].add(dep)
    
    def _aggregate_examples_from_patterns(self) -> None:
        """
        Aggregate examples from all loaded patterns by entity type.

        This method collects examples from pattern definitions and organizes them
        by entity type for quick lookup.
        """
        try:
            self.logger.info("Aggregating examples from loaded patterns...")

            with self._lock:
                # Clear existing aggregated examples
                self._aggregated_examples.clear()

                # Iterate through all loaded patterns
                for group_name, pattern_group in self._patterns.items():
                    for pattern_name, compiled_pattern in pattern_group.patterns.items():
                        # Skip patterns without entity type or examples
                        if not compiled_pattern.entity_type or not compiled_pattern.examples:
                            continue

                        # Get the mapped entity type
                        entity_type = self._map_entity_type(compiled_pattern.entity_type)

                        # Initialize entity type list if needed
                        if entity_type not in self._aggregated_examples:
                            self._aggregated_examples[entity_type] = []

                        # Add unique examples (avoid duplicates)
                        for example in compiled_pattern.examples:
                            if example not in self._aggregated_examples[entity_type]:
                                self._aggregated_examples[entity_type].append(example)

                        # Also store for the original (unmapped) entity type if different
                        if compiled_pattern.entity_type != entity_type:
                            if compiled_pattern.entity_type not in self._aggregated_examples:
                                self._aggregated_examples[compiled_pattern.entity_type] = []

                            for example in compiled_pattern.examples:
                                if example not in self._aggregated_examples[compiled_pattern.entity_type]:
                                    self._aggregated_examples[compiled_pattern.entity_type].append(example)

                # Log statistics about aggregated examples
                total_entity_types = len(self._aggregated_examples)
                total_examples = sum(len(examples) for examples in self._aggregated_examples.values())

                self.logger.info(
                    f"Aggregated {total_examples} examples across {total_entity_types} entity types"
                )

                # Log entity types with most examples (top 5)
                sorted_types = sorted(
                    self._aggregated_examples.items(),
                    key=lambda x: len(x[1]),
                    reverse=True
                )[:5]

                for entity_type, examples in sorted_types:
                    self.logger.debug(
                        f"Entity type '{entity_type}': {len(examples)} examples"
                    )

                # Warn about entity types without examples (only check types with actual patterns)
                entity_types_without_examples = []
                # Only check entity types that have actual pattern definitions
                for et in self._entity_type_index.keys():
                    if et not in self._aggregated_examples or not self._aggregated_examples[et]:
                        entity_types_without_examples.append(et)

                if entity_types_without_examples:
                    self.logger.warning(
                        f"{len(entity_types_without_examples)} entity types have no examples: "
                        f"{entity_types_without_examples[:5]}{'...' if len(entity_types_without_examples) > 5 else ''}"
                    )

        except Exception as e:
            self.logger.error(f"Failed to aggregate examples from patterns: {e}")
            # Don't raise - this is supplementary data
    
    def get_pattern(self, pattern_name: str) -> Optional[CompiledPattern]:
        """
        Get a compiled pattern by name.
        
        Args:
            pattern_name: Name of the pattern
            
        Returns:
            Optional[CompiledPattern]: Compiled pattern or None if not found
        """
        with self._lock:
            if pattern_name in self._pattern_index:
                group_name, _ = self._pattern_index[pattern_name]
                return self._patterns[group_name].patterns.get(pattern_name)
        return None
    
    def get_patterns_by_entity_type(self, entity_type: str) -> List[CompiledPattern]:
        """
        Get all patterns for a specific entity type.
        
        Args:
            entity_type: Entity type to search for
            
        Returns:
            List[CompiledPattern]: List of matching patterns
        """
        patterns = []
        with self._lock:
            # First check the mapped index (for EntityType enum values)
            if entity_type in self._mapped_entity_type_index:
                for group_name, pattern_name in self._mapped_entity_type_index[entity_type]:
                    pattern = self._patterns[group_name].patterns.get(pattern_name)
                    if pattern:
                        patterns.append(pattern)
            
            # Also check the original index (for direct matches)
            if entity_type in self._entity_type_index:
                for group_name, pattern_name in self._entity_type_index[entity_type]:
                    pattern = self._patterns[group_name].patterns.get(pattern_name)
                    if pattern and pattern not in patterns:  # Avoid duplicates
                        patterns.append(pattern)
        
        return patterns
    
    def get_patterns_by_confidence(self, min_confidence: float) -> List[CompiledPattern]:
        """
        Get all patterns with confidence above threshold.
        
        Args:
            min_confidence: Minimum confidence threshold
            
        Returns:
            List[CompiledPattern]: List of matching patterns
        """
        patterns = []
        with self._lock:
            for pattern_group in self._patterns.values():
                for pattern in pattern_group.patterns.values():
                    if pattern.confidence >= min_confidence:
                        patterns.append(pattern)
        return patterns
    
    def get_pattern_groups(self) -> Dict[str, PatternGroup]:
        """
        Get all pattern groups.
        
        Returns:
            Dict[str, PatternGroup]: All loaded pattern groups
        """
        with self._lock:
            return self._patterns.copy()
    
    def get_pattern_names(self) -> List[str]:
        """
        Get all pattern names.
        
        Returns:
            List[str]: List of all pattern names
        """
        with self._lock:
            return list(self._pattern_index.keys())
    
    def get_entity_types(self) -> List[str]:
        """
        Get all entity types (including mapped types).

        Returns:
            List[str]: List of all entity types
        """
        with self._lock:
            # Combine original and mapped entity types
            all_types = set(self._entity_type_index.keys())
            all_types.update(self._mapped_entity_type_index.keys())
            return sorted(list(all_types))

    def get_entity_types_with_examples(self) -> List[str]:
        """
        Get only entity types that have examples.

        Returns:
            List[str]: List of entity types with examples
        """
        with self._lock:
            entity_types_with_examples = []

            # Check all entity types from the index
            all_types = set(self._entity_type_index.keys())
            all_types.update(self._mapped_entity_type_index.keys())

            for entity_type in all_types:
                # Check if this entity type has any examples
                has_examples = False

                # Check in aggregated examples
                if entity_type in self._aggregated_examples and self._aggregated_examples[entity_type]:
                    has_examples = True
                else:
                    # Check in patterns directly
                    patterns = self.get_patterns_by_entity_type(entity_type)
                    for pattern in patterns:
                        if pattern.examples:
                            has_examples = True
                            break

                if has_examples:
                    entity_types_with_examples.append(entity_type)

            return sorted(entity_types_with_examples)

    def get_relationship_types(self) -> List[str]:
        """
        Get all relationship types from relationship pattern files.

        Returns:
            List[str]: List of all relationship types
        """
        relationship_types = []
        relationships_dir = self.patterns_dir / "relationships"

        if not relationships_dir.exists():
            return []

        for yaml_file in relationships_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)

                if data and 'patterns' in data:
                    for pattern in data['patterns']:
                        rel_type = pattern.get('relationship_type')
                        if rel_type and rel_type not in relationship_types:
                            relationship_types.append(rel_type)
            except Exception as e:
                self.logger.warning(f"Error loading relationship file {yaml_file}: {e}")

        return sorted(relationship_types)

    def get_relationship_patterns(self) -> Dict[str, List[Dict]]:
        """
        Get all relationship patterns organized by category.

        Returns:
            Dict[str, List[Dict]]: Relationship patterns by category
        """
        relationship_patterns = {}
        relationships_dir = self.patterns_dir / "relationships"

        if not relationships_dir.exists():
            return {}

        for yaml_file in relationships_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)

                if data and 'patterns' in data:
                    category = yaml_file.stem  # Use filename as category
                    relationship_patterns[category] = data['patterns']
            except Exception as e:
                self.logger.warning(f"Error loading relationship file {yaml_file}: {e}")

        return relationship_patterns

    def get_relationship_categories(self) -> Dict[str, List[str]]:
        """
        Get relationship types organized by category for wave building.

        Returns:
            Dict[str, List[str]]: Relationship types by category
        """
        categories = {}
        relationships_dir = self.patterns_dir / "relationships"

        if not relationships_dir.exists():
            return {}

        for yaml_file in relationships_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)

                if data and 'patterns' in data:
                    category = yaml_file.stem  # Use filename as category
                    rel_types = []

                    for pattern in data['patterns']:
                        rel_type = pattern.get('relationship_type')
                        if rel_type and rel_type not in rel_types:
                            rel_types.append(rel_type)

                    if rel_types:
                        categories[category] = sorted(rel_types)
            except Exception as e:
                self.logger.warning(f"Error loading relationship file {yaml_file}: {e}")

        return categories

    def get_dependencies(self, pattern_name: str) -> Set[str]:
        """
        Get dependencies for a pattern.
        
        Args:
            pattern_name: Name of the pattern
            
        Returns:
            Set[str]: Set of dependency names
        """
        with self._lock:
            return self._dependency_graph.get(pattern_name, set()).copy()
    
    def reload_patterns(self) -> None:
        """Reload all patterns from disk."""
        self.logger.info("Reloading patterns...")
        
        with self._lock:
            # Clear existing data
            self._patterns.clear()
            self._pattern_index.clear()
            self._entity_type_index.clear()
            self._dependency_graph.clear()
            self._file_hashes.clear()
            
            # Reset metrics
            self._load_metrics = {
                "files_loaded": 0,
                "patterns_loaded": 0,
                "load_errors": 0,
                "last_load_time": None,
                "total_load_time": 0.0
            }
        
        # Reload
        self.load_all_patterns()
    
    def get_load_metrics(self) -> Dict[str, Any]:
        """
        Get pattern loading metrics.
        
        Returns:
            Dict[str, Any]: Loading metrics
        """
        with self._lock:
            return self._load_metrics.copy()
    
    def validate_pattern_dependencies(self) -> Dict[str, List[str]]:
        """
        Validate all pattern dependencies.
        
        Returns:
            Dict[str, List[str]]: Map of pattern names to missing dependencies
        """
        missing_deps = {}
        
        with self._lock:
            all_pattern_names = set(self._pattern_index.keys())
            
            for pattern_name, deps in self._dependency_graph.items():
                missing = []
                for dep in deps:
                    if dep not in all_pattern_names:
                        missing.append(dep)
                
                if missing:
                    missing_deps[pattern_name] = missing
        
        return missing_deps
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive pattern statistics.
        
        Returns:
            Dict[str, Any]: Pattern statistics
        """
        with self._lock:
            stats = {
                "total_groups": len(self._patterns),
                "total_patterns": len(self._pattern_index),
                "total_entity_types": len(self._entity_type_index),
                "groups": {},
                "confidence_distribution": {},
                "entity_type_distribution": {},
                "dependency_count": sum(len(deps) for deps in self._dependency_graph.values())
            }
            
            # Group statistics
            for group_name, pattern_group in self._patterns.items():
                stats["groups"][group_name] = {
                    "pattern_count": len(pattern_group.patterns),
                    "metadata": {
                        "pattern_type": pattern_group.metadata.pattern_type,
                        "jurisdiction": pattern_group.metadata.jurisdiction,
                        "version": pattern_group.metadata.pattern_version
                    }
                }
            
            # Confidence distribution
            confidence_ranges = {
                "0.0-0.5": 0,
                "0.5-0.7": 0,
                "0.7-0.8": 0,
                "0.8-0.9": 0,
                "0.9-1.0": 0
            }
            
            for pattern_group in self._patterns.values():
                for pattern in pattern_group.patterns.values():
                    conf = pattern.confidence
                    if conf < 0.5:
                        confidence_ranges["0.0-0.5"] += 1
                    elif conf < 0.7:
                        confidence_ranges["0.5-0.7"] += 1
                    elif conf < 0.8:
                        confidence_ranges["0.7-0.8"] += 1
                    elif conf < 0.9:
                        confidence_ranges["0.8-0.9"] += 1
                    else:
                        confidence_ranges["0.9-1.0"] += 1
            
            stats["confidence_distribution"] = confidence_ranges
            
            # Entity type distribution
            for entity_type, patterns in self._entity_type_index.items():
                stats["entity_type_distribution"][entity_type] = len(patterns)
        
        return stats
    
    def get_entity_type_info(self, entity_type: str) -> Dict[str, Any]:
        """
        Get comprehensive information about an entity type.
        
        Args:
            entity_type: The entity type to get info for
            
        Returns:
            Dict with entity type information including patterns, examples, descriptions
        """
        with self._lock:
            patterns = self.get_patterns_by_entity_type(entity_type)
            
            # Collect all examples and descriptions
            all_examples = []
            descriptions = []
            pattern_names = []
            confidence_scores = []
            
            for pattern in patterns:
                if pattern.examples:
                    all_examples.extend(pattern.examples[:3])  # Limit examples per pattern
                if pattern.metadata.description:
                    descriptions.append(pattern.metadata.description)
                pattern_names.append(pattern.name)
                confidence_scores.append(pattern.confidence)
            
            # Get unique examples from patterns
            unique_examples = list(dict.fromkeys(all_examples))[:10]  # Limit total examples

            # If no examples from patterns, use aggregated examples
            if not unique_examples and entity_type in self._aggregated_examples:
                unique_examples = self._aggregated_examples[entity_type][:5]  # Get up to 5 aggregated examples
                self.logger.debug(f"Using aggregated examples for {entity_type}: {len(unique_examples)} examples")
            
            # Calculate average confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Get the most common description or generate one
            description = descriptions[0] if descriptions else f"Legal entity type: {entity_type.replace('_', ' ').lower()}"
            
            return {
                "entity_type": entity_type,
                "pattern_count": len(patterns),
                "examples": unique_examples,
                "description": description,
                "average_confidence": avg_confidence,
                "pattern_names": pattern_names[:10],  # Limit pattern names shown
                "has_patterns": len(patterns) > 0,
                "jurisdictions": list(set(p.metadata.jurisdiction for p in patterns if p.metadata.jurisdiction)),
                "pattern_types": list(set(p.metadata.pattern_type for p in patterns if p.metadata.pattern_type))
            }
    
    def get_all_entity_types_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information for all entity types.
        
        Returns:
            Dict mapping entity types to their information
        """
        entity_info = {}
        
        # Get entity types with patterns
        for entity_type in self.get_entity_types():
            entity_info[entity_type] = self.get_entity_type_info(entity_type)
        
        # Also include entity types that only have aggregated examples
        with self._lock:
            for entity_type in self._aggregated_examples.keys():
                if entity_type not in entity_info:
                    entity_info[entity_type] = self.get_entity_type_info(entity_type)
        
        return entity_info
    
    def get_aggregated_examples(self, entity_type: str) -> List[str]:
        """
        Get aggregated examples for a specific entity type.

        Args:
            entity_type: The entity type to get examples for

        Returns:
            List[str]: List of example strings for the entity type
        """
        with self._lock:
            # Try mapped entity type first
            mapped_type = self._map_entity_type(entity_type)
            if mapped_type in self._aggregated_examples:
                return self._aggregated_examples[mapped_type].copy()

            # Try original entity type
            if entity_type in self._aggregated_examples:
                return self._aggregated_examples[entity_type].copy()

            return []

    def get_all_aggregated_examples(self) -> Dict[str, List[str]]:
        """
        Get all aggregated examples organized by entity type.

        Returns:
            Dict[str, List[str]]: Dictionary mapping entity types to their examples
        """
        with self._lock:
            return {
                entity_type: examples.copy()
                for entity_type, examples in self._aggregated_examples.items()
            }

    def get_citation_types(self) -> List[str]:
        """
        Get all citation types from loaded patterns.

        Returns:
            List of citation type names
        """
        citation_types = set()
        with self._lock:
            for pattern_group in self._patterns.values():
                for pattern in pattern_group.patterns.values():
                    # Check if it's a citation pattern
                    if pattern.entity_type and 'CITATION' in pattern.entity_type:
                        citation_types.add(pattern.entity_type)
                    # Also check pattern name for citation indicators
                    elif any(term in pattern.name.lower() for term in ['citation', 'cite', 'reference']):
                        # Extract citation type from pattern name
                        parts = pattern.name.split('.')
                        if len(parts) > 0:
                            citation_type = parts[0].upper()
                            if 'CITATION' not in citation_type:
                                citation_type = f"{citation_type}_CITATION"
                            citation_types.add(citation_type)

        return sorted(list(citation_types))
    
    def get_all_patterns_detailed(self) -> List[Dict[str, Any]]:
        """
        Get detailed information about all patterns.
        
        Returns:
            List of dictionaries with detailed pattern information
        """
        patterns_detailed = []
        with self._lock:
            for group_name, pattern_group in self._patterns.items():
                for pattern_name, pattern in pattern_group.patterns.items():
                    # Use mapped entity type if available
                    mapped_entity_type = self._map_entity_type(pattern.entity_type) if pattern.entity_type else pattern.entity_type
                    
                    patterns_detailed.append({
                        "name": pattern.name,
                        "pattern": pattern.pattern[:200] if len(pattern.pattern) > 200 else pattern.pattern,
                        "full_pattern": pattern.pattern,
                        "entity_type": mapped_entity_type,  # Use mapped type
                        "original_entity_type": pattern.entity_type,  # Keep original for reference
                        "confidence": pattern.confidence,
                        "examples": pattern.examples[:5] if pattern.examples else [],
                        "group": group_name,
                        "metadata": {
                            "pattern_type": pattern.metadata.pattern_type,
                            "jurisdiction": pattern.metadata.jurisdiction,
                            "court_level": pattern.metadata.court_level,
                            "bluebook_compliance": pattern.metadata.bluebook_compliance,
                            "description": pattern.metadata.description,
                            "file_path": pattern.metadata.file_path
                        },
                        "components": pattern.components,
                        "dependencies": pattern.dependencies,
                        "validation_rules": pattern.validation_rules
                    })
        
        return patterns_detailed
    
    def _generate_group_name(self, file_path: Path, metadata: PatternMetadata) -> str:
        """Generate a group name from file path and metadata."""
        # Use metadata pattern_type if available
        if metadata.pattern_type and metadata.pattern_type != 'unknown':
            return metadata.pattern_type
        
        # Use file name without extension
        return file_path.stem
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    @lru_cache(maxsize=100)
    def search_patterns(
        self, 
        query: str, 
        entity_type: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[CompiledPattern]:
        """
        Search patterns by name, description, or entity type.
        
        Args:
            query: Search query
            entity_type: Optional entity type filter
            min_confidence: Optional minimum confidence filter
            
        Returns:
            List[CompiledPattern]: Matching patterns
        """
        matches = []
        query_lower = query.lower()
        
        with self._lock:
            for pattern_group in self._patterns.values():
                for pattern in pattern_group.patterns.values():
                    # Apply filters
                    if entity_type and pattern.entity_type != entity_type:
                        continue
                    
                    if min_confidence and pattern.confidence < min_confidence:
                        continue
                    
                    # Check if query matches
                    if (query_lower in pattern.name.lower() or
                        query_lower in pattern.metadata.description.lower() if pattern.metadata.description else False or
                        any(query_lower in example.lower() for example in pattern.examples)):
                        matches.append(pattern)
        
        # Sort by confidence descending
        matches.sort(key=lambda p: p.confidence, reverse=True)
        
        return matches
    
    def __repr__(self) -> str:
        """String representation of PatternLoader."""
        return (
            f"PatternLoader("
            f"patterns_dir='{self.patterns_dir}', "
            f"groups={len(self._patterns)}, "
            f"patterns={len(self._pattern_index)}, "
            f"entity_types={len(self._entity_type_index)}"
            f")"
        )