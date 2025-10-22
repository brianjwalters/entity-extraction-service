#!/usr/bin/env python3
"""
Entity type analyzer for Dobbs.pdf extraction results.
Tracks entity type performance, calculates precision/recall, and identifies gaps.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import logging
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class EntityTypeMetrics:
    """Metrics for a specific entity type."""
    entity_type: str
    total_found: int = 0
    unique_values: int = 0
    strategies_found_by: List[str] = None
    confidence_avg: float = 0.0
    confidence_min: float = 0.0
    confidence_max: float = 0.0
    sample_values: List[str] = None
    extraction_methods: Dict[str, int] = None
    
    def __post_init__(self):
        if self.strategies_found_by is None:
            self.strategies_found_by = []
        if self.sample_values is None:
            self.sample_values = []
        if self.extraction_methods is None:
            self.extraction_methods = {}

class EntityTypeAnalyzer:
    """Analyzer for entity type performance across extraction strategies."""
    
    # Define expected entity types for Dobbs (Supreme Court case)
    DOBBS_EXPECTED_TYPES = {
        'COURT', 'JUDGE', 'CASE_CITATION', 'STATUTE_CITATION',
        'CONSTITUTIONAL_CITATION', 'OPINION', 'LEGAL_DOCTRINE',
        'CONSTITUTIONAL_RIGHT', 'PRECEDENT', 'HOLDING', 'RULING',
        'DISSENT', 'CONCURRENCE', 'APPELLANT', 'APPELLEE',
        'ATTORNEY', 'LAW_FIRM', 'AMICUS_CURIAE', 'DATE',
        'LEGAL_ISSUE', 'LEGAL_STANDARD', 'LEGAL_PRINCIPLE'
    }
    
    # High-value entity types for legal documents
    HIGH_VALUE_TYPES = {
        'CASE_CITATION', 'STATUTE_CITATION', 'CONSTITUTIONAL_CITATION',
        'COURT', 'JUDGE', 'HOLDING', 'RULING', 'LEGAL_DOCTRINE',
        'PRECEDENT', 'CONSTITUTIONAL_RIGHT'
    }
    
    def __init__(self, results_file: Optional[str] = None):
        self.results_dir = Path("/srv/luris/be/entity-extraction-service/tests/dobbs_testing/results")
        self.results_dir.mkdir(exist_ok=True)
        
        if results_file:
            self.load_results(results_file)
        else:
            self.results = None
        
        self.entity_type_data = defaultdict(lambda: EntityTypeMetrics(entity_type=""))
    
    def load_results(self, results_file: str):
        """Load test results from JSON file."""
        try:
            with open(results_file, 'r') as f:
                self.results = json.load(f)
            logger.info(f"Loaded results from {results_file}")
            self._process_results()
        except Exception as e:
            logger.error(f"Error loading results: {e}")
            self.results = None
    
    def load_latest_results(self):
        """Load the most recent test results."""
        try:
            json_files = list(self.results_dir.glob("dobbs_test_*.json"))
            if not json_files:
                logger.error("No test results found")
                return None
            
            latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
            self.load_results(str(latest_file))
            return latest_file
        except Exception as e:
            logger.error(f"Error loading latest results: {e}")
            return None
    
    def _process_results(self):
        """Process loaded results to extract entity type data."""
        if not self.results:
            return
        
        modes = self.results.get("modes_tested", [])
        
        for mode_result in modes:
            if not mode_result.get("success"):
                continue
            
            strategy_name = f"{mode_result['mode']}_{mode_result['strategy']}"
            
            # Process entity type counts
            for entity_type, count in mode_result.get("entity_type_counts", {}).items():
                if entity_type not in self.entity_type_data:
                    self.entity_type_data[entity_type] = EntityTypeMetrics(entity_type=entity_type)
                
                metrics = self.entity_type_data[entity_type]
                metrics.total_found += count
                
                if strategy_name not in metrics.strategies_found_by:
                    metrics.strategies_found_by.append(strategy_name)
                
                if strategy_name not in metrics.extraction_methods:
                    metrics.extraction_methods[strategy_name] = 0
                metrics.extraction_methods[strategy_name] += count
            
            # Process sample entities for detailed metrics
            for entity in mode_result.get("sample_entities", []):
                entity_type = entity.get("entity_type")
                if entity_type:
                    metrics = self.entity_type_data[entity_type]
                    
                    # Update confidence scores
                    if "confidence" in entity:
                        conf = entity["confidence"]
                        if metrics.confidence_min == 0 or conf < metrics.confidence_min:
                            metrics.confidence_min = conf
                        if conf > metrics.confidence_max:
                            metrics.confidence_max = conf
                    
                    # Collect sample values
                    entity_text = entity.get("entity_text", "")
                    if entity_text and entity_text not in metrics.sample_values:
                        metrics.sample_values.append(entity_text[:100])  # Limit length
                        if len(metrics.sample_values) > 10:
                            metrics.sample_values = metrics.sample_values[:10]
        
        # Calculate averages and unique counts
        for entity_type, metrics in self.entity_type_data.items():
            metrics.unique_values = len(set(metrics.sample_values))
            
            # Calculate average confidence (simplified)
            if metrics.confidence_min > 0 and metrics.confidence_max > 0:
                metrics.confidence_avg = (metrics.confidence_min + metrics.confidence_max) / 2
    
    def calculate_entity_type_scores(self) -> Dict[str, Dict[str, float]]:
        """Calculate performance scores for each entity type."""
        scores = {}
        
        total_strategies = len(set(
            strategy 
            for mode in self.results.get("modes_tested", []) 
            if mode.get("success")
            for strategy in [f"{mode['mode']}_{mode['strategy']}"]
        ))
        
        for entity_type, metrics in self.entity_type_data.items():
            coverage = len(metrics.strategies_found_by) / max(total_strategies, 1)
            
            # Calculate importance weight
            importance = 1.0
            if entity_type in self.HIGH_VALUE_TYPES:
                importance = 2.0
            if entity_type in self.DOBBS_EXPECTED_TYPES:
                importance *= 1.5
            
            # Calculate overall score
            score = {
                "coverage": coverage,
                "total_found": metrics.total_found,
                "importance": importance,
                "confidence_avg": metrics.confidence_avg,
                "strategies_count": len(metrics.strategies_found_by),
                "overall_score": coverage * importance * (1 + metrics.confidence_avg)
            }
            
            scores[entity_type] = score
        
        return scores
    
    def identify_gaps(self) -> Dict[str, Any]:
        """Identify gaps in entity type extraction."""
        gaps = {
            "missing_expected": [],
            "low_coverage": [],
            "low_confidence": [],
            "single_strategy_only": [],
            "recommendations": []
        }
        
        # Check for missing expected types
        found_types = set(self.entity_type_data.keys())
        missing_expected = self.DOBBS_EXPECTED_TYPES - found_types
        gaps["missing_expected"] = sorted(list(missing_expected))
        
        # Check for low coverage types
        scores = self.calculate_entity_type_scores()
        
        for entity_type, score in scores.items():
            if score["coverage"] < 0.5:
                gaps["low_coverage"].append({
                    "type": entity_type,
                    "coverage": score["coverage"],
                    "found_by": self.entity_type_data[entity_type].strategies_found_by
                })
            
            if score["confidence_avg"] < 0.7 and score["confidence_avg"] > 0:
                gaps["low_confidence"].append({
                    "type": entity_type,
                    "confidence": score["confidence_avg"]
                })
            
            if score["strategies_count"] == 1:
                gaps["single_strategy_only"].append({
                    "type": entity_type,
                    "strategy": self.entity_type_data[entity_type].strategies_found_by[0]
                })
        
        # Generate recommendations
        if gaps["missing_expected"]:
            gaps["recommendations"].append(
                f"Critical entity types missing: {', '.join(gaps['missing_expected'][:5])}. "
                "Consider enhancing patterns or prompts for these types."
            )
        
        if len(gaps["low_coverage"]) > 5:
            gaps["recommendations"].append(
                f"{len(gaps['low_coverage'])} entity types have low coverage (<50%). "
                "Consider using hybrid mode for better coverage."
            )
        
        if gaps["single_strategy_only"]:
            gaps["recommendations"].append(
                f"{len(gaps['single_strategy_only'])} entity types found by only one strategy. "
                "These may be unreliable or strategy-specific."
            )
        
        return gaps
    
    def compare_strategy_performance(self) -> pd.DataFrame:
        """Compare performance across strategies for each entity type."""
        if not self.results:
            return pd.DataFrame()
        
        # Build comparison matrix
        strategies = []
        entity_types = sorted(self.entity_type_data.keys())
        
        for mode in self.results.get("modes_tested", []):
            if mode.get("success"):
                strategies.append(f"{mode['mode']}_{mode['strategy']}")
        
        # Create matrix
        matrix = pd.DataFrame(index=entity_types, columns=strategies)
        
        for entity_type, metrics in self.entity_type_data.items():
            for strategy, count in metrics.extraction_methods.items():
                if strategy in matrix.columns:
                    matrix.at[entity_type, strategy] = count
        
        matrix = matrix.fillna(0).astype(int)
        
        # Add summary columns
        matrix['Total'] = matrix.sum(axis=1)
        matrix['Strategies'] = matrix.apply(lambda row: sum(row[col] > 0 for col in strategies), axis=1)
        matrix['Avg_Per_Strategy'] = matrix['Total'] / matrix['Strategies']
        
        # Sort by total count
        matrix = matrix.sort_values('Total', ascending=False)
        
        return matrix
    
    def generate_analysis_report(self) -> str:
        """Generate comprehensive entity type analysis report."""
        if not self.results:
            return "No results loaded"
        
        md = "# Entity Type Analysis Report\n\n"
        md += f"**Test ID:** {self.results.get('test_id', 'Unknown')}\n"
        md += f"**Document:** Dobbs.pdf\n"
        md += f"**Generated:** {datetime.now().isoformat()}\n\n"
        
        # Summary statistics
        md += "## Summary Statistics\n\n"
        md += f"- **Total Entity Types Found:** {len(self.entity_type_data)}\n"
        md += f"- **Expected Types Found:** {len(self.DOBBS_EXPECTED_TYPES & set(self.entity_type_data.keys()))}/{len(self.DOBBS_EXPECTED_TYPES)}\n"
        md += f"- **High-Value Types Found:** {len(self.HIGH_VALUE_TYPES & set(self.entity_type_data.keys()))}/{len(self.HIGH_VALUE_TYPES)}\n\n"
        
        # Performance scores
        scores = self.calculate_entity_type_scores()
        top_performers = sorted(scores.items(), key=lambda x: x[1]["overall_score"], reverse=True)[:20]
        
        md += "## Top Performing Entity Types\n\n"
        md += "| Rank | Entity Type | Total Found | Coverage | Confidence | Score |\n"
        md += "|------|-------------|-------------|----------|------------|-------|\n"
        
        for i, (entity_type, score) in enumerate(top_performers, 1):
            md += f"| {i} | {entity_type} | {score['total_found']} | "
            md += f"{score['coverage']:.1%} | {score['confidence_avg']:.3f} | "
            md += f"{score['overall_score']:.2f} |\n"
        
        # Gap analysis
        gaps = self.identify_gaps()
        
        md += "\n## Gap Analysis\n\n"
        
        if gaps["missing_expected"]:
            md += "### Missing Expected Entity Types\n\n"
            md += "These entity types were expected in Dobbs.pdf but not found:\n\n"
            for entity_type in gaps["missing_expected"]:
                md += f"- **{entity_type}**\n"
        
        if gaps["low_coverage"]:
            md += "\n### Low Coverage Entity Types\n\n"
            md += "Found by less than 50% of strategies:\n\n"
            for item in gaps["low_coverage"][:10]:
                md += f"- **{item['type']}**: {item['coverage']:.1%} coverage "
                md += f"(found by: {', '.join(item['found_by'])})\n"
        
        if gaps["low_confidence"]:
            md += "\n### Low Confidence Entity Types\n\n"
            md += "Average confidence below 70%:\n\n"
            for item in gaps["low_confidence"][:10]:
                md += f"- **{item['type']}**: {item['confidence']:.3f} confidence\n"
        
        # Strategy comparison
        md += "\n## Strategy Comparison Matrix\n\n"
        
        comparison_df = self.compare_strategy_performance()
        if not comparison_df.empty:
            # Show top entity types
            top_types = comparison_df.head(25)
            
            md += "Top 25 entity types by occurrence:\n\n"
            md += "| Entity Type | " + " | ".join(comparison_df.columns[:-3]) + " | Total |\n"
            md += "|-------------|" + "|".join(["-----" for _ in comparison_df.columns[:-2]]) + "|\n"
            
            for entity_type, row in top_types.iterrows():
                md += f"| {entity_type} "
                for col in comparison_df.columns[:-3]:
                    value = row[col]
                    md += f"| {int(value) if value > 0 else '-'} "
                md += f"| {int(row['Total'])} |\n"
        
        # Sample values for top entity types
        md += "\n## Sample Entity Values\n\n"
        
        for entity_type, score in top_performers[:10]:
            metrics = self.entity_type_data[entity_type]
            if metrics.sample_values:
                md += f"### {entity_type}\n"
                for value in metrics.sample_values[:5]:
                    md += f"- {value}\n"
                md += "\n"
        
        # Recommendations
        if gaps["recommendations"]:
            md += "\n## Recommendations\n\n"
            for i, rec in enumerate(gaps["recommendations"], 1):
                md += f"{i}. {rec}\n"
        
        return md
    
    def save_analysis(self, output_format: str = "both"):
        """Save analysis results."""
        if not self.results:
            logger.error("No results to analyze")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Prepare analysis data
        analysis_data = {
            "test_id": self.results.get("test_id"),
            "timestamp": timestamp,
            "entity_type_metrics": {
                entity_type: asdict(metrics)
                for entity_type, metrics in self.entity_type_data.items()
            },
            "performance_scores": self.calculate_entity_type_scores(),
            "gaps": self.identify_gaps(),
            "comparison_matrix": self.compare_strategy_performance().to_dict() if not self.compare_strategy_performance().empty else {}
        }
        
        # Save JSON
        if output_format in ["json", "both"]:
            json_file = self.results_dir / f"entity_type_analysis_{timestamp}.json"
            with open(json_file, 'w') as f:
                json.dump(analysis_data, f, indent=2, default=str)
            logger.info(f"JSON analysis saved to: {json_file}")
        
        # Save Markdown
        if output_format in ["markdown", "both"]:
            md_file = self.results_dir / f"entity_type_analysis_{timestamp}.md"
            md_content = self.generate_analysis_report()
            
            with open(md_file, 'w') as f:
                f.write(md_content)
            logger.info(f"Markdown analysis saved to: {md_file}")
        
        # Print summary
        print(f"\n{'='*60}")
        print("Entity Type Analysis Complete")
        print(f"{'='*60}")
        print(f"Total entity types found: {len(self.entity_type_data)}")
        print(f"Expected types coverage: {len(self.DOBBS_EXPECTED_TYPES & set(self.entity_type_data.keys()))}/{len(self.DOBBS_EXPECTED_TYPES)}")
        
        gaps = self.identify_gaps()
        if gaps["missing_expected"]:
            print(f"\nMissing expected types: {', '.join(gaps['missing_expected'][:5])}")
        
        print(f"\nReports saved to: {self.results_dir}")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Entity type analyzer for Dobbs extraction")
    parser.add_argument("--results-file", help="Path to test results JSON file")
    parser.add_argument("--latest", action="store_true", help="Use latest test results")
    parser.add_argument("--format", choices=["json", "markdown", "both"], default="both",
                       help="Output format for analysis")
    
    args = parser.parse_args()
    
    analyzer = EntityTypeAnalyzer()
    
    if args.results_file:
        analyzer.load_results(args.results_file)
    elif args.latest:
        file = analyzer.load_latest_results()
        if file:
            print(f"Loaded latest results from: {file}")
    else:
        print("Please specify --results-file or --latest")
        sys.exit(1)
    
    if analyzer.results:
        analyzer.save_analysis(output_format=args.format)
    else:
        print("No results to analyze")

if __name__ == "__main__":
    main()