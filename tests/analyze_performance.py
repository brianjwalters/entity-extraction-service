#!/usr/bin/env python3
"""
Performance Analysis Script for Entity Extraction Service
Analyzes test_history.json to identify trends, bottlenecks, and optimization opportunities
"""

import json
import statistics
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

def load_test_history(file_path: str) -> Dict:
    """Load test history from JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def analyze_performance_metrics(tests: List[Dict]) -> Dict[str, Any]:
    """Analyze core performance metrics across all tests"""

    metrics = {
        'execution_times': [],
        'entities_per_second': [],
        'document_sizes': [],
        'entity_counts': [],
        'tokens_used': [],
        'avg_confidence_scores': [],
        'strategies': {},
    }

    for test in tests:
        perf = test['performance']
        routing = test['routing']
        entity_dist = test['entity_distribution']
        quality = test['quality']

        # Collect metrics
        metrics['execution_times'].append(perf['total_duration_seconds'])
        metrics['entities_per_second'].append(perf['entities_per_second'])
        metrics['entity_counts'].append(entity_dist['total_entities'])
        metrics['tokens_used'].append(routing['estimated_tokens'])
        metrics['avg_confidence_scores'].append(quality['avg_confidence_score'])

        # Estimate document size from tokens (roughly 4 chars per token)
        doc_size = routing['estimated_tokens'] * 4
        metrics['document_sizes'].append(doc_size)

        # Track by strategy
        strategy = routing['strategy']
        if strategy not in metrics['strategies']:
            metrics['strategies'][strategy] = {
                'count': 0,
                'avg_time': [],
                'avg_entities': [],
                'avg_confidence': []
            }

        metrics['strategies'][strategy]['count'] += 1
        metrics['strategies'][strategy]['avg_time'].append(perf['total_duration_seconds'])
        metrics['strategies'][strategy]['avg_entities'].append(entity_dist['total_entities'])
        metrics['strategies'][strategy]['avg_confidence'].append(quality['avg_confidence_score'])

    return metrics

def calculate_correlations(metrics: Dict[str, Any]) -> Dict[str, float]:
    """Calculate correlations between different metrics"""

    def pearson_correlation(x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(xi**2 for xi in x)
        sum_y2 = sum(yi**2 for yi in y)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))**0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator

    correlations = {
        'time_vs_doc_size': pearson_correlation(
            metrics['execution_times'],
            metrics['document_sizes']
        ),
        'time_vs_entity_count': pearson_correlation(
            metrics['execution_times'],
            metrics['entity_counts']
        ),
        'time_vs_tokens': pearson_correlation(
            metrics['execution_times'],
            metrics['tokens_used']
        ),
        'entities_vs_doc_size': pearson_correlation(
            metrics['entity_counts'],
            metrics['document_sizes']
        ),
        'confidence_vs_time': pearson_correlation(
            metrics['avg_confidence_scores'],
            metrics['execution_times']
        )
    }

    return correlations

def analyze_token_efficiency(metrics: Dict[str, Any]) -> Dict[str, float]:
    """Analyze token usage efficiency"""

    tokens_per_char = []
    tokens_per_entity = []
    chars_per_entity = []

    for i in range(len(metrics['tokens_used'])):
        tokens = metrics['tokens_used'][i]
        doc_size = metrics['document_sizes'][i]
        entities = metrics['entity_counts'][i]

        if doc_size > 0:
            tokens_per_char.append(tokens / doc_size)

        if entities > 0:
            tokens_per_entity.append(tokens / entities)
            chars_per_entity.append(doc_size / entities)

    efficiency = {
        'avg_tokens_per_char': statistics.mean(tokens_per_char) if tokens_per_char else 0,
        'avg_tokens_per_entity': statistics.mean(tokens_per_entity) if tokens_per_entity else 0,
        'avg_chars_per_entity': statistics.mean(chars_per_entity) if chars_per_entity else 0,
    }

    return efficiency

def analyze_strategy_comparison(metrics: Dict[str, Any]) -> Dict[str, Dict]:
    """Compare performance across different routing strategies"""

    comparison = {}

    for strategy, data in metrics['strategies'].items():
        comparison[strategy] = {
            'test_count': data['count'],
            'avg_execution_time': statistics.mean(data['avg_time']),
            'min_execution_time': min(data['avg_time']),
            'max_execution_time': max(data['avg_time']),
            'avg_entities_extracted': statistics.mean(data['avg_entities']),
            'avg_confidence': statistics.mean(data['avg_confidence']),
            'entities_per_second': statistics.mean(data['avg_entities']) / statistics.mean(data['avg_time']) if statistics.mean(data['avg_time']) > 0 else 0
        }

    return comparison

def identify_bottlenecks(tests: List[Dict]) -> List[Dict[str, Any]]:
    """Identify performance bottlenecks and outliers"""

    execution_times = [t['performance']['total_duration_seconds'] for t in tests]
    avg_time = statistics.mean(execution_times)
    stdev_time = statistics.stdev(execution_times) if len(execution_times) > 1 else 0

    bottlenecks = []

    for test in tests:
        time = test['performance']['total_duration_seconds']

        # Identify tests significantly slower than average
        if time > avg_time + stdev_time:
            bottlenecks.append({
                'test_id': test['test_id'],
                'document_id': test['document_id'],
                'execution_time': time,
                'deviation_from_avg': time - avg_time,
                'strategy': test['routing']['strategy'],
                'tokens': test['routing']['estimated_tokens'],
                'entities': test['entity_distribution']['total_entities'],
                'issue': 'Significantly slower than average'
            })

    return bottlenecks

def generate_recommendations(metrics: Dict, correlations: Dict, comparison: Dict) -> List[str]:
    """Generate performance optimization recommendations"""

    recommendations = []

    # Analyze strategy performance
    if 'single_pass' in comparison and 'three_wave' in comparison:
        single_time = comparison['single_pass']['avg_execution_time']
        three_time = comparison['three_wave']['avg_execution_time']

        if single_time < three_time:
            speedup = ((three_time - single_time) / three_time) * 100
            recommendations.append(
                f"✅ STRATEGY OPTIMIZATION: single_pass is {speedup:.1f}% faster than three_wave "
                f"({single_time:.2f}s vs {three_time:.2f}s). Prioritize single_pass for similar workloads."
            )

    # Analyze correlation between document size and execution time
    if correlations['time_vs_doc_size'] > 0.7:
        recommendations.append(
            f"⚠️ DOCUMENT SIZE BOTTLENECK: Strong correlation ({correlations['time_vs_doc_size']:.2f}) "
            f"between document size and execution time. Consider chunking strategies for large documents."
        )

    # Analyze token efficiency
    avg_exec_time = statistics.mean(metrics['execution_times'])
    if avg_exec_time > 30:
        recommendations.append(
            f"⚠️ EXECUTION TIME: Average execution time ({avg_exec_time:.2f}s) exceeds 30s. "
            f"Consider parallel processing or caching strategies."
        )

    # Analyze entity extraction rate
    avg_entities_per_sec = statistics.mean(metrics['entities_per_second'])
    if avg_entities_per_sec < 0.5:
        recommendations.append(
            f"⚠️ EXTRACTION RATE: Average extraction rate ({avg_entities_per_sec:.3f} entities/sec) is low. "
            f"Consider optimizing pattern matching or LLM processing."
        )

    # Analyze confidence vs time tradeoff
    if correlations['confidence_vs_time'] < -0.3:
        recommendations.append(
            f"⚠️ QUALITY vs SPEED TRADEOFF: Negative correlation ({correlations['confidence_vs_time']:.2f}) "
            f"suggests faster processing may reduce confidence. Validate quality at higher speeds."
        )
    else:
        recommendations.append(
            f"✅ QUALITY MAINTAINED: Low correlation ({correlations['confidence_vs_time']:.2f}) "
            f"between confidence and time suggests quality is maintained across different speeds."
        )

    return recommendations

def generate_markdown_report(analysis: Dict, output_path: str):
    """Generate comprehensive markdown performance report"""

    report = []

    # Header
    report.append("# Entity Extraction Service - Performance Analysis Report")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n**Total Tests Analyzed:** {analysis['total_tests']}")
    report.append("\n---\n")

    # Executive Summary
    report.append("## Executive Summary\n")
    metrics = analysis['metrics']
    report.append(f"- **Average Execution Time:** {statistics.mean(metrics['execution_times']):.2f}s")
    report.append(f"- **Execution Time Range:** {min(metrics['execution_times']):.2f}s - {max(metrics['execution_times']):.2f}s")
    report.append(f"- **Average Entities Extracted:** {statistics.mean(metrics['entity_counts']):.1f} entities/test")
    report.append(f"- **Average Extraction Rate:** {statistics.mean(metrics['entities_per_second']):.3f} entities/second")
    report.append(f"- **Average Confidence Score:** {statistics.mean(metrics['avg_confidence_scores']):.3f}")
    report.append("\n---\n")

    # Performance Metrics
    report.append("## Performance Metrics\n")
    report.append("### Execution Time Analysis\n")
    report.append("| Metric | Value |")
    report.append("|--------|-------|")
    report.append(f"| Mean | {statistics.mean(metrics['execution_times']):.2f}s |")
    report.append(f"| Median | {statistics.median(metrics['execution_times']):.2f}s |")
    if len(metrics['execution_times']) > 1:
        report.append(f"| Std Dev | {statistics.stdev(metrics['execution_times']):.2f}s |")
    report.append(f"| Min | {min(metrics['execution_times']):.2f}s |")
    report.append(f"| Max | {max(metrics['execution_times']):.2f}s |")
    report.append("\n")

    # Token Efficiency
    report.append("### Token Usage Efficiency\n")
    efficiency = analysis['efficiency']
    report.append("| Metric | Value |")
    report.append("|--------|-------|")
    report.append(f"| Avg Tokens per Character | {efficiency['avg_tokens_per_char']:.4f} |")
    report.append(f"| Avg Tokens per Entity | {efficiency['avg_tokens_per_entity']:.1f} |")
    report.append(f"| Avg Characters per Entity | {efficiency['avg_chars_per_entity']:.1f} |")
    report.append("\n")

    # Entity Extraction Throughput
    report.append("### Entity Extraction Throughput\n")
    report.append("| Metric | Value |")
    report.append("|--------|-------|")
    report.append(f"| Mean | {statistics.mean(metrics['entities_per_second']):.3f} entities/sec |")
    report.append(f"| Median | {statistics.median(metrics['entities_per_second']):.3f} entities/sec |")
    report.append(f"| Min | {min(metrics['entities_per_second']):.3f} entities/sec |")
    report.append(f"| Max | {max(metrics['entities_per_second']):.3f} entities/sec |")
    report.append("\n---\n")

    # Correlation Analysis
    report.append("## Correlation Analysis\n")
    correlations = analysis['correlations']
    report.append("| Correlation | Coefficient | Interpretation |")
    report.append("|-------------|-------------|----------------|")

    for corr_name, coeff in correlations.items():
        interpretation = ""
        if abs(coeff) > 0.7:
            interpretation = "Strong correlation"
        elif abs(coeff) > 0.4:
            interpretation = "Moderate correlation"
        elif abs(coeff) > 0.2:
            interpretation = "Weak correlation"
        else:
            interpretation = "No significant correlation"

        display_name = corr_name.replace('_', ' ').title()
        report.append(f"| {display_name} | {coeff:.3f} | {interpretation} |")
    report.append("\n---\n")

    # Strategy Comparison
    report.append("## Strategy Comparison\n")
    comparison = analysis['comparison']

    if comparison:
        report.append("| Strategy | Tests | Avg Time (s) | Min Time (s) | Max Time (s) | Avg Entities | Entities/Sec | Avg Confidence |")
        report.append("|----------|-------|--------------|--------------|--------------|--------------|--------------|----------------|")

        for strategy, data in comparison.items():
            report.append(
                f"| {strategy} | {data['test_count']} | {data['avg_execution_time']:.2f} | "
                f"{data['min_execution_time']:.2f} | {data['max_execution_time']:.2f} | "
                f"{data['avg_entities_extracted']:.1f} | {data['entities_per_second']:.3f} | "
                f"{data['avg_confidence']:.3f} |"
            )
        report.append("\n")

        # Strategy performance comparison
        if 'single_pass' in comparison and 'three_wave' in comparison:
            single = comparison['single_pass']
            three = comparison['three_wave']

            report.append("### Key Findings:\n")

            time_diff = ((three['avg_execution_time'] - single['avg_execution_time']) / single['avg_execution_time']) * 100
            report.append(f"- **Speed:** `single_pass` is **{abs(time_diff):.1f}% {'faster' if time_diff > 0 else 'slower'}** than `three_wave`")

            entity_diff = ((three['avg_entities_extracted'] - single['avg_entities_extracted']) / single['avg_entities_extracted']) * 100
            report.append(f"- **Entity Extraction:** `three_wave` extracts **{abs(entity_diff):.1f}% {'more' if entity_diff > 0 else 'fewer'}** entities on average")

            conf_diff = ((three['avg_confidence'] - single['avg_confidence']) / single['avg_confidence']) * 100
            report.append(f"- **Confidence:** `three_wave` has **{abs(conf_diff):.1f}% {'higher' if conf_diff > 0 else 'lower'}** average confidence")

    report.append("\n---\n")

    # Bottlenecks
    report.append("## Performance Bottlenecks\n")
    bottlenecks = analysis['bottlenecks']

    if bottlenecks:
        report.append(f"**Identified {len(bottlenecks)} performance bottleneck(s):**\n")
        report.append("| Test ID | Document | Time (s) | Strategy | Tokens | Entities | Issue |")
        report.append("|---------|----------|----------|----------|--------|----------|-------|")

        for bottleneck in bottlenecks:
            report.append(
                f"| {bottleneck['test_id'][-8:]} | {bottleneck['document_id']} | "
                f"{bottleneck['execution_time']:.2f} | {bottleneck['strategy']} | "
                f"{bottleneck['tokens']} | {bottleneck['entities']} | {bottleneck['issue']} |"
            )
    else:
        report.append("✅ No significant performance bottlenecks identified.\n")

    report.append("\n---\n")

    # Quality vs Performance
    report.append("## Quality vs Performance Analysis\n")
    report.append("| Metric | Value |")
    report.append("|--------|-------|")
    report.append(f"| Average Confidence Score | {statistics.mean(metrics['avg_confidence_scores']):.3f} |")
    report.append(f"| Min Confidence Score | {min(metrics['avg_confidence_scores']):.3f} |")
    report.append(f"| Max Confidence Score | {max(metrics['avg_confidence_scores']):.3f} |")
    report.append(f"| Confidence-Time Correlation | {correlations['confidence_vs_time']:.3f} |")
    report.append("\n")

    # Interpretation
    if correlations['confidence_vs_time'] < -0.3:
        report.append("⚠️ **Finding:** Negative correlation suggests faster processing may reduce confidence.\n")
    elif abs(correlations['confidence_vs_time']) < 0.2:
        report.append("✅ **Finding:** Low correlation indicates quality is maintained across different processing speeds.\n")
    else:
        report.append("ℹ️ **Finding:** Moderate correlation between confidence and processing time.\n")

    report.append("\n---\n")

    # Recommendations
    report.append("## Performance Optimization Recommendations\n")
    for i, rec in enumerate(analysis['recommendations'], 1):
        report.append(f"{i}. {rec}\n")

    report.append("\n---\n")

    # Conclusion
    report.append("## Conclusion\n")
    avg_time = statistics.mean(metrics['execution_times'])
    avg_rate = statistics.mean(metrics['entities_per_second'])
    avg_conf = statistics.mean(metrics['avg_confidence_scores'])

    report.append(f"The entity extraction service demonstrates **{'strong' if avg_rate > 0.3 else 'moderate'}** performance with:\n")
    report.append(f"- Average processing time of **{avg_time:.2f} seconds** per test")
    report.append(f"- Entity extraction rate of **{avg_rate:.3f} entities/second**")
    report.append(f"- Consistent high-quality results with **{avg_conf:.1%}** average confidence")
    report.append("\n")

    if 'single_pass' in comparison:
        report.append(f"The `single_pass` strategy offers optimal performance for most workloads, ")
        report.append(f"achieving **{comparison['single_pass']['avg_execution_time']:.2f}s** average execution time.\n")

    # Write report to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))

    print(f"✅ Performance analysis report generated: {output_path}")

def main():
    """Main analysis function"""

    # Paths
    base_path = Path(__file__).parent
    test_history_path = base_path / "results" / "test_history.json"
    output_path = base_path / "results" / "performance_analysis.md"

    print("🔍 Loading test history...")
    data = load_test_history(test_history_path)
    tests = data['tests']

    print(f"📊 Analyzing {len(tests)} tests...")

    # Analyze metrics
    metrics = analyze_performance_metrics(tests)

    # Calculate correlations
    correlations = calculate_correlations(metrics)

    # Analyze token efficiency
    efficiency = analyze_token_efficiency(metrics)

    # Compare strategies
    comparison = analyze_strategy_comparison(metrics)

    # Identify bottlenecks
    bottlenecks = identify_bottlenecks(tests)

    # Generate recommendations
    recommendations = generate_recommendations(metrics, correlations, comparison)

    # Compile analysis
    analysis = {
        'total_tests': len(tests),
        'metrics': metrics,
        'correlations': correlations,
        'efficiency': efficiency,
        'comparison': comparison,
        'bottlenecks': bottlenecks,
        'recommendations': recommendations
    }

    # Generate markdown report
    print("📝 Generating markdown report...")
    generate_markdown_report(analysis, output_path)

    # Print summary
    print("\n" + "="*60)
    print("PERFORMANCE ANALYSIS SUMMARY")
    print("="*60)
    print(f"Total Tests Analyzed: {len(tests)}")
    print(f"Average Execution Time: {statistics.mean(metrics['execution_times']):.2f}s")
    print(f"Average Extraction Rate: {statistics.mean(metrics['entities_per_second']):.3f} entities/sec")
    print(f"Average Confidence: {statistics.mean(metrics['avg_confidence_scores']):.3f}")
    print(f"\nBottlenecks Identified: {len(bottlenecks)}")
    print(f"Optimization Recommendations: {len(recommendations)}")
    print("="*60)

if __name__ == "__main__":
    main()
