#!/usr/bin/env python3
"""
Compare results between base and fine-tuned SaulLM models.
Analyzes whether fine-tuning is necessary or if enhanced prompts are sufficient.
"""

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import pandas as pd

class FineTuningComparison:
    def __init__(self):
        self.results = {}
        
    def load_results(self):
        """Load all available test results."""
        results_dirs = {
            "baseline": "tests/results/baselines",
            "fine_tuned": "tests/results/fine_tuned", 
            "base_enhanced": "tests/results/base_model"
        }
        
        for result_type, dir_path in results_dirs.items():
            path = Path(dir_path)
            if path.exists():
                # Get most recent file
                files = sorted(path.glob("*.json"), key=lambda x: x.stat().st_mtime)
                if files:
                    with open(files[-1], 'r') as f:
                        self.results[result_type] = json.load(f)
                        print(f"Loaded {result_type}: {files[-1].name}")
                        
    def analyze_results(self):
        """Analyze and compare results."""
        comparison = {}
        
        for name, data in self.results.items():
            if 'statistics' in data:
                stats = data['statistics']
                comparison[name] = {
                    'total_entities': stats.get('total_entities', 0),
                    'unique_types': stats.get('unique_entity_types', 0),
                    'relationships': stats.get('total_relationships', 0),
                    'avg_per_chunk': stats.get('avg_entities_per_chunk', 0),
                    'processing_time': stats.get('total_processing_time', 0)
                }
            elif 'improvements' in data:
                # Handle comparison format
                comparison[name] = {
                    'total_entities': data['improvements'].get('entity_count', {}).get('after', 0),
                    'unique_types': data['improvements'].get('type_diversity', {}).get('after', 0)
                }
            else:
                # Handle simple format
                comparison[name] = {
                    'total_entities': len(data.get('entities', [])),
                    'unique_types': len(set(e.get('entity_type') for e in data.get('entities', [])))
                }
                
        return comparison
        
    def generate_report(self):
        """Generate comparison report."""
        comparison = self.analyze_results()
        
        print("\n" + "="*70)
        print("FINE-TUNING VS ENHANCED PROMPT COMPARISON REPORT")
        print("="*70)
        
        # Create DataFrame for comparison
        df = pd.DataFrame.from_dict(comparison, orient='index')
        
        print("\nPerformance Metrics:")
        print("-"*50)
        print(df.to_string())
        
        # Analysis
        print("\n\nAnalysis:")
        print("-"*50)
        
        if 'baseline' in comparison and 'fine_tuned' in comparison:
            baseline_entities = comparison['baseline']['total_entities']
            fine_tuned_entities = comparison['fine_tuned']['total_entities']
            
            improvement = ((fine_tuned_entities - baseline_entities) / baseline_entities) * 100
            print(f"Fine-tuning improvement over baseline: {improvement:+.1f}%")
            
        if 'baseline' in comparison and 'base_enhanced' in comparison:
            baseline_entities = comparison['baseline']['total_entities']
            enhanced_entities = comparison['base_enhanced']['total_entities']
            
            improvement = ((enhanced_entities - baseline_entities) / baseline_entities) * 100
            print(f"Enhanced prompt improvement over baseline: {improvement:+.1f}%")
            
        if 'fine_tuned' in comparison and 'base_enhanced' in comparison:
            fine_tuned_entities = comparison['fine_tuned']['total_entities']
            enhanced_entities = comparison['base_enhanced']['total_entities']
            
            if enhanced_entities > 0:
                ratio = fine_tuned_entities / enhanced_entities
                print(f"\nFine-tuned vs Enhanced prompt ratio: {ratio:.2f}x")
                
                if ratio < 1.2:
                    print("\n🔍 FINDING: Fine-tuning provides minimal improvement over enhanced prompts.")
                    print("   Enhanced prompting may be sufficient for this use case.")
                elif ratio > 2.0:
                    print("\n🔍 FINDING: Fine-tuning significantly outperforms enhanced prompts.")
                    print("   Fine-tuning is recommended for optimal performance.")
                else:
                    print("\n🔍 FINDING: Fine-tuning provides moderate improvement.")
                    print("   Consider cost/benefit trade-off for your specific needs.")
                    
        # Recommendations
        print("\n\nRecommendations:")
        print("-"*50)
        
        if 'base_enhanced' in comparison:
            enhanced = comparison['base_enhanced']
            if enhanced['total_entities'] > 50:
                print("✅ Enhanced prompting shows good performance")
                print("   - Consider using base model with enhanced prompts for:")
                print("     • Quick prototyping")
                print("     • Cases where model updates are frequent")
                print("     • When training resources are limited")
            else:
                print("⚠️ Enhanced prompting shows limited performance")
                print("   - Fine-tuning is recommended for production use")
                
        print("\n" + "="*70)
        
        # Save report
        report = {
            'timestamp': datetime.now().isoformat(),
            'comparison': comparison,
            'recommendations': self.generate_recommendations(comparison)
        }
        
        output_file = Path('fine_tuning_comparison_report.json')
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"\nReport saved to: {output_file}")
        
    def generate_recommendations(self, comparison: Dict) -> Dict:
        """Generate specific recommendations based on results."""
        recommendations = {
            'use_fine_tuning': False,
            'use_enhanced_prompts': False,
            'reasoning': []
        }
        
        if 'base_enhanced' in comparison and 'fine_tuned' in comparison:
            enhanced = comparison['base_enhanced']['total_entities']
            fine_tuned = comparison['fine_tuned']['total_entities']
            
            if enhanced > fine_tuned * 0.8:  # Enhanced is within 80% of fine-tuned
                recommendations['use_enhanced_prompts'] = True
                recommendations['reasoning'].append(
                    "Enhanced prompts achieve comparable performance to fine-tuning"
                )
            else:
                recommendations['use_fine_tuning'] = True
                recommendations['reasoning'].append(
                    "Fine-tuning provides significantly better entity extraction"
                )
                
        return recommendations

def main():
    comparator = FineTuningComparison()
    comparator.load_results()
    comparator.generate_report()

if __name__ == "__main__":
    main()