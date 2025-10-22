"""
Report Generator Module

This module generates comprehensive test reports with performance metrics,
visualizations, and detailed analysis of extraction results.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import statistics
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
import matplotlib.pyplot as plt
import pandas as pd


@dataclass
class TestReport:
    """Complete test report data."""
    test_id: str
    timestamp: datetime
    documents_tested: List[str]
    strategies_tested: List[str]
    total_processing_time_ms: float
    vllm_health_checks: List[Dict[str, Any]]
    document_results: List[Dict[str, Any]]
    summary_metrics: Dict[str, Any]
    warnings: List[str]
    errors: List[str]
    

class ReportGenerator:
    """
    Generate comprehensive test reports with visualizations.
    
    This generator creates:
    - Rich console output with tables and panels
    - HTML reports with interactive charts
    - JSON data exports
    - CSV metrics exports
    - Performance visualizations
    """
    
    def __init__(
        self,
        output_dir: str = "/srv/luris/be/entity-extraction-service/tests/results",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the report generator.
        
        Args:
            output_dir: Directory for saving reports
            logger: Optional logger instance
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or logging.getLogger(__name__)
        self.console = Console()
    
    def generate_report(
        self,
        test_results: Dict[str, Any],
        save_files: bool = True
    ) -> TestReport:
        """
        Generate comprehensive test report.
        
        Args:
            test_results: Complete test results data
            save_files: Whether to save report files
            
        Returns:
            TestReport object with all report data
        """
        timestamp = datetime.now()
        test_id = timestamp.strftime("%Y%m%d_%H%M%S")
        
        # Extract key metrics
        summary_metrics = self._calculate_summary_metrics(test_results)
        warnings, errors = self._analyze_issues(test_results)
        
        # Create report object
        report = TestReport(
            test_id=test_id,
            timestamp=timestamp,
            documents_tested=test_results.get("documents_tested", []),
            strategies_tested=test_results.get("strategies_tested", []),
            total_processing_time_ms=test_results.get("total_processing_time_ms", 0),
            vllm_health_checks=test_results.get("vllm_health_checks", []),
            document_results=test_results.get("document_results", []),
            summary_metrics=summary_metrics,
            warnings=warnings,
            errors=errors
        )
        
        # Display console report
        self._display_console_report(report)
        
        # Save files if requested
        if save_files:
            # Save JSON report
            json_path = self.output_dir / f"test_report_{test_id}.json"
            self._save_json_report(report, json_path)
            
            # Save HTML report
            html_path = self.output_dir / f"test_report_{test_id}.html"
            self._save_html_report(report, html_path)
            
            # Save CSV metrics
            csv_path = self.output_dir / f"test_metrics_{test_id}.csv"
            self._save_csv_metrics(report, csv_path)
            
            # Generate visualizations
            viz_path = self.output_dir / f"test_visualizations_{test_id}.png"
            self._generate_visualizations(report, viz_path)
            
            self.logger.info(f"Reports saved to {self.output_dir}")
        
        return report
    
    def _calculate_summary_metrics(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate summary metrics from test results.
        
        Args:
            test_results: Complete test results
            
        Returns:
            Dictionary of summary metrics
        """
        doc_results = test_results.get("document_results", [])
        
        if not doc_results:
            return {}
        
        # Extract metrics
        processing_times = [r["total_processing_time_ms"] for r in doc_results]
        entity_counts = [r["total_entities"] for r in doc_results]
        citation_counts = [r["total_citations"] for r in doc_results]
        chunk_counts = [r["chunks_created"] for r in doc_results]
        ai_rates = [r["ai_enhancement_rate"] for r in doc_results]
        
        # Calculate statistics
        metrics = {
            "total_documents": len(doc_results),
            "total_chunks_processed": sum(chunk_counts),
            "total_entities_extracted": sum(entity_counts),
            "total_citations_extracted": sum(citation_counts),
            "average_processing_time_ms": statistics.mean(processing_times) if processing_times else 0,
            "median_processing_time_ms": statistics.median(processing_times) if processing_times else 0,
            "average_entities_per_doc": statistics.mean(entity_counts) if entity_counts else 0,
            "average_citations_per_doc": statistics.mean(citation_counts) if citation_counts else 0,
            "average_chunks_per_doc": statistics.mean(chunk_counts) if chunk_counts else 0,
            "average_ai_enhancement_rate": statistics.mean(ai_rates) if ai_rates else 0,
            "documents_with_ai_enhancement": sum(1 for r in doc_results if r.get("extraction_mode") != "regex_only"),
            "documents_with_regex_only": sum(1 for r in doc_results if r.get("extraction_mode") == "regex_only"),
            "success_rate": sum(1 for r in doc_results if not r.get("error")) / len(doc_results) * 100 if doc_results else 0
        }
        
        return metrics
    
    def _analyze_issues(self, test_results: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Analyze test results for warnings and errors.
        
        Args:
            test_results: Complete test results
            
        Returns:
            Tuple of (warnings, errors)
        """
        warnings = []
        errors = []
        
        # Check for regex_only fallbacks
        doc_results = test_results.get("document_results", [])
        regex_only_docs = [r["document_path"] for r in doc_results 
                          if r.get("extraction_mode") == "regex_only"]
        
        if regex_only_docs:
            errors.append(f"🚨 CRITICAL: {len(regex_only_docs)} documents fell back to regex_only mode!")
            errors.append(f"   Affected documents: {', '.join(Path(d).name for d in regex_only_docs)}")
        
        # Check for partial AI enhancement
        partial_ai_docs = [r["document_path"] for r in doc_results 
                          if r.get("extraction_mode") == "partial_ai"]
        
        if partial_ai_docs:
            warnings.append(f"⚠️  {len(partial_ai_docs)} documents had partial AI enhancement")
        
        # Check for slow processing
        slow_docs = [r for r in doc_results 
                    if r.get("total_processing_time_ms", 0) > 10000]  # > 10 seconds
        
        if slow_docs:
            warnings.append(f"⚠️  {len(slow_docs)} documents took over 10 seconds to process")
        
        # Check for low entity counts
        low_entity_docs = [r for r in doc_results 
                          if r.get("total_entities", 0) < 10]
        
        if low_entity_docs:
            warnings.append(f"⚠️  {len(low_entity_docs)} documents extracted fewer than 10 entities")
        
        # Check vLLM health
        health_checks = test_results.get("vllm_health_checks", [])
        failed_health = [h for h in health_checks if h.get("status") != "healthy"]
        
        if failed_health:
            errors.append(f"🚨 vLLM health check failures: {len(failed_health)}")
        
        return warnings, errors
    
    def _display_console_report(self, report: TestReport):
        """
        Display report in rich console format.
        
        Args:
            report: TestReport object
        """
        self.console.print()
        
        # Header
        header = Panel(
            Text(f"Entity Extraction Test Report", justify="center", style="bold cyan"),
            subtitle=f"Test ID: {report.test_id} | {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            border_style="cyan"
        )
        self.console.print(header)
        
        # Errors and Warnings
        if report.errors:
            self.console.print("\n[bold red]ERRORS:[/bold red]")
            for error in report.errors:
                self.console.print(f"  {error}")
        
        if report.warnings:
            self.console.print("\n[bold yellow]WARNINGS:[/bold yellow]")
            for warning in report.warnings:
                self.console.print(f"  {warning}")
        
        # Summary Metrics Table
        self.console.print("\n[bold]SUMMARY METRICS:[/bold]")
        
        metrics_table = Table(show_header=True, header_style="bold magenta")
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", justify="right")
        
        metrics = report.summary_metrics
        metrics_table.add_row("Documents Tested", str(metrics.get("total_documents", 0)))
        metrics_table.add_row("Total Chunks", str(metrics.get("total_chunks_processed", 0)))
        metrics_table.add_row("Total Entities", f"{metrics.get('total_entities_extracted', 0):,}")
        metrics_table.add_row("Total Citations", f"{metrics.get('total_citations_extracted', 0):,}")
        metrics_table.add_row("Avg Processing Time", f"{metrics.get('average_processing_time_ms', 0):.1f}ms")
        metrics_table.add_row("AI Enhancement Rate", f"{metrics.get('average_ai_enhancement_rate', 0):.1f}%")
        metrics_table.add_row("Success Rate", f"{metrics.get('success_rate', 0):.1f}%")
        
        self.console.print(metrics_table)
        
        # Document Results Table
        self.console.print("\n[bold]DOCUMENT RESULTS:[/bold]")
        
        doc_table = Table(show_header=True, header_style="bold magenta")
        doc_table.add_column("Document", style="cyan")
        doc_table.add_column("Size", justify="right")
        doc_table.add_column("Chunks", justify="right")
        doc_table.add_column("Entities", justify="right")
        doc_table.add_column("Citations", justify="right")
        doc_table.add_column("Mode", justify="center")
        doc_table.add_column("Time", justify="right")
        
        for result in report.document_results[:10]:  # Show first 10
            doc_name = Path(result["document_path"]).name
            size_mb = result["document_size_chars"] / 1_000_000
            
            # Color code extraction mode
            mode = result["extraction_mode"]
            if mode == "regex_only":
                mode_display = f"[red]{mode}[/red]"
            elif mode == "partial_ai":
                mode_display = f"[yellow]{mode}[/yellow]"
            else:
                mode_display = f"[green]{mode}[/green]"
            
            doc_table.add_row(
                doc_name[:30],
                f"{size_mb:.1f}MB",
                str(result["chunks_created"]),
                str(result["unique_entities"]),
                str(result["unique_citations"]),
                mode_display,
                f"{result['total_processing_time_ms']:.0f}ms"
            )
        
        self.console.print(doc_table)
        
        # Performance by Strategy
        if len(report.strategies_tested) > 1:
            self.console.print("\n[bold]PERFORMANCE BY STRATEGY:[/bold]")
            
            strategy_table = Table(show_header=True, header_style="bold magenta")
            strategy_table.add_column("Strategy", style="cyan")
            strategy_table.add_column("Avg Time", justify="right")
            strategy_table.add_column("Avg Entities", justify="right")
            strategy_table.add_column("AI Rate", justify="right")
            
            for strategy in report.strategies_tested:
                strategy_results = [r for r in report.document_results 
                                   if r.get("strategy") == strategy]
                if strategy_results:
                    avg_time = statistics.mean([r["total_processing_time_ms"] 
                                               for r in strategy_results])
                    avg_entities = statistics.mean([r["unique_entities"] 
                                                   for r in strategy_results])
                    avg_ai_rate = statistics.mean([r["ai_enhancement_rate"] 
                                                   for r in strategy_results])
                    
                    strategy_table.add_row(
                        strategy,
                        f"{avg_time:.0f}ms",
                        f"{avg_entities:.0f}",
                        f"{avg_ai_rate:.1f}%"
                    )
            
            self.console.print(strategy_table)
        
        self.console.print()
    
    def _save_json_report(self, report: TestReport, path: Path):
        """Save report as JSON file."""
        report_dict = {
            "test_id": report.test_id,
            "timestamp": report.timestamp.isoformat(),
            "documents_tested": report.documents_tested,
            "strategies_tested": report.strategies_tested,
            "total_processing_time_ms": report.total_processing_time_ms,
            "summary_metrics": report.summary_metrics,
            "warnings": report.warnings,
            "errors": report.errors,
            "document_results": report.document_results,
            "vllm_health_checks": report.vllm_health_checks
        }
        
        with open(path, 'w') as f:
            json.dump(report_dict, f, indent=2)
        
        self.logger.info(f"JSON report saved to {path}")
    
    def _save_html_report(self, report: TestReport, path: Path):
        """Generate and save HTML report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Entity Extraction Test Report - {report.test_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .metric-card {{ background: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ color: #7f8c8d; font-size: 12px; margin-top: 5px; }}
        .error {{ background: #e74c3c; color: white; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .warning {{ background: #f39c12; color: white; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .success {{ background: #27ae60; color: white; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        table {{ width: 100%; background: white; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #34495e; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ecf0f1; }}
        tr:hover {{ background: #f8f9fa; }}
        .chart {{ margin: 20px 0; background: white; padding: 20px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Entity Extraction Test Report</h1>
        <p>Test ID: {report.test_id} | {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    {''.join(f'<div class="error">{error}</div>' for error in report.errors)}
    {''.join(f'<div class="warning">{warning}</div>' for warning in report.warnings)}
    
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-value">{report.summary_metrics.get('total_documents', 0)}</div>
            <div class="metric-label">Documents Tested</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{report.summary_metrics.get('total_entities_extracted', 0):,}</div>
            <div class="metric-label">Total Entities</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{report.summary_metrics.get('total_citations_extracted', 0):,}</div>
            <div class="metric-label">Total Citations</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{report.summary_metrics.get('average_ai_enhancement_rate', 0):.1f}%</div>
            <div class="metric-label">AI Enhancement Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{report.summary_metrics.get('success_rate', 0):.1f}%</div>
            <div class="metric-label">Success Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{report.summary_metrics.get('average_processing_time_ms', 0):.0f}ms</div>
            <div class="metric-label">Avg Processing Time</div>
        </div>
    </div>
    
    <h2>Document Results</h2>
    <table>
        <thead>
            <tr>
                <th>Document</th>
                <th>Size (MB)</th>
                <th>Chunks</th>
                <th>Entities</th>
                <th>Citations</th>
                <th>Mode</th>
                <th>Time (ms)</th>
            </tr>
        </thead>
        <tbody>
            {''.join(f'''
            <tr>
                <td>{Path(r["document_path"]).name}</td>
                <td>{r["document_size_chars"]/1_000_000:.1f}</td>
                <td>{r["chunks_created"]}</td>
                <td>{r["unique_entities"]}</td>
                <td>{r["unique_citations"]}</td>
                <td style="color: {'red' if r["extraction_mode"] == 'regex_only' else 'green'}">
                    {r["extraction_mode"]}
                </td>
                <td>{r["total_processing_time_ms"]:.0f}</td>
            </tr>
            ''' for r in report.document_results)}
        </tbody>
    </table>
</body>
</html>
        """
        
        with open(path, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML report saved to {path}")
    
    def _save_csv_metrics(self, report: TestReport, path: Path):
        """Save metrics as CSV file."""
        # Convert document results to DataFrame
        df = pd.DataFrame(report.document_results)
        
        # Add document names
        df['document_name'] = df['document_path'].apply(lambda x: Path(x).name)
        
        # Select key columns
        columns = [
            'document_name', 'document_size_chars', 'chunks_created',
            'total_entities', 'unique_entities', 'total_citations', 
            'unique_citations', 'extraction_mode', 'ai_enhancement_rate',
            'total_processing_time_ms'
        ]
        
        df = df[columns]
        
        # Save to CSV
        df.to_csv(path, index=False)
        
        self.logger.info(f"CSV metrics saved to {path}")
    
    def _generate_visualizations(self, report: TestReport, path: Path):
        """Generate performance visualizations."""
        if not report.document_results:
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(f'Entity Extraction Test Results - {report.test_id}', fontsize=16)
        
        # Processing Time by Document
        ax1 = axes[0, 0]
        doc_names = [Path(r["document_path"]).name[:20] for r in report.document_results]
        processing_times = [r["total_processing_time_ms"] for r in report.document_results]
        ax1.bar(range(len(doc_names)), processing_times)
        ax1.set_xticks(range(len(doc_names)))
        ax1.set_xticklabels(doc_names, rotation=45, ha='right')
        ax1.set_ylabel('Processing Time (ms)')
        ax1.set_title('Processing Time by Document')
        
        # Entities vs Document Size
        ax2 = axes[0, 1]
        doc_sizes = [r["document_size_chars"]/1_000_000 for r in report.document_results]
        entity_counts = [r["unique_entities"] for r in report.document_results]
        ax2.scatter(doc_sizes, entity_counts)
        ax2.set_xlabel('Document Size (MB)')
        ax2.set_ylabel('Unique Entities')
        ax2.set_title('Entities vs Document Size')
        
        # AI Enhancement Rate
        ax3 = axes[1, 0]
        ai_rates = [r["ai_enhancement_rate"] for r in report.document_results]
        ax3.bar(range(len(doc_names)), ai_rates)
        ax3.set_xticks(range(len(doc_names)))
        ax3.set_xticklabels(doc_names, rotation=45, ha='right')
        ax3.set_ylabel('AI Enhancement Rate (%)')
        ax3.set_title('AI Enhancement Rate by Document')
        ax3.axhline(y=80, color='r', linestyle='--', alpha=0.5, label='Target (80%)')
        ax3.legend()
        
        # Chunks vs Document Size
        ax4 = axes[1, 1]
        chunk_counts = [r["chunks_created"] for r in report.document_results]
        ax4.scatter(doc_sizes, chunk_counts)
        ax4.set_xlabel('Document Size (MB)')
        ax4.set_ylabel('Chunks Created')
        ax4.set_title('Chunks vs Document Size')
        
        plt.tight_layout()
        plt.savefig(path, dpi=100, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Visualizations saved to {path}")


if __name__ == "__main__":
    # Test the report generator
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    # Create test data
    test_results = {
        "documents_tested": ["doc1.pdf", "doc2.pdf"],
        "strategies_tested": ["unified", "multipass"],
        "total_processing_time_ms": 5000,
        "document_results": [
            {
                "document_path": "/path/to/doc1.pdf",
                "document_size_chars": 100000,
                "chunks_created": 2,
                "total_entities": 50,
                "unique_entities": 45,
                "total_citations": 20,
                "unique_citations": 18,
                "extraction_mode": "ai_enhanced",
                "ai_enhancement_rate": 85.0,
                "total_processing_time_ms": 2500,
                "strategy": "unified"
            },
            {
                "document_path": "/path/to/doc2.pdf",
                "document_size_chars": 200000,
                "chunks_created": 4,
                "total_entities": 100,
                "unique_entities": 90,
                "total_citations": 40,
                "unique_citations": 35,
                "extraction_mode": "regex_only",  # This will trigger an error
                "ai_enhancement_rate": 0.0,
                "total_processing_time_ms": 2500,
                "strategy": "multipass"
            }
        ],
        "vllm_health_checks": [
            {"status": "healthy", "timestamp": "2024-01-01T12:00:00"}
        ]
    }
    
    generator = ReportGenerator()
    report = generator.generate_report(test_results, save_files=True)
    
    print(f"\nReport generated: {report.test_id}")
    print(f"Warnings: {len(report.warnings)}")
    print(f"Errors: {len(report.errors)}")