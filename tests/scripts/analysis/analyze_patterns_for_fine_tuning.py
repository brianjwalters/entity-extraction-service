#!/usr/bin/env python3
"""
Pattern Analysis Script for SaulLM Fine-Tuning Data Generation

This script analyzes the entity extraction service's pattern system to identify
all entity types and citation types that have examples available for fine-tuning.
"""

import os

from utils.pattern_loader import PatternLoader
from models.entities import EntityType, CitationType
import json
from pathlib import Path
from collections import defaultdict, Counter
import yaml

def analyze_patterns_for_fine_tuning():
    """
    Comprehensive analysis of pattern system for SaulLM fine-tuning data.
    """
    print("🔍 Analyzing Entity Extraction Service Pattern System for SaulLM Fine-Tuning")
    print("=" * 80)
    
    # Initialize the pattern loader
    try:
        loader = PatternLoader()
        print(f"✅ PatternLoader initialized successfully")
        print(f"📁 Patterns directory: {loader.patterns_dir}")
    except Exception as e:
        print(f"❌ Failed to initialize PatternLoader: {e}")
        return None
    
    # Get pattern statistics
    stats = loader.get_pattern_statistics()
    print(f"\n📊 Pattern System Overview:")
    print(f"   • Total Pattern Groups: {stats['total_groups']}")
    print(f"   • Total Patterns: {stats['total_patterns']}")
    print(f"   • Entity Types with Patterns: {stats['total_entity_types']}")
    
    # Get all entity type information
    print(f"\n🎯 Analyzing Entity Types and Examples...")
    all_entity_info = loader.get_all_entity_types_info()
    
    # Analyze examples by entity type
    training_ready_types = {}
    insufficient_examples = {}
    no_examples = []
    
    # Get all EntityType enum values
    all_entity_types = set([e.value for e in EntityType])
    
    # Get all CitationType enum values
    all_citation_types = set([c.value for c in CitationType])
    
    print(f"\n📋 EntityType Enum Analysis:")
    print(f"   • Total EntityType enum values: {len(all_entity_types)}")
    print(f"   • Total CitationType enum values: {len(all_citation_types)}")
    
    # Analyze entity types with examples
    for entity_type, info in all_entity_info.items():
        example_count = len(info.get('examples', []))
        
        if example_count >= 5:  # Minimum threshold for training
            training_ready_types[entity_type] = {
                'examples': info['examples'],
                'example_count': example_count,
                'pattern_count': info['pattern_count'],
                'description': info.get('description', ''),
                'average_confidence': info.get('average_confidence', 0.0),
                'jurisdictions': info.get('jurisdictions', []),
                'has_patterns': info.get('has_patterns', False)
            }
        elif example_count > 0:
            insufficient_examples[entity_type] = {
                'example_count': example_count,
                'examples': info['examples'],
                'pattern_count': info['pattern_count'],
                'description': info.get('description', '')
            }
        else:
            no_examples.append(entity_type)
    
    # Check for entity types in enum but not in patterns
    covered_types = set(all_entity_info.keys())
    enum_only_entity_types = all_entity_types - covered_types
    enum_only_citation_types = all_citation_types - covered_types
    
    # Categorize by domain
    domains = {
        'Courts and Judicial': [],
        'Parties and Representatives': [],
        'Legal Professionals': [],
        'Legal Authority': [],
        'Legal Documents': [],
        'Citations': [],
        'Dates and Time': [],
        'Financial and Damages': [],
        'Criminal Law': [],
        'Evidence': [],
        'Legal Concepts': [],
        'Organizations': [],
        'Procedural Elements': [],
        'Miscellaneous': []
    }
    
    # Categorize based on entity type patterns
    for entity_type in training_ready_types.keys():
        if any(term in entity_type.lower() for term in ['court', 'judge', 'magistrate', 'justice']):
            domains['Courts and Judicial'].append(entity_type)
        elif any(term in entity_type.lower() for term in ['plaintiff', 'defendant', 'party', 'appellant']):
            domains['Parties and Representatives'].append(entity_type)
        elif any(term in entity_type.lower() for term in ['attorney', 'law_firm', 'prosecutor', 'counsel']):
            domains['Legal Professionals'].append(entity_type)
        elif any(term in entity_type.lower() for term in ['citation', 'usc', 'cfr', 'case_citation']):
            domains['Citations'].append(entity_type)
        elif any(term in entity_type.lower() for term in ['motion', 'brief', 'complaint', 'order', 'document']):
            domains['Legal Documents'].append(entity_type)
        elif any(term in entity_type.lower() for term in ['date', 'deadline', 'filing', 'hearing']):
            domains['Dates and Time'].append(entity_type)
        elif any(term in entity_type.lower() for term in ['damages', 'monetary', 'fine', 'penalty', 'award']):
            domains['Financial and Damages'].append(entity_type)
        elif any(term in entity_type.lower() for term in ['charge', 'felony', 'sentence', 'conviction']):
            domains['Criminal Law'].append(entity_type)
        elif any(term in entity_type.lower() for term in ['evidence', 'exhibit', 'testimony', 'witness']):
            domains['Evidence'].append(entity_type)
        elif any(term in entity_type.lower() for term in ['statute', 'regulation', 'constitutional', 'ordinance']):
            domains['Legal Authority'].append(entity_type)
        elif any(term in entity_type.lower() for term in ['corporation', 'agency', 'organization', 'government']):
            domains['Organizations'].append(entity_type)
        elif any(term in entity_type.lower() for term in ['procedural', 'jurisdiction', 'venue', 'forum']):
            domains['Procedural Elements'].append(entity_type)
        elif any(term in entity_type.lower() for term in ['doctrine', 'concept', 'standard', 'principle']):
            domains['Legal Concepts'].append(entity_type)
        else:
            domains['Miscellaneous'].append(entity_type)
    
    # Generate comprehensive report
    report = {
        'metadata': {
            'analysis_date': '2025-09-15',
            'pattern_system_stats': stats,
            'total_entity_types_analyzed': len(all_entity_info),
            'total_entity_enum_values': len(all_entity_types),
            'total_citation_enum_values': len(all_citation_types),
            'training_ready_count': len(training_ready_types),
            'insufficient_examples_count': len(insufficient_examples),
            'no_examples_count': len(no_examples),
            'enum_only_entity_types_count': len(enum_only_entity_types),
            'enum_only_citation_types_count': len(enum_only_citation_types)
        },
        'training_ready_entity_types': training_ready_types,
        'insufficient_examples': insufficient_examples,
        'no_examples': no_examples,
        'enum_only_entity_types': list(enum_only_entity_types),
        'enum_only_citation_types': list(enum_only_citation_types),
        'domain_categorization': domains,
        'recommendations': {
            'minimum_examples_threshold': 5,
            'recommended_examples_per_type': 10,
            'priority_types_for_fine_tuning': [],
            'types_needing_more_examples': list(insufficient_examples.keys())
        }
    }
    
    # Identify priority types for fine-tuning
    priority_types = []
    for entity_type, info in training_ready_types.items():
        if (info['example_count'] >= 10 and 
            info['pattern_count'] > 0 and 
            info['average_confidence'] > 0.8):
            priority_types.append({
                'entity_type': entity_type,
                'example_count': info['example_count'],
                'pattern_count': info['pattern_count'],
                'confidence': info['average_confidence']
            })
    
    # Sort by example count and confidence
    priority_types.sort(key=lambda x: (x['example_count'], x['confidence']), reverse=True)
    report['recommendations']['priority_types_for_fine_tuning'] = priority_types[:20]  # Top 20
    
    # Print summary results
    print(f"\n🎯 Fine-Tuning Readiness Summary:")
    print(f"   ✅ Training-Ready Types (≥5 examples): {len(training_ready_types)}")
    print(f"   ⚠️  Insufficient Examples (1-4 examples): {len(insufficient_examples)}")
    print(f"   ❌ No Examples: {len(no_examples)}")
    print(f"   📝 Enum-Only Entity Types: {len(enum_only_entity_types)}")
    print(f"   📝 Enum-Only Citation Types: {len(enum_only_citation_types)}")
    
    print(f"\n🏆 Top Training-Ready Entity Types:")
    for i, priority_type in enumerate(priority_types[:10], 1):
        print(f"   {i:2d}. {priority_type['entity_type']:30} "
              f"({priority_type['example_count']:2d} examples, "
              f"conf: {priority_type['confidence']:.2f})")
    
    print(f"\n📊 Domain Distribution (Training-Ready Types):")
    for domain, types in domains.items():
        if types:
            print(f"   • {domain:25}: {len(types):2d} types")
    
    # Calculate total examples available
    total_examples = sum(info['example_count'] for info in training_ready_types.values())
    print(f"\n📈 Example Statistics:")
    print(f"   • Total Examples Available: {total_examples}")
    print(f"   • Average Examples per Type: {total_examples / len(training_ready_types):.1f}")
    print(f"   • Types with 10+ Examples: {sum(1 for info in training_ready_types.values() if info['example_count'] >= 10)}")
    
    return report

def main():
    """Main execution function."""
    report = analyze_patterns_for_fine_tuning()
    
    if report:
        # Save detailed report
        output_file = Path(__file__).parent / "fine_tuning_analysis_report.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n💾 Detailed report saved to: {output_file}")
        
        # Save training data summary
        training_data_file = Path(__file__).parent / "training_data_summary.json"
        training_summary = {
            'entity_types_with_examples': {
                entity_type: {
                    'examples': info['examples'][:10],  # Limit to 10 examples per type
                    'example_count': info['example_count'],
                    'description': info['description']
                }
                for entity_type, info in report['training_ready_entity_types'].items()
            },
            'total_training_ready_types': len(report['training_ready_entity_types']),
            'total_examples': sum(info['example_count'] for info in report['training_ready_entity_types'].values()),
            'recommended_for_immediate_training': [
                t['entity_type'] for t in report['recommendations']['priority_types_for_fine_tuning'][:10]
            ]
        }
        
        with open(training_data_file, 'w') as f:
            json.dump(training_summary, f, indent=2)
        
        print(f"📋 Training data summary saved to: {training_data_file}")
        print(f"\n✨ Analysis complete! Ready for SaulLM fine-tuning data generation.")
    
    return report

if __name__ == "__main__":
    main()