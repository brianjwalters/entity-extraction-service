#!/usr/bin/env python3
"""
Visual quality inspector for Dobbs.pdf extraction results.
Creates visual comparisons, coverage matrices, and quality heatmaps.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VisualQualityInspector:
    """Visual comparison and analysis tool for extraction results."""
    
    def __init__(self, results_file: Optional[str] = None):
        self.results_dir = Path("/srv/luris/be/entity-extraction-service/tests/dobbs_testing/results")
        self.results_dir.mkdir(exist_ok=True)
        
        if results_file:
            self.load_results(results_file)
        else:
            self.results = None
    
    def load_results(self, results_file: str):
        """Load test results from JSON file."""
        try:
            with open(results_file, 'r') as f:
                self.results = json.load(f)
            logger.info(f"Loaded results from {results_file}")
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
    
    def create_strategy_comparison(self) -> str:
        """Create a side-by-side strategy comparison in Markdown."""
        if not self.results:
            return "No results loaded"
        
        modes = self.results.get("modes_tested", [])
        successful = [m for m in modes if m.get("success")]
        
        if not successful:
            return "No successful tests to compare"
        
        # Create comparison table
        md = "# Strategy Comparison Report\n\n"
        md += f"**Test ID:** {self.results.get('test_id', 'Unknown')}\n"
        md += f"**Document:** {self.results.get('document', 'Unknown')}\n"
        md += f"**Date:** {self.results.get('started_at', 'Unknown')}\n\n"
        
        md += "## Performance Overview\n\n"
        md += "| Mode | Strategy | Entities | Citations | Types Found | Coverage % | Time (s) | Avg Confidence |\n"
        md += "|------|----------|----------|-----------|-------------|------------|----------|----------------|\n"
        
        for mode in successful:
            md += f"| {mode['mode']} | {mode['strategy']} | "
            md += f"{mode.get('total_entities', 0)} | "
            md += f"{mode.get('total_citations', 0)} | "
            md += f"{mode.get('unique_entity_types', 0)} | "
            md += f"{mode.get('entity_type_coverage', 0):.1f}% | "
            md += f"{mode.get('elapsed_time', 0):.2f} | "
            md += f"{mode.get('average_confidence', 0):.3f} |\n"
        
        # Add entity type distribution
        md += "\n## Entity Type Distribution\n\n"
        
        # Collect all entity types found across all modes
        all_types = set()
        for mode in successful:
            all_types.update(mode.get('entity_type_counts', {}).keys())
        
        if all_types:
            md += "| Entity Type | " + " | ".join([f"{m['mode']}_{m['strategy']}" for m in successful]) + " |\n"
            md += "|-------------|" + "|".join(["--------" for _ in successful]) + "|\n"
            
            for entity_type in sorted(all_types)[:50]:  # Top 50 types
                md += f"| {entity_type} "
                for mode in successful:
                    count = mode.get('entity_type_counts', {}).get(entity_type, 0)
                    md += f"| {count} "
                md += "|\n"
        
        # Add best performers
        md += "\n## Best Performers\n\n"
        
        if successful:
            best_coverage = max(successful, key=lambda x: x.get('entity_type_coverage', 0))
            most_entities = max(successful, key=lambda x: x.get('total_entities', 0))
            fastest = min(successful, key=lambda x: x.get('elapsed_time', float('inf')))
            
            md += f"- **Best Coverage:** {best_coverage['mode']}_{best_coverage['strategy']} "
            md += f"({best_coverage['entity_type_coverage']:.1f}% - {best_coverage['unique_entity_types']} types)\n"
            
            md += f"- **Most Entities:** {most_entities['mode']}_{most_entities['strategy']} "
            md += f"({most_entities['total_entities']} entities)\n"
            
            md += f"- **Fastest:** {fastest['mode']}_{fastest['strategy']} "
            md += f"({fastest['elapsed_time']:.2f} seconds)\n"
        
        return md
    
    def create_coverage_matrix(self) -> str:
        """Create an entity type coverage matrix."""
        if not self.results:
            return "No results loaded"
        
        coverage = self.results.get("entity_type_coverage_summary", {})
        if not coverage:
            return "No coverage data available"
        
        md = "# Entity Type Coverage Matrix\n\n"
        md += f"**Total Entity Types:** {len(coverage)}\n\n"
        
        # Group by coverage level
        fully_covered = []  # Found by all strategies
        partially_covered = []  # Found by some strategies
        not_covered = []  # Not found by any strategy
        
        modes = self.results.get("modes_tested", [])
        successful = [m for m in modes if m.get("success")]
        num_strategies = len(successful)
        
        for entity_type, data in coverage.items():
            found_by = data.get("found_by", [])
            if len(found_by) == num_strategies and num_strategies > 0:
                fully_covered.append((entity_type, data))
            elif len(found_by) > 0:
                partially_covered.append((entity_type, data))
            else:
                not_covered.append((entity_type, data))
        
        # Report coverage levels
        md += f"## Coverage Summary\n\n"
        md += f"- **Fully Covered (found by all):** {len(fully_covered)} types\n"
        md += f"- **Partially Covered:** {len(partially_covered)} types\n"
        md += f"- **Not Covered:** {len(not_covered)} types\n\n"
        
        # Show fully covered types
        if fully_covered:
            md += "## Fully Covered Entity Types\n\n"
            md += "| Entity Type | Total Count | Found By |\n"
            md += "|-------------|-------------|----------|\n"
            
            for entity_type, data in sorted(fully_covered, key=lambda x: x[1]['total_count'], reverse=True)[:20]:
                md += f"| {entity_type} | {data['total_count']} | All strategies |\n"
        
        # Show partially covered types
        if partially_covered:
            md += "\n## Partially Covered Entity Types\n\n"
            md += "| Entity Type | Total Count | Coverage | Found By |\n"
            md += "|-------------|-------------|----------|----------|\n"
            
            for entity_type, data in sorted(partially_covered, key=lambda x: len(x[1]['found_by']), reverse=True)[:30]:
                coverage_pct = (len(data['found_by']) / num_strategies * 100) if num_strategies > 0 else 0
                found_by_str = ", ".join(data['found_by'][:3])
                if len(data['found_by']) > 3:
                    found_by_str += f" (+{len(data['found_by'])-3} more)"
                md += f"| {entity_type} | {data['total_count']} | {coverage_pct:.0f}% | {found_by_str} |\n"
        
        # Show not covered types
        if not_covered:
            md += "\n## Not Covered Entity Types\n\n"
            md += "These entity types were not found by any strategy:\n\n"
            for entity_type, _ in not_covered[:50]:
                md += f"- {entity_type}\n"
        
        return md
    
    def create_confidence_distribution(self) -> str:
        """Create confidence score distribution analysis."""
        if not self.results:
            return "No results loaded"
        
        md = "# Confidence Score Distribution\n\n"
        
        modes = self.results.get("modes_tested", [])
        successful = [m for m in modes if m.get("success")]
        
        if not successful:
            return md + "No successful tests\n"
        
        md += "## Confidence Statistics by Strategy\n\n"
        md += "| Strategy | Avg Confidence | Min | Max | Std Dev | Entities w/ Confidence |\n"
        md += "|----------|----------------|-----|-----|---------|------------------------|\n"
        
        for mode in successful:
            conf_dist = mode.get('confidence_distribution', {})
            avg_conf = mode.get('average_confidence', 0)
            
            # Calculate std dev from sample entities if available
            sample_entities = mode.get('sample_entities', [])
            confidences = [e.get('confidence', 0) for e in sample_entities if 'confidence' in e]
            std_dev = np.std(confidences) if confidences else 0
            
            md += f"| {mode['mode']}_{mode['strategy']} | "
            md += f"{avg_conf:.3f} | "
            md += f"{conf_dist.get('min', 0):.3f} | "
            md += f"{conf_dist.get('max', 0):.3f} | "
            md += f"{std_dev:.3f} | "
            md += f"{conf_dist.get('count_with_confidence', 0)} |\n"
        
        # Add confidence buckets
        md += "\n## Confidence Buckets\n\n"
        
        for mode in successful:
            md += f"\n### {mode['mode']}_{mode['strategy']}\n\n"
            
            sample_entities = mode.get('sample_entities', [])
            if sample_entities:
                # Create confidence buckets
                buckets = {
                    "Very High (0.9-1.0)": [],
                    "High (0.8-0.9)": [],
                    "Medium (0.7-0.8)": [],
                    "Low (0.6-0.7)": [],
                    "Very Low (<0.6)": []
                }
                
                for entity in sample_entities:
                    if 'confidence' in entity:
                        conf = entity['confidence']
                        text = entity.get('entity_text', 'Unknown')[:50]
                        entity_type = entity.get('entity_type', 'Unknown')
                        
                        if conf >= 0.9:
                            buckets["Very High (0.9-1.0)"].append(f"{text} ({entity_type})")
                        elif conf >= 0.8:
                            buckets["High (0.8-0.9)"].append(f"{text} ({entity_type})")
                        elif conf >= 0.7:
                            buckets["Medium (0.7-0.8)"].append(f"{text} ({entity_type})")
                        elif conf >= 0.6:
                            buckets["Low (0.6-0.7)"].append(f"{text} ({entity_type})")
                        else:
                            buckets["Very Low (<0.6)"].append(f"{text} ({entity_type})")
                
                for bucket_name, entities in buckets.items():
                    if entities:
                        md += f"**{bucket_name}:** {len(entities)} entities\n"
                        for entity in entities[:3]:  # Show first 3 examples
                            md += f"  - {entity}\n"
                        if len(entities) > 3:
                            md += f"  - ... and {len(entities)-3} more\n"
                        md += "\n"
        
        return md
    
    def create_quality_heatmap_data(self) -> Dict[str, Any]:
        """Create data for quality heatmap visualization."""
        if not self.results:
            return {}
        
        modes = self.results.get("modes_tested", [])
        successful = [m for m in modes if m.get("success")]
        
        if not successful:
            return {}
        
        # Create quality metrics matrix
        metrics = [
            "entity_type_coverage",
            "total_entities",
            "total_citations",
            "unique_entity_types",
            "average_confidence",
            "elapsed_time"
        ]
        
        heatmap_data = {
            "strategies": [],
            "metrics": metrics,
            "values": [],
            "normalized_values": []
        }
        
        # Collect raw values
        for mode in successful:
            strategy_name = f"{mode['mode']}_{mode['strategy']}"
            heatmap_data["strategies"].append(strategy_name)
            
            values = []
            for metric in metrics:
                if metric == "elapsed_time":
                    # Invert time (lower is better)
                    value = 1.0 / (mode.get(metric, 1) + 0.1)
                else:
                    value = mode.get(metric, 0)
                values.append(value)
            
            heatmap_data["values"].append(values)
        
        # Normalize values (0-1 scale)
        values_array = np.array(heatmap_data["values"])
        if values_array.size > 0:
            min_vals = values_array.min(axis=0)
            max_vals = values_array.max(axis=0)
            
            # Avoid division by zero
            ranges = max_vals - min_vals
            ranges[ranges == 0] = 1
            
            normalized = (values_array - min_vals) / ranges
            heatmap_data["normalized_values"] = normalized.tolist()
        
        return heatmap_data
    
    def generate_comprehensive_report(self, output_format: str = "both") -> None:
        """Generate comprehensive report in JSON and/or Markdown format."""
        if not self.results:
            logger.error("No results loaded")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create comprehensive analysis
        analysis = {
            "test_id": self.results.get("test_id"),
            "document": self.results.get("document"),
            "timestamp": timestamp,
            "strategy_comparison": self.create_strategy_comparison(),
            "coverage_matrix": self.create_coverage_matrix(),
            "confidence_distribution": self.create_confidence_distribution(),
            "quality_heatmap_data": self.create_quality_heatmap_data(),
            "aggregate_metrics": self.results.get("aggregate_metrics", {})
        }
        
        # Save JSON report
        if output_format in ["json", "both"]:
            json_file = self.results_dir / f"visual_analysis_{timestamp}.json"
            with open(json_file, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            logger.info(f"JSON report saved to: {json_file}")
        
        # Save Markdown report
        if output_format in ["markdown", "both"]:
            md_file = self.results_dir / f"visual_analysis_{timestamp}.md"
            
            md_content = "# Dobbs.pdf Extraction Visual Quality Analysis\n\n"
            md_content += f"Generated: {datetime.now().isoformat()}\n\n"
            md_content += "---\n\n"
            
            md_content += analysis["strategy_comparison"]
            md_content += "\n---\n\n"
            md_content += analysis["coverage_matrix"]
            md_content += "\n---\n\n"
            md_content += analysis["confidence_distribution"]
            
            # Add quality heatmap as table
            md_content += "\n---\n\n"
            md_content += "# Quality Metrics Heatmap\n\n"
            
            heatmap = analysis["quality_heatmap_data"]
            if heatmap and "strategies" in heatmap:
                md_content += "| Strategy | " + " | ".join(heatmap["metrics"]) + " |\n"
                md_content += "|----------|" + "|".join(["----------" for _ in heatmap["metrics"]]) + "|\n"
                
                for i, strategy in enumerate(heatmap["strategies"]):
                    md_content += f"| {strategy} "
                    for j, value in enumerate(heatmap["normalized_values"][i]):
                        # Use emoji indicators for normalized values
                        if value >= 0.8:
                            indicator = "🟢"
                        elif value >= 0.6:
                            indicator = "🟡"
                        elif value >= 0.4:
                            indicator = "🟠"
                        else:
                            indicator = "🔴"
                        md_content += f"| {indicator} {value:.2f} "
                    md_content += "|\n"
            
            # Add summary statistics
            md_content += "\n---\n\n"
            md_content += "# Summary Statistics\n\n"
            
            metrics = analysis["aggregate_metrics"]
            md_content += f"- **Total Tests:** {metrics.get('total_tests', 0)}\n"
            md_content += f"- **Successful:** {metrics.get('successful_tests', 0)}\n"
            md_content += f"- **Failed:** {metrics.get('failed_tests', 0)}\n"
            md_content += f"- **Overall Coverage:** {metrics.get('overall_coverage', 0):.1f}%\n"
            md_content += f"- **Unique Entity Types Found:** {metrics.get('total_unique_entity_types', 0)}\n"
            md_content += f"- **Average Extraction Time:** {metrics.get('average_extraction_time', 0):.2f}s\n"
            
            with open(md_file, 'w') as f:
                f.write(md_content)
            logger.info(f"Markdown report saved to: {md_file}")
        
        print(f"\n{'='*60}")
        print("Visual Quality Analysis Complete")
        print(f"{'='*60}")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Visual quality inspector for Dobbs extraction")
    parser.add_argument("--results-file", help="Path to test results JSON file")
    parser.add_argument("--latest", action="store_true", help="Use latest test results")
    parser.add_argument("--format", choices=["json", "markdown", "both"], default="both",
                       help="Output format for reports")
    
    args = parser.parse_args()
    
    inspector = VisualQualityInspector()
    
    if args.results_file:
        inspector.load_results(args.results_file)
    elif args.latest:
        file = inspector.load_latest_results()
        if file:
            print(f"Loaded latest results from: {file}")
    else:
        print("Please specify --results-file or --latest")
        sys.exit(1)
    
    if inspector.results:
        inspector.generate_comprehensive_report(output_format=args.format)
    else:
        print("No results to analyze")

if __name__ == "__main__":
    main()