#!/usr/bin/env python3
"""
Enhanced Visual Dashboard for Entity Extraction Quality Analysis.
Creates rich console visualizations with actual extracted values and detailed comparisons.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.columns import Columns
from rich import box
from rich.align import Align
from rich.syntax import Syntax
from rich.bar import Bar
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedVisualDashboard:
    """Enhanced dashboard with rich console visualizations."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.results = None
        self.results_dir = Path("/srv/luris/be/entity-extraction-service/tests/dobbs_testing/results")
    
    def load_results(self, results_file: str) -> bool:
        """Load test results from JSON file."""
        try:
            with open(results_file, 'r') as f:
                self.results = json.load(f)
            return True
        except Exception as e:
            self.console.print(f"[red]Error loading results: {e}[/red]")
            return False
    
    def create_header_panel(self) -> Panel:
        """Create the header panel with test information."""
        if not self.results:
            return Panel("No results loaded", title="Dashboard")
        
        header_text = Text()
        header_text.append("Entity Extraction Quality Dashboard\n", style="bold cyan")
        header_text.append(f"\nTest ID: ", style="dim")
        header_text.append(f"{self.results.get('test_id', 'Unknown')}\n", style="yellow")
        header_text.append(f"Document: ", style="dim")
        header_text.append(f"{self.results.get('document', 'Unknown')}\n", style="green")
        header_text.append(f"Generated: ", style="dim")
        header_text.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="blue")
        
        return Panel(
            Align.center(header_text),
            title="[bold]Dobbs v. Jackson Extraction Analysis[/bold]",
            border_style="bright_blue",
            box=box.DOUBLE
        )
    
    def create_performance_table(self) -> Table:
        """Create performance comparison table."""
        table = Table(title="Strategy Performance Comparison", box=box.ROUNDED)
        
        # Define columns
        table.add_column("Strategy", style="cyan", no_wrap=True)
        table.add_column("Entities", justify="right", style="green")
        table.add_column("Citations", justify="right", style="yellow")
        table.add_column("Types", justify="right", style="magenta")
        table.add_column("Coverage", justify="right", style="blue")
        table.add_column("Confidence", justify="right", style="green")
        table.add_column("Time (s)", justify="right", style="red")
        table.add_column("Score", justify="right", style="bold white")
        
        modes = self.results.get("modes_tested", [])
        successful = [m for m in modes if m.get("success")]
        
        # Calculate composite scores for ranking
        max_entities = max(m.get("total_entities", 0) for m in successful) or 1
        max_coverage = max(m.get("entity_type_coverage", 0) for m in successful) or 1
        min_time = min(m.get("elapsed_time", 1) for m in successful) or 1
        
        for mode in successful:
            # Calculate composite quality score (0-100)
            entity_score = (mode.get("total_entities", 0) / max_entities) * 25
            coverage_score = (mode.get("entity_type_coverage", 0) / max_coverage) * 25
            confidence_score = mode.get("average_confidence", 0) * 25
            time_score = (min_time / mode.get("elapsed_time", 1)) * 25
            total_score = entity_score + coverage_score + confidence_score + time_score
            
            # Format strategy name
            strategy_name = f"{mode['mode']}_{mode['strategy']}"
            
            # Add row with color coding
            conf_val = mode.get("average_confidence", 0)
            conf_style = "green" if conf_val > 0.9 else "yellow" if conf_val > 0.8 else "red"
            
            table.add_row(
                strategy_name,
                str(mode.get("total_entities", 0)),
                str(mode.get("total_citations", 0)),
                str(mode.get("unique_entity_types", 0)),
                f"{mode.get('entity_type_coverage', 0):.1f}%",
                f"[{conf_style}]{conf_val:.3f}[/{conf_style}]",
                f"{mode.get('elapsed_time', 0):.2f}",
                f"{total_score:.0f}"
            )
        
        return table
    
    def create_entity_samples_panel(self) -> Panel:
        """Create panel showing actual extracted entity samples."""
        if not self.results:
            return Panel("No results", title="Entity Samples")
        
        modes = self.results.get("modes_tested", [])
        best_mode = max(modes, key=lambda x: x.get("average_confidence", 0))
        
        samples = best_mode.get("sample_entities", [])[:10]
        
        content = Text()
        content.append(f"Top Entities from {best_mode['mode']}_{best_mode['strategy']}\n\n", 
                      style="bold cyan")
        
        for entity in samples:
            # Color code by confidence
            conf = entity.get("confidence", 0)
            if conf >= 0.9:
                conf_color = "green"
                symbol = "✓"
            elif conf >= 0.8:
                conf_color = "yellow"
                symbol = "⚠"
            else:
                conf_color = "red"
                symbol = "✗"
            
            content.append(f"{symbol} ", style=conf_color)
            content.append(f"{entity.get('entity_text', 'Unknown')[:40]:40} ", style="white")
            content.append(f"[{entity.get('entity_type', 'Unknown'):20}] ", style="cyan")
            content.append(f"[{conf:.3f}]", style=conf_color)
            content.append(f" p.{entity.get('page', 0)}\n", style="dim")
        
        return Panel(
            content,
            title="[bold]Actual Extracted Entities[/bold]",
            border_style="green",
            box=box.ROUNDED
        )
    
    def create_coverage_heatmap(self) -> Panel:
        """Create entity type coverage heatmap."""
        if not self.results:
            return Panel("No coverage data", title="Coverage")
        
        coverage = self.results.get("entity_type_coverage_summary", {})
        modes = self.results.get("modes_tested", [])
        
        # Create heatmap grid
        content = Text()
        content.append("Entity Type Coverage Heatmap\n\n", style="bold")
        
        # Header row with strategy names
        strategies = [f"{m['mode'][:3]}_{m['strategy'][:4]}" for m in modes if m.get("success")]
        content.append("Type               " + "  ".join(strategies) + "\n", style="cyan")
        content.append("-" * 60 + "\n", style="dim")
        
        # Show top entity types
        sorted_types = sorted(coverage.items(), 
                            key=lambda x: x[1].get('total_count', 0), 
                            reverse=True)[:15]
        
        for entity_type, data in sorted_types:
            # Truncate entity type name
            type_name = f"{entity_type[:15]:15}"
            content.append(type_name + "  ", style="white")
            
            # Show coverage for each strategy
            found_by = data.get("found_by", [])
            for mode in modes:
                if not mode.get("success"):
                    continue
                    
                strategy_id = f"{mode['mode']}_{mode['strategy']}"
                count = mode.get("entity_type_counts", {}).get(entity_type, 0)
                
                if count > 20:
                    symbol = "█"
                    color = "green"
                elif count > 10:
                    symbol = "▓"
                    color = "yellow"
                elif count > 5:
                    symbol = "▒"
                    color = "cyan"
                elif count > 0:
                    symbol = "░"
                    color = "blue"
                else:
                    symbol = "·"
                    color = "dim"
                
                content.append(f"[{color}]{symbol*3}[/{color}]  ", style=color)
            
            content.append(f" {data.get('total_count', 0):3}", style="dim")
            content.append("\n")
        
        return Panel(
            content,
            title="[bold]Coverage Heatmap[/bold]",
            border_style="magenta",
            box=box.ROUNDED
        )
    
    def create_confidence_distribution(self) -> Panel:
        """Create confidence distribution visualization."""
        if not self.results:
            return Panel("No confidence data", title="Confidence")
        
        content = Text()
        content.append("Confidence Score Distribution\n\n", style="bold cyan")
        
        modes = self.results.get("modes_tested", [])
        
        for mode in modes:
            if not mode.get("success"):
                continue
            
            strategy = f"{mode['mode']}_{mode['strategy']}"
            avg_conf = mode.get("average_confidence", 0)
            
            # Create confidence bar
            bar_length = int(avg_conf * 30)
            bar_color = "green" if avg_conf > 0.9 else "yellow" if avg_conf > 0.8 else "red"
            
            content.append(f"{strategy:30} ", style="white")
            content.append(f"[{bar_color}]{'█' * bar_length}{'░' * (30 - bar_length)}[/{bar_color}] ")
            content.append(f"{avg_conf:.3f}\n", style=bar_color)
            
            # Show distribution details
            dist = mode.get("confidence_distribution", {})
            content.append(f"  Range: [{dist.get('min', 0):.3f} - {dist.get('max', 0):.3f}]  ", 
                          style="dim")
            
            # Calculate buckets from sample entities
            samples = mode.get("sample_entities", [])
            if samples:
                confs = [e.get("confidence", 0) for e in samples if "confidence" in e]
                high = sum(1 for c in confs if c >= 0.9)
                med = sum(1 for c in confs if 0.8 <= c < 0.9)
                low = sum(1 for c in confs if c < 0.8)
                content.append(f"High:{high} Med:{med} Low:{low}\n", style="dim")
            else:
                content.append("\n")
        
        return Panel(
            content,
            title="[bold]Confidence Analysis[/bold]",
            border_style="yellow",
            box=box.ROUNDED
        )
    
    def create_quality_metrics_panel(self) -> Panel:
        """Create panel with quality metrics and recommendations."""
        if not self.results:
            return Panel("No metrics", title="Quality Metrics")
        
        metrics = self.results.get("aggregate_metrics", {})
        
        content = Text()
        content.append("Overall Quality Metrics\n\n", style="bold cyan")
        
        # Success rate
        total = metrics.get("total_tests", 0)
        successful = metrics.get("successful_tests", 0)
        success_rate = (successful / total * 100) if total > 0 else 0
        
        content.append("Success Rate: ", style="white")
        color = "green" if success_rate == 100 else "yellow" if success_rate > 80 else "red"
        content.append(f"[{color}]{success_rate:.0f}%[/{color}] ({successful}/{total})\n")
        
        # Coverage
        coverage = metrics.get("overall_coverage", 0)
        content.append("Average Coverage: ", style="white")
        color = "green" if coverage > 85 else "yellow" if coverage > 70 else "red"
        content.append(f"[{color}]{coverage:.1f}%[/{color}]\n")
        
        # Entity types
        types_found = metrics.get("total_unique_entity_types", 0)
        content.append("Entity Types Found: ", style="white")
        content.append(f"[cyan]{types_found}[/cyan] / 31 total\n")
        
        # Processing time
        avg_time = metrics.get("average_extraction_time", 0)
        content.append("Average Time: ", style="white")
        color = "green" if avg_time < 3 else "yellow" if avg_time < 6 else "red"
        content.append(f"[{color}]{avg_time:.2f}s[/{color}]\n")
        
        # Recommendations
        content.append("\nRecommendations:\n", style="bold yellow")
        
        modes = self.results.get("modes_tested", [])
        if modes:
            # Find best for different use cases
            fastest = min(modes, key=lambda x: x.get("elapsed_time", float('inf')))
            most_accurate = max(modes, key=lambda x: x.get("average_confidence", 0))
            best_coverage = max(modes, key=lambda x: x.get("entity_type_coverage", 0))
            
            content.append("• Speed Priority: ", style="dim")
            content.append(f"{fastest['mode']}_{fastest['strategy']}\n", style="green")
            
            content.append("• Accuracy Priority: ", style="dim")
            content.append(f"{most_accurate['mode']}_{most_accurate['strategy']}\n", style="green")
            
            content.append("• Coverage Priority: ", style="dim")
            content.append(f"{best_coverage['mode']}_{best_coverage['strategy']}\n", style="green")
        
        return Panel(
            content,
            title="[bold]Quality Metrics & Recommendations[/bold]",
            border_style="blue",
            box=box.ROUNDED
        )
    
    def create_full_dashboard(self) -> None:
        """Create and display the full dashboard."""
        # Clear console
        self.console.clear()
        
        # Create header
        header = self.create_header_panel()
        self.console.print(header)
        self.console.print()
        
        # Create performance table
        perf_table = self.create_performance_table()
        self.console.print(perf_table)
        self.console.print()
        
        # Create two-column layout for middle section
        layout = Layout()
        layout.split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        # Left column: Entity samples and confidence
        left_layout = Layout()
        left_layout.split_column(
            Layout(self.create_entity_samples_panel(), name="samples"),
            Layout(self.create_confidence_distribution(), name="confidence")
        )
        layout["left"].update(left_layout)
        
        # Right column: Coverage heatmap and metrics
        right_layout = Layout()
        right_layout.split_column(
            Layout(self.create_coverage_heatmap(), name="coverage"),
            Layout(self.create_quality_metrics_panel(), name="metrics")
        )
        layout["right"].update(right_layout)
        
        self.console.print(layout)
        
        # Footer
        self.console.print()
        self.console.rule("[bold cyan]Analysis Complete[/bold cyan]")
        self.console.print(
            f"[dim]Dashboard generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
            justify="center"
        )
    
    def export_detailed_json(self, output_file: Optional[str] = None) -> str:
        """Export detailed JSON analysis."""
        if not self.results:
            return None
        
        # Create detailed analysis
        analysis = {
            "dashboard_version": "2.0",
            "generated_at": datetime.now().isoformat(),
            "test_summary": {
                "test_id": self.results.get("test_id"),
                "document": self.results.get("document"),
                "strategies_tested": len(self.results.get("modes_tested", [])),
                "aggregate_metrics": self.results.get("aggregate_metrics", {})
            },
            "strategy_rankings": [],
            "entity_type_analysis": {},
            "confidence_analysis": {},
            "performance_analysis": {},
            "recommendations": {}
        }
        
        # Rank strategies
        modes = self.results.get("modes_tested", [])
        for mode in modes:
            if mode.get("success"):
                # Calculate composite score
                score = (
                    mode.get("entity_type_coverage", 0) * 0.3 +
                    mode.get("average_confidence", 0) * 100 * 0.3 +
                    (mode.get("total_entities", 0) / 200) * 100 * 0.2 +
                    (1.0 / (mode.get("elapsed_time", 1) + 0.1)) * 10 * 0.2
                )
                
                analysis["strategy_rankings"].append({
                    "strategy": f"{mode['mode']}_{mode['strategy']}",
                    "composite_score": round(score, 2),
                    "metrics": {
                        "entities": mode.get("total_entities", 0),
                        "coverage": mode.get("entity_type_coverage", 0),
                        "confidence": mode.get("average_confidence", 0),
                        "time": mode.get("elapsed_time", 0)
                    }
                })
        
        # Sort by score
        analysis["strategy_rankings"].sort(key=lambda x: x["composite_score"], reverse=True)
        
        # Entity type analysis
        coverage = self.results.get("entity_type_coverage_summary", {})
        for entity_type, data in coverage.items():
            analysis["entity_type_analysis"][entity_type] = {
                "total_occurrences": data.get("total_count", 0),
                "strategies_found": len(data.get("found_by", [])),
                "coverage_percent": data.get("coverage_percent", 0),
                "found_by": data.get("found_by", [])
            }
        
        # Save to file
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.results_dir / f"detailed_analysis_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        return str(output_file)

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced visual dashboard for extraction analysis")
    parser.add_argument("--results-file", help="Path to test results JSON file")
    parser.add_argument("--latest", action="store_true", help="Use latest test results")
    parser.add_argument("--export-json", action="store_true", help="Export detailed JSON analysis")
    
    args = parser.parse_args()
    
    console = Console()
    dashboard = EnhancedVisualDashboard(console)
    
    # Load results
    if args.results_file:
        if not dashboard.load_results(args.results_file):
            sys.exit(1)
    elif args.latest:
        # Find latest results
        results_dir = Path("/srv/luris/be/entity-extraction-service/tests/dobbs_testing/results")
        json_files = list(results_dir.glob("dobbs_test_*.json"))
        if not json_files:
            console.print("[red]No test results found[/red]")
            sys.exit(1)
        
        latest = max(json_files, key=lambda f: f.stat().st_mtime)
        console.print(f"[cyan]Loading: {latest}[/cyan]")
        if not dashboard.load_results(str(latest)):
            sys.exit(1)
    else:
        console.print("[yellow]Please specify --results-file or --latest[/yellow]")
        sys.exit(1)
    
    # Display dashboard
    dashboard.create_full_dashboard()
    
    # Export JSON if requested
    if args.export_json:
        output_file = dashboard.export_detailed_json()
        if output_file:
            console.print(f"\n[green]Detailed analysis exported to: {output_file}[/green]")

if __name__ == "__main__":
    main()