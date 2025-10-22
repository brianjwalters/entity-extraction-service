"""
Pattern Statistics Models for Entity Extraction Service.

Comprehensive models for pattern library analytics and statistics.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ConfidenceDistribution(BaseModel):
    """Distribution of pattern confidence scores."""
    very_low: int = Field(0, description="Patterns with confidence 0.0-0.5")
    low: int = Field(0, description="Patterns with confidence 0.5-0.7")
    medium: int = Field(0, description="Patterns with confidence 0.7-0.8")
    high: int = Field(0, description="Patterns with confidence 0.8-0.9")
    very_high: int = Field(0, description="Patterns with confidence 0.9-1.0")
    average: float = Field(0.0, description="Average confidence across all patterns")
    std_dev: float = Field(0.0, description="Standard deviation of confidence scores")


class JurisdictionStats(BaseModel):
    """Statistics for patterns by jurisdiction."""
    federal: int = Field(0, description="Federal jurisdiction patterns")
    state_specific: Dict[str, int] = Field(
        default_factory=dict,
        description="State-specific patterns by state code"
    )
    state_agnostic: int = Field(0, description="Patterns applicable to all states")
    international: int = Field(0, description="International legal patterns")
    unknown: int = Field(0, description="Patterns with unknown jurisdiction")
    
    @property
    def total_state_patterns(self) -> int:
        """Total number of state-specific patterns."""
        return sum(self.state_specific.values())


class BluebookComplianceInfo(BaseModel):
    """Bluebook compliance information for patterns."""
    bluebook_22nd_edition: int = Field(0, description="Patterns compliant with Bluebook 22nd Edition")
    bluebook_21st_edition: int = Field(0, description="Patterns compliant with Bluebook 21st Edition")
    bluebook_20th_edition: int = Field(0, description="Patterns compliant with Bluebook 20th Edition")
    non_bluebook: int = Field(0, description="Patterns not following Bluebook format")
    unknown_compliance: int = Field(0, description="Patterns with unknown Bluebook compliance")
    compliance_percentage: float = Field(0.0, description="Percentage of patterns with known Bluebook compliance")


class EntityTypeCoverage(BaseModel):
    """Coverage information for an entity type."""
    entity_type: str = Field(..., description="Entity type name")
    pattern_count: int = Field(0, description="Number of patterns for this entity type")
    has_ai_enhancement: bool = Field(False, description="Whether AI enhancement is available")
    has_regex_patterns: bool = Field(False, description="Whether regex patterns exist")
    confidence_avg: float = Field(0.0, description="Average confidence for patterns of this type")
    examples_count: int = Field(0, description="Number of examples available")
    jurisdictions: List[str] = Field(default_factory=list, description="Jurisdictions covered")


class CoverageAnalysis(BaseModel):
    """Analysis of pattern library coverage."""
    total_entity_types: int = Field(0, description="Total number of unique entity types")
    covered_entity_types: int = Field(0, description="Entity types with at least one pattern")
    uncovered_entity_types: List[str] = Field(
        default_factory=list,
        description="Entity types without patterns"
    )
    coverage_percentage: float = Field(0.0, description="Percentage of entity types covered")
    entity_type_details: List[EntityTypeCoverage] = Field(
        default_factory=list,
        description="Detailed coverage for each entity type"
    )
    high_coverage_types: List[str] = Field(
        default_factory=list,
        description="Entity types with >10 patterns"
    )
    low_coverage_types: List[str] = Field(
        default_factory=list,
        description="Entity types with 1-3 patterns"
    )


class PatternValidationStatus(BaseModel):
    """Validation status of patterns."""
    total_patterns: int = Field(0, description="Total number of patterns")
    valid_patterns: int = Field(0, description="Number of valid patterns")
    invalid_patterns: int = Field(0, description="Number of invalid patterns")
    validation_errors: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Validation errors by pattern ID"
    )
    untested_patterns: int = Field(0, description="Patterns not yet tested")
    test_coverage: float = Field(0.0, description="Percentage of patterns with test coverage")


class PerformanceMetrics(BaseModel):
    """Performance metrics for pattern matching."""
    average_compilation_time_ms: float = Field(0.0, description="Average pattern compilation time")
    average_match_time_ms: float = Field(0.0, description="Average pattern match time")
    cache_hit_rate: float = Field(0.0, description="Pattern cache hit rate")
    memory_usage_mb: float = Field(0.0, description="Memory used by compiled patterns")
    patterns_in_cache: int = Field(0, description="Number of patterns currently cached")
    cache_size_limit: int = Field(1000, description="Maximum cache size")


class PatternGroupStatistics(BaseModel):
    """Statistics for a pattern group."""
    group_name: str = Field(..., description="Pattern group name")
    pattern_count: int = Field(0, description="Number of patterns in group")
    pattern_type: str = Field("unknown", description="Type of patterns in group")
    jurisdiction: str = Field("unknown", description="Jurisdiction for group")
    bluebook_compliance: Optional[str] = Field(None, description="Bluebook compliance status")
    version: str = Field("1.0", description="Pattern group version")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    file_path: Optional[str] = Field(None, description="Source file path")
    dependencies: List[str] = Field(default_factory=list, description="Pattern dependencies")


class PatternLibraryHealth(BaseModel):
    """Health status of the pattern library."""
    status: str = Field("healthy", description="Overall health status: healthy, warning, critical")
    issues: List[str] = Field(default_factory=list, description="List of health issues")
    warnings: List[str] = Field(default_factory=list, description="List of warnings")
    last_reload: Optional[datetime] = Field(None, description="Last pattern reload timestamp")
    reload_frequency_hours: float = Field(24.0, description="Hours between pattern reloads")
    pattern_conflicts: List[str] = Field(default_factory=list, description="Conflicting patterns")
    duplicate_patterns: List[str] = Field(default_factory=list, description="Duplicate pattern IDs")


class PatternStatisticsResponse(BaseModel):
    """Comprehensive pattern statistics response."""
    summary: Dict[str, Any] = Field(..., description="High-level summary statistics")
    jurisdiction_breakdown: JurisdictionStats = Field(..., description="Jurisdiction statistics")
    bluebook_compliance: BluebookComplianceInfo = Field(..., description="Bluebook compliance information")
    coverage_analysis: CoverageAnalysis = Field(..., description="Entity type coverage analysis")
    confidence_distribution: ConfidenceDistribution = Field(..., description="Pattern confidence distribution")
    validation_status: PatternValidationStatus = Field(..., description="Pattern validation status")
    performance_metrics: Optional[PerformanceMetrics] = Field(None, description="Performance metrics if available")
    pattern_groups: List[PatternGroupStatistics] = Field(
        default_factory=list,
        description="Statistics for each pattern group"
    )
    library_health: PatternLibraryHealth = Field(..., description="Pattern library health status")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata and statistics"
    )