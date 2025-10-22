#!/usr/bin/env python3
"""
Entity Relationship Analysis Script

Analyzes and visualizes entity relationships from test_history.json
for the Entity Extraction Service test dashboard.

Usage:
    python3 analyze_relationships.py [options]

Options:
    --test-id <id>         Analyze specific test
    --relationship-type <type>  Filter by relationship type
    --min-confidence <float>    Filter by minimum confidence
    --export-csv              Export to CSV format
    --export-json             Export filtered results to JSON
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict
from dataclasses import dataclass, asdict


@dataclass
class RelationshipStats:
    """Statistics for relationship analysis"""
    total_relationships: int
    unique_types: int
    avg_confidence: float
    min_confidence: float
    max_confidence: float
    relationships_by_type: Dict[str, int]
    top_entity_pairs: List[tuple]


class RelationshipAnalyzer:
    """Analyzer for entity relationships in test data"""

    def __init__(self, data_file: str = "test_history.json"):
        self.data_file = Path(data_file)
        self.data = self._load_data()

    def _load_data(self) -> dict:
        """Load test history data"""
        with open(self.data_file, 'r') as f:
            return json.load(f)

    def get_test_by_id(self, test_id: str) -> Optional[dict]:
        """Get specific test by ID"""
        for test in self.data['tests']:
            if test['test_id'] == test_id:
                return test
        return None

    def get_all_relationships(self, test_id: Optional[str] = None) -> List[dict]:
        """Get all relationships, optionally filtered by test ID"""
        relationships = []

        if test_id:
            test = self.get_test_by_id(test_id)
            if test:
                relationships = test.get('relationships', [])
        else:
            for test in self.data['tests']:
                relationships.extend(test.get('relationships', []))

        return relationships

    def filter_relationships(
        self,
        relationship_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        test_id: Optional[str] = None
    ) -> List[dict]:
        """Filter relationships by criteria"""
        relationships = self.get_all_relationships(test_id)

        if relationship_type:
            relationships = [r for r in relationships if r['relationship_type'] == relationship_type]

        if min_confidence is not None:
            relationships = [r for r in relationships if r['confidence'] >= min_confidence]

        return relationships

    def calculate_stats(self, relationships: List[dict]) -> RelationshipStats:
        """Calculate statistics for relationships"""
        if not relationships:
            return RelationshipStats(
                total_relationships=0,
                unique_types=0,
                avg_confidence=0.0,
                min_confidence=0.0,
                max_confidence=0.0,
                relationships_by_type={},
                top_entity_pairs=[]
            )

        # Basic stats
        confidences = [r['confidence'] for r in relationships]
        types = [r['relationship_type'] for r in relationships]

        # Count by type
        type_counts = defaultdict(int)
        for t in types:
            type_counts[t] += 1

        # Entity pair frequency
        pair_counts = defaultdict(int)
        for r in relationships:
            pair = (r['source_entity_id'], r['target_entity_id'])
            pair_counts[pair] += 1

        top_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return RelationshipStats(
            total_relationships=len(relationships),
            unique_types=len(set(types)),
            avg_confidence=sum(confidences) / len(confidences),
            min_confidence=min(confidences),
            max_confidence=max(confidences),
            relationships_by_type=dict(type_counts),
            top_entity_pairs=top_pairs
        )

    def get_entity_by_id(self, test_id: str, entity_id: str) -> Optional[dict]:
        """Get entity by ID from specific test"""
        test = self.get_test_by_id(test_id)
        if test:
            entities = test['raw_response']['entities']
            for entity in entities:
                if entity['id'] == entity_id:
                    return entity
        return None

    def get_entity_relationships(self, test_id: str, entity_id: str) -> Dict[str, List[dict]]:
        """Get all relationships for a specific entity"""
        test = self.get_test_by_id(test_id)
        if not test:
            return {'as_source': [], 'as_target': []}

        relationships = test.get('relationships', [])

        as_source = [r for r in relationships if r['source_entity_id'] == entity_id]
        as_target = [r for r in relationships if r['target_entity_id'] == entity_id]

        return {
            'as_source': as_source,
            'as_target': as_target
        }

    def export_to_csv(self, output_file: str = "relationships.csv"):
        """Export relationships to CSV format"""
        import csv

        relationships = self.get_all_relationships()

        with open(output_file, 'w', newline='') as f:
            fieldnames = [
                'id', 'test_id', 'document_id', 'relationship_type',
                'source_entity_id', 'target_entity_id', 'confidence',
                'start_pos', 'end_pos', 'context'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for rel in relationships:
                row = {k: rel.get(k, '') for k in fieldnames}
                writer.writerow(row)

        print(f"✅ Exported {len(relationships)} relationships to {output_file}")

    def print_summary(self, test_id: Optional[str] = None):
        """Print summary of relationships"""
        relationships = self.get_all_relationships(test_id)
        stats = self.calculate_stats(relationships)

        print("=" * 70)
        if test_id:
            print(f"RELATIONSHIP SUMMARY FOR TEST: {test_id}")
        else:
            print("RELATIONSHIP SUMMARY (ALL TESTS)")
        print("=" * 70)

        print(f"\nTotal Relationships: {stats.total_relationships}")
        print(f"Unique Types: {stats.unique_types}")
        print(f"\nConfidence Statistics:")
        print(f"  Average: {stats.avg_confidence:.3f}")
        print(f"  Min: {stats.min_confidence:.3f}")
        print(f"  Max: {stats.max_confidence:.3f}")

        print(f"\nRelationships by Type:")
        for rel_type, count in sorted(stats.relationships_by_type.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / stats.total_relationships) * 100
            print(f"  {rel_type}: {count} ({percentage:.1f}%)")

        print("\n" + "=" * 70)

    def print_entity_network(self, test_id: str, entity_id: str):
        """Print network of relationships for a specific entity"""
        test = self.get_test_by_id(test_id)
        if not test:
            print(f"❌ Test {test_id} not found")
            return

        entity = self.get_entity_by_id(test_id, entity_id)
        if not entity:
            print(f"❌ Entity {entity_id} not found in test {test_id}")
            return

        relationships = self.get_entity_relationships(test_id, entity_id)

        print("=" * 70)
        print(f"ENTITY NETWORK FOR: {entity['text']} ({entity['entity_type']})")
        print("=" * 70)

        print(f"\nOutgoing Relationships ({len(relationships['as_source'])}):")
        for rel in relationships['as_source']:
            target = self.get_entity_by_id(test_id, rel['target_entity_id'])
            if target:
                print(f"  → {rel['relationship_type']} → {target['text']} ({target['entity_type']})")
                print(f"    Confidence: {rel['confidence']:.3f}")

        print(f"\nIncoming Relationships ({len(relationships['as_target'])}):")
        for rel in relationships['as_target']:
            source = self.get_entity_by_id(test_id, rel['source_entity_id'])
            if source:
                print(f"  ← {rel['relationship_type']} ← {source['text']} ({source['entity_type']})")
                print(f"    Confidence: {rel['confidence']:.3f}")

        print("\n" + "=" * 70)


def main():
    """Main entry point"""
    analyzer = RelationshipAnalyzer()

    # Parse simple command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--export-csv":
            output = sys.argv[2] if len(sys.argv) > 2 else "relationships.csv"
            analyzer.export_to_csv(output)

        elif command == "--test-id":
            if len(sys.argv) < 3:
                print("❌ Error: --test-id requires a test ID argument")
                return
            test_id = sys.argv[2]
            analyzer.print_summary(test_id)

        elif command == "--relationship-type":
            if len(sys.argv) < 3:
                print("❌ Error: --relationship-type requires a type argument")
                return
            rel_type = sys.argv[2]
            relationships = analyzer.filter_relationships(relationship_type=rel_type)
            print(f"\nFound {len(relationships)} relationships of type: {rel_type}")
            for rel in relationships[:10]:
                print(f"  Test: {rel['test_id']}, Confidence: {rel['confidence']:.3f}")

        elif command == "--help":
            print(__doc__)

        else:
            print(f"❌ Unknown command: {command}")
            print("Use --help for usage information")

    else:
        # Default: print summary
        analyzer.print_summary()

        # Print test-by-test breakdown
        print("\nTest-by-Test Breakdown:")
        print("-" * 70)
        for test in analyzer.data['tests']:
            test_id = test['test_id']
            rel_count = len(test.get('relationships', []))
            entity_count = len(test['raw_response']['entities'])
            print(f"\n{test_id}:")
            print(f"  Entities: {entity_count}")
            print(f"  Relationships: {rel_count}")
            print(f"  Ratio: {rel_count/entity_count:.2f} relationships per entity")


if __name__ == "__main__":
    main()
