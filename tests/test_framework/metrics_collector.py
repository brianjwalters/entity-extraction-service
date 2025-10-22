"""
Metrics Collection Module for Entity Extraction Service Testing Framework

This module extracts comprehensive metrics from Entity Extraction API responses.
It collects 22+ metrics across multiple categories:

Categories:
- Routing Decision Metrics (strategy, prompt version, estimated tokens)
- Wave Execution Metrics (entities per wave, tokens per wave, duration per wave)
- Entity Distribution Metrics (counts by type, category, confidence)
- Performance Metrics (total duration, throughput, latency)
- Quality Metrics (confidence scores, validation status)
- Resource Metrics (memory usage, GPU utilization)

Usage:
    collector = MetricsCollector()
    metrics = collector.collect_metrics(api_response, execution_time)
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class RoutingMetrics:
    """Metrics about routing decision."""
    strategy: str
    prompt_version: str
    estimated_tokens: int
    estimated_duration: float
    size_category: Optional[str] = None


@dataclass
class WaveMetrics:
    """Metrics for a single wave execution."""
    wave_number: int
    entities_extracted: int
    tokens_used: int
    duration_seconds: float
    entity_types: List[str] = field(default_factory=list)


@dataclass
class EntityDistributionMetrics:
    """Metrics about entity distribution."""
    total_entities: int
    unique_types: int
    entities_by_type: Dict[str, int] = field(default_factory=dict)
    entities_by_category: Dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    min_confidence: float = 0.0
    max_confidence: float = 0.0


@dataclass
class PerformanceMetrics:
    """Performance-related metrics."""
    total_duration_seconds: float
    entities_per_second: float
    tokens_per_second: float
    avg_latency_per_wave: float
    total_tokens_used: int


@dataclass
class QualityMetrics:
    """Quality-related metrics."""
    avg_confidence_score: float
    low_confidence_count: int  # Entities with confidence < 0.7
    medium_confidence_count: int  # Entities with 0.7 <= confidence < 0.9
    high_confidence_count: int  # Entities with confidence >= 0.9
    validation_passed: bool


@dataclass
class ComprehensiveMetrics:
    """Complete metrics collection from extraction."""
    test_id: str
    timestamp: float
    document_id: str
    routing: RoutingMetrics
    waves: List[WaveMetrics]
    entity_distribution: EntityDistributionMetrics
    performance: PerformanceMetrics
    quality: QualityMetrics
    raw_response: Optional[Dict[str, Any]] = None


class MetricsCollector:
    """
    Collects comprehensive metrics from Entity Extraction API responses.

    This collector extracts 22+ metrics from the response, including:
    - Routing decision details (strategy, tokens, duration)
    - Per-wave statistics (entities, tokens, timing)
    - Entity distribution (types, categories, confidence)
    - Performance metrics (throughput, latency)
    - Quality metrics (confidence scores, validation)
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.logger = logging.getLogger(__name__)

    def collect_metrics(
        self,
        api_response: Dict[str, Any],
        execution_time: float,
        document_id: str = "unknown"
    ) -> ComprehensiveMetrics:
        """
        Collect comprehensive metrics from API response.

        Args:
            api_response: Response from /api/v2/process/extract
            execution_time: Total execution time in seconds
            document_id: Document identifier

        Returns:
            ComprehensiveMetrics: Complete metrics collection
        """
        test_id = f"test_{int(time.time() * 1000)}"
        timestamp = time.time()

        # Extract routing metrics
        routing = self._extract_routing_metrics(api_response)

        # Extract wave metrics
        waves = self._extract_wave_metrics(api_response)

        # Extract entity distribution metrics
        entities = api_response.get("entities", [])
        entity_dist = self._extract_entity_distribution_metrics(entities)

        # Calculate performance metrics
        performance = self._calculate_performance_metrics(
            execution_time=execution_time,
            total_entities=entity_dist.total_entities,
            waves=waves
        )

        # Calculate quality metrics
        quality = self._calculate_quality_metrics(entities)

        return ComprehensiveMetrics(
            test_id=test_id,
            timestamp=timestamp,
            document_id=document_id,
            routing=routing,
            waves=waves,
            entity_distribution=entity_dist,
            performance=performance,
            quality=quality,
            raw_response=api_response
        )

    def _extract_routing_metrics(self, response: Dict[str, Any]) -> RoutingMetrics:
        """Extract routing decision metrics."""
        routing_decision = response.get("routing_decision", {})

        return RoutingMetrics(
            strategy=routing_decision.get("strategy", "unknown"),
            prompt_version=routing_decision.get("prompt_version", "unknown"),
            estimated_tokens=routing_decision.get("estimated_tokens", 0),
            estimated_duration=routing_decision.get("estimated_duration", 0.0),
            size_category=routing_decision.get("size_category")
        )

    def _extract_wave_metrics(self, response: Dict[str, Any]) -> List[WaveMetrics]:
        """Extract per-wave execution metrics."""
        processing_stats = response.get("processing_stats", {})
        wave_details = processing_stats.get("wave_details", [])
        waves = []

        for wave_data in wave_details:
            # Extract entity types from wave
            entities = wave_data.get("entities", [])
            entity_types = list(set(e.get("type", "UNKNOWN") for e in entities))

            waves.append(WaveMetrics(
                wave_number=wave_data.get("wave_number", 0),
                entities_extracted=wave_data.get("entities_extracted", 0),
                tokens_used=wave_data.get("tokens_used", 0),
                duration_seconds=wave_data.get("duration_seconds", 0.0),
                entity_types=entity_types
            ))

        return waves

    def _extract_entity_distribution_metrics(
        self,
        entities: List[Dict[str, Any]]
    ) -> EntityDistributionMetrics:
        """Extract entity distribution metrics."""
        if not entities:
            return EntityDistributionMetrics(
                total_entities=0,
                unique_types=0,
                entities_by_type={},
                entities_by_category={},
                avg_confidence=0.0,
                min_confidence=0.0,
                max_confidence=0.0
            )

        # Count entities by type
        entities_by_type = defaultdict(int)
        entities_by_category = defaultdict(int)
        confidence_scores = []

        for entity in entities:
            entity_type = entity.get("type", "UNKNOWN")
            category = entity.get("category", "UNKNOWN")
            confidence = entity.get("confidence", 0.0)

            entities_by_type[entity_type] += 1
            entities_by_category[category] += 1
            confidence_scores.append(confidence)

        # Calculate confidence statistics
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        min_confidence = min(confidence_scores)
        max_confidence = max(confidence_scores)

        return EntityDistributionMetrics(
            total_entities=len(entities),
            unique_types=len(entities_by_type),
            entities_by_type=dict(entities_by_type),
            entities_by_category=dict(entities_by_category),
            avg_confidence=avg_confidence,
            min_confidence=min_confidence,
            max_confidence=max_confidence
        )

    def _calculate_performance_metrics(
        self,
        execution_time: float,
        total_entities: int,
        waves: List[WaveMetrics]
    ) -> PerformanceMetrics:
        """Calculate performance metrics."""
        # Calculate total tokens used
        total_tokens = sum(wave.tokens_used for wave in waves)

        # Calculate entities per second
        entities_per_second = total_entities / execution_time if execution_time > 0 else 0.0

        # Calculate tokens per second
        tokens_per_second = total_tokens / execution_time if execution_time > 0 else 0.0

        # Calculate average latency per wave
        avg_latency_per_wave = (
            sum(wave.duration_seconds for wave in waves) / len(waves)
            if waves else 0.0
        )

        return PerformanceMetrics(
            total_duration_seconds=execution_time,
            entities_per_second=entities_per_second,
            tokens_per_second=tokens_per_second,
            avg_latency_per_wave=avg_latency_per_wave,
            total_tokens_used=total_tokens
        )

    def _calculate_quality_metrics(
        self,
        entities: List[Dict[str, Any]]
    ) -> QualityMetrics:
        """Calculate quality metrics."""
        if not entities:
            return QualityMetrics(
                avg_confidence_score=0.0,
                low_confidence_count=0,
                medium_confidence_count=0,
                high_confidence_count=0,
                validation_passed=False
            )

        confidence_scores = [e.get("confidence", 0.0) for e in entities]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)

        # Count by confidence level
        low_count = sum(1 for c in confidence_scores if c < 0.7)
        medium_count = sum(1 for c in confidence_scores if 0.7 <= c < 0.9)
        high_count = sum(1 for c in confidence_scores if c >= 0.9)

        # Validation: Pass if avg confidence >= 0.7 and at least 80% high/medium confidence
        high_medium_ratio = (high_count + medium_count) / len(entities) if entities else 0
        validation_passed = avg_confidence >= 0.7 and high_medium_ratio >= 0.8

        return QualityMetrics(
            avg_confidence_score=avg_confidence,
            low_confidence_count=low_count,
            medium_confidence_count=medium_count,
            high_confidence_count=high_count,
            validation_passed=validation_passed
        )

    def metrics_to_dict(self, metrics: ComprehensiveMetrics) -> Dict[str, Any]:
        """
        Convert metrics to dictionary for JSON serialization.

        Args:
            metrics: ComprehensiveMetrics instance

        Returns:
            dict: Serializable metrics dictionary
        """
        return {
            "test_id": metrics.test_id,
            "timestamp": metrics.timestamp,
            "document_id": metrics.document_id,
            "routing": asdict(metrics.routing),
            "waves": [asdict(wave) for wave in metrics.waves],
            "entity_distribution": asdict(metrics.entity_distribution),
            "performance": asdict(metrics.performance),
            "quality": asdict(metrics.quality),
            "raw_response": metrics.raw_response
        }

    def format_entities_table(
        self,
        entities: List[Dict[str, Any]],
        max_display: int = 50
    ) -> str:
        """
        Format entities as terminal-friendly table with Unicode box-drawing.

        Creates a visually appealing table showing entity details including
        type, text, position, and confidence. Supports pagination for large
        entity lists to prevent overwhelming console output.

        Args:
            entities: List of LurisEntityV2 entities in dict format
            max_display: Maximum number of entities to display (default: 50)
                        Use 0 for unlimited display

        Returns:
            Formatted table string with Unicode box-drawing characters.
            Empty message if no entities provided.

        Example:
            >>> entities = [{
            ...     "entity_type": "STATUTE_CITATION",
            ...     "text": "18 U.S.C. § 922",
            ...     "start_pos": 0,
            ...     "end_pos": 15,
            ...     "confidence": 0.95
            ... }]
            >>> table = collector.format_entities_table(entities, max_display=10)
            >>> print(table)
            Extracted Entities (1 total):
            ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            ┃ #   ┃ Type             ┃ Text              ┃ Position ┃ Conf  ┃
            ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            ┃ 1   ┃ STATUTE_CITATION ┃ 18 U.S.C. § 922   ┃ [0-15]   ┃ 0.950 ┃
            ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        if not entities:
            return "\nNo entities extracted."

        lines = [
            f"\nExtracted Entities ({len(entities)} total):",
            "━" * 100,
            f"┃ {'#':<3} ┃ {'Type':<20} ┃ {'Text':<40} ┃ {'Position':<12} ┃ {'Conf':<6} ┃",
            "━" * 100,
        ]

        display_count = len(entities) if max_display == 0 else min(len(entities), max_display)

        for i, entity in enumerate(entities[:display_count], start=1):
            entity_type = entity.get("type", entity.get("entity_type", "UNKNOWN"))[:20]
            text = entity.get("text", "")[:40]
            start_pos = entity.get("start_pos", entity.get("start", 0))
            end_pos = entity.get("end_pos", entity.get("end", 0))
            confidence = entity.get("confidence", 0.0)

            pos_str = f"[{start_pos}-{end_pos}]"

            lines.append(
                f"┃ {i:<3} ┃ {entity_type:<20} ┃ {text:<40} ┃ "
                f"{pos_str:<12} ┃ {confidence:.3f} ┃"
            )

        lines.append("━" * 100)

        if max_display > 0 and len(entities) > max_display:
            lines.append(f"\n... and {len(entities) - max_display} more entities (use --max-entities 0 to show all)")

        return "\n".join(lines)

    def format_entity_type_breakdown(
        self,
        entities: List[Dict[str, Any]],
        top_n: int = 10
    ) -> str:
        """
        Format entity type breakdown with counts and average confidence.

        Provides a statistical summary of extracted entities grouped by type,
        showing the count and average confidence for each entity type. Results
        are sorted by entity count in descending order.

        Args:
            entities: List of LurisEntityV2 entities in dict format
            top_n: Maximum number of entity types to display (default: 10)
                  Remaining types are summarized in a footer line

        Returns:
            Formatted breakdown string with entity type statistics.
            Empty string if no entities provided.

        Example:
            >>> entities = [
            ...     {"entity_type": "STATUTE_CITATION", "confidence": 0.95},
            ...     {"entity_type": "STATUTE_CITATION", "confidence": 0.93},
            ...     {"entity_type": "CASE_CITATION", "confidence": 0.90}
            ... ]
            >>> breakdown = collector.format_entity_type_breakdown(entities)
            >>> print(breakdown)
            Entity Type Breakdown:
              • STATUTE_CITATION: 2 entities (avg confidence: 0.940)
              • CASE_CITATION: 1 entities (avg confidence: 0.900)
        """
        if not entities:
            return ""

        type_stats = defaultdict(lambda: {"count": 0, "total_conf": 0.0, "entities": []})

        for entity in entities:
            entity_type = entity.get("type", entity.get("entity_type", "UNKNOWN"))
            confidence = entity.get("confidence", 0.0)
            type_stats[entity_type]["count"] += 1
            type_stats[entity_type]["total_conf"] += confidence
            type_stats[entity_type]["entities"].append(entity)

        # Sort by count descending
        sorted_types = sorted(
            type_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )

        lines = ["\nEntity Type Breakdown:"]
        for entity_type, stats in sorted_types[:top_n]:
            count = stats["count"]
            avg_conf = stats["total_conf"] / count
            lines.append(f"  • {entity_type}: {count} entities (avg confidence: {avg_conf:.3f})")

        if len(sorted_types) > top_n:
            remaining = len(sorted_types) - top_n
            lines.append(f"  ... and {remaining} more entity types")

        return "\n".join(lines)

    def format_relationships_table(
        self,
        relationships: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
        max_display: int = 20
    ) -> str:
        """
        Format Wave 4 relationships as terminal-friendly display.

        Creates a readable display of entity relationships extracted during Wave 4,
        showing relationship type, source/target entities, confidence, and supporting
        evidence. Requires entity list for entity ID lookups.

        Args:
            relationships: List of entity relationships from Wave 4 extraction
            entities: List of entities (for ID-to-entity lookup)
            max_display: Maximum number of relationships to display (default: 20)
                        Use 0 for unlimited display

        Returns:
            Formatted relationships string with details for each relationship.
            Empty string if no relationships provided.

        Example:
            >>> relationships = [{
            ...     "relationship_type": "CITES",
            ...     "source_entity_id": "entity-1",
            ...     "target_entity_id": "entity-2",
            ...     "confidence": 0.92,
            ...     "evidence_text": "The statute cites the constitutional provision..."
            ... }]
            >>> entities = [
            ...     {"id": "entity-1", "text": "18 U.S.C. § 922"},
            ...     {"id": "entity-2", "text": "Second Amendment"}
            ... ]
            >>> table = collector.format_relationships_table(relationships, entities)
            >>> print(table)
            Entity Relationships (1 total):

              1. CITES (confidence: 0.920)
                 Source: 18 U.S.C. § 922
                 Target: Second Amendment
                 Evidence: "The statute cites the constitutional provision..."
        """
        if not relationships:
            return ""

        # Create entity lookup by ID
        entity_lookup = {e.get("id"): e for e in entities}

        lines = [f"\nEntity Relationships ({len(relationships)} total):"]

        display_count = len(relationships) if max_display == 0 else min(len(relationships), max_display)

        for i, rel in enumerate(relationships[:display_count], start=1):
            rel_type = rel.get("relationship_type", "UNKNOWN")
            source_id = rel.get("source_entity_id")
            target_id = rel.get("target_entity_id")
            confidence = rel.get("confidence", 0.0)
            evidence = rel.get("evidence_text", "")[:80]

            source_entity = entity_lookup.get(source_id, {})
            target_entity = entity_lookup.get(target_id, {})

            source_text = source_entity.get("text", "Unknown")[:40]
            target_text = target_entity.get("text", "Unknown")[:40]

            lines.append(f"\n  {i}. {rel_type} (confidence: {confidence:.3f})")
            lines.append(f"     Source: {source_text}")
            lines.append(f"     Target: {target_text}")
            if evidence:
                lines.append(f"     Evidence: \"{evidence}\"")

        if max_display > 0 and len(relationships) > max_display:
            lines.append(f"\n... and {len(relationships) - max_display} more relationships")

        return "\n".join(lines)

    def format_metrics_summary(
        self,
        metrics: ComprehensiveMetrics,
        show_entities: bool = True,
        max_entities: int = 50
    ) -> str:
        """
        Format metrics as human-readable summary.

        Args:
            metrics: ComprehensiveMetrics instance
            show_entities: Whether to display entity table (default: True)
            max_entities: Maximum entities to display (default: 50)

        Returns:
            str: Formatted summary text
        """
        lines = [
            "="*70,
            "Entity Extraction Test Results",
            "="*70,
            f"Test ID: {metrics.test_id}",
            f"Document: {metrics.document_id}",
            f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(metrics.timestamp))}",
            "",
            "Routing Decision:",
            f"  Strategy: {metrics.routing.strategy}",
            f"  Prompt Version: {metrics.routing.prompt_version}",
            f"  Estimated Tokens: {metrics.routing.estimated_tokens:,}",
            f"  Estimated Duration: {metrics.routing.estimated_duration:.2f}s",
            "",
            "Wave Execution:",
        ]

        for wave in metrics.waves:
            lines.append(f"  Wave {wave.wave_number}:")
            lines.append(f"    Entities: {wave.entities_extracted}")
            lines.append(f"    Tokens: {wave.tokens_used:,}")
            lines.append(f"    Duration: {wave.duration_seconds:.2f}s")
            lines.append(f"    Types: {len(wave.entity_types)}")

        lines.extend([
            "",
            "Entity Distribution:",
            f"  Total Entities: {metrics.entity_distribution.total_entities}",
            f"  Unique Types: {metrics.entity_distribution.unique_types}",
            f"  Avg Confidence: {metrics.entity_distribution.avg_confidence:.3f}",
            f"  Confidence Range: [{metrics.entity_distribution.min_confidence:.3f}, {metrics.entity_distribution.max_confidence:.3f}]",
            "",
            "Performance:",
            f"  Total Duration: {metrics.performance.total_duration_seconds:.2f}s",
            f"  Entities/Second: {metrics.performance.entities_per_second:.2f}",
            f"  Tokens/Second: {metrics.performance.tokens_per_second:.2f}",
            f"  Avg Wave Latency: {metrics.performance.avg_latency_per_wave:.2f}s",
            f"  Total Tokens: {metrics.performance.total_tokens_used:,}",
            "",
            "Quality:",
            f"  Avg Confidence: {metrics.quality.avg_confidence_score:.3f}",
            f"  High Confidence: {metrics.quality.high_confidence_count} (≥0.9)",
            f"  Medium Confidence: {metrics.quality.medium_confidence_count} (0.7-0.9)",
            f"  Low Confidence: {metrics.quality.low_confidence_count} (<0.7)",
            f"  Validation: {'✅ PASSED' if metrics.quality.validation_passed else '❌ FAILED'}",
            "="*70
        ])

        # Add entity display sections if enabled
        entities = metrics.raw_response.get("entities", []) if metrics.raw_response else []
        relationships = metrics.raw_response.get("relationships", []) if metrics.raw_response else []

        if show_entities and entities:
            lines.append(self.format_entities_table(entities, max_entities))
            lines.append(self.format_entity_type_breakdown(entities))

        if relationships:
            lines.append(self.format_relationships_table(relationships, entities))

        return "\n".join(lines)


if __name__ == "__main__":
    # Example usage with mock data
    mock_response = {
        "document_id": "rahimi_2024",
        "routing_decision": {
            "strategy": "three_wave",
            "prompt_version": "wave_v1",
            "estimated_tokens": 30838,
            "estimated_duration": 0.85
        },
        "processing_stats": {
            "duration_seconds": 0.92,
            "entities_extracted": 142,
            "waves_executed": 4,
            "tokens_used": 28500,
            "wave_details": [
                {
                    "wave_number": 1,
                    "entities_extracted": 65,
                    "tokens_used": 8500,
                    "duration_seconds": 0.25,
                    "entities": [{"type": "CASE", "confidence": 0.95}]
                },
                {
                    "wave_number": 2,
                    "entities_extracted": 38,
                    "tokens_used": 7200,
                    "duration_seconds": 0.22,
                    "entities": [{"type": "STATUTE", "confidence": 0.92}]
                }
            ]
        },
        "entities": [
            {"type": "CASE", "text": "United States v. Rahimi", "confidence": 0.95, "category": "citation"},
            {"type": "STATUTE", "text": "18 U.S.C. § 922(g)(8)", "confidence": 0.92, "category": "statute"},
            {"type": "DATE", "text": "June 21, 2024", "confidence": 0.88, "category": "temporal"}
        ]
    }

    collector = MetricsCollector()
    metrics = collector.collect_metrics(mock_response, execution_time=0.92, document_id="rahimi_2024")

    print(collector.format_metrics_summary(metrics))
