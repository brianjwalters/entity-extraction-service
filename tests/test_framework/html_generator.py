"""
HTML Dashboard Generator for Entity Extraction Service Testing Framework

This module generates interactive HTML dashboards with Chart.js visualizations
for test results. The dashboard displays:

- Test execution timeline
- Wave performance charts (entities per wave, tokens per wave, duration)
- Entity distribution charts (by type, by category, by confidence)
- Performance metrics (throughput, latency)
- Quality metrics (confidence distribution, validation status)
- Historical trend analysis

The generated dashboard is self-contained (includes CDN links for Chart.js)
and can be opened directly in a browser.

Usage:
    generator = HTMLDashboardGenerator()
    generator.generate_dashboard(test_results, output_path="dashboard.html")
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class HTMLDashboardGenerator:
    """
    Generates interactive HTML dashboards for test results.

    Uses Chart.js for interactive visualizations including:
    - Line charts for performance trends
    - Bar charts for entity distribution
    - Pie charts for confidence breakdown
    - Tables for detailed metrics
    """

    def __init__(self):
        """Initialize HTML dashboard generator."""
        self.logger = logging.getLogger(__name__)

    def generate_dashboard(
        self,
        test_results: List[Dict[str, Any]],
        output_path: Path,
        title: str = "Entity Extraction Test Dashboard"
    ) -> bool:
        """
        Generate complete HTML dashboard.

        Args:
            test_results: List of test result dictionaries
            output_path: Path to output HTML file
            title: Dashboard title

        Returns:
            bool: True if generated successfully
        """
        try:
            if not test_results:
                self.logger.warning("No test results to visualize")
                return False

            html_content = self._build_html(test_results, title)

            with open(output_path, 'w') as f:
                f.write(html_content)

            self.logger.info(f"Generated dashboard: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate dashboard: {e}", exc_info=True)
            return False

    def _build_html(self, test_results: List[Dict[str, Any]], title: str) -> str:
        """Build complete HTML document."""
        # Prepare data for charts
        chart_data = self._prepare_chart_data(test_results)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{title}</h1>
            <p class="subtitle">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <div class="summary-cards">
            {self._build_summary_cards(test_results)}
        </div>

        <div class="charts-grid">
            <div class="chart-container">
                <h2>Performance Over Time</h2>
                <canvas id="performanceChart"></canvas>
            </div>

            <div class="chart-container">
                <h2>Wave Execution Times</h2>
                <canvas id="waveTimesChart"></canvas>
            </div>

            <div class="chart-container">
                <h2>Entities Per Wave</h2>
                <canvas id="entitiesPerWaveChart"></canvas>
            </div>

            <div class="chart-container">
                <h2>Confidence Distribution</h2>
                <canvas id="confidenceChart"></canvas>
            </div>

            <div class="chart-container">
                <h2>Top Entity Types</h2>
                <canvas id="entityTypesChart"></canvas>
            </div>

            <div class="chart-container">
                <h2>Throughput Metrics</h2>
                <canvas id="throughputChart"></canvas>
            </div>
        </div>

        <div class="table-container">
            <h2>Recent Test Results</h2>
            {self._build_results_table(test_results[-10:][::-1])}
        </div>
    </div>

    <script>
        {self._get_chart_scripts(chart_data)}
    </script>
</body>
</html>"""
        return html

    def _get_css(self) -> str:
        """Get CSS styles for dashboard."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }

        header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid #667eea;
        }

        h1 {
            font-size: 2.5em;
            color: #2d3748;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #718096;
            font-size: 1.1em;
        }

        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }

        .card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .card-title {
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }

        .card-value {
            font-size: 2.5em;
            font-weight: bold;
        }

        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }

        .chart-container {
            background: #f7fafc;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .chart-container h2 {
            color: #2d3748;
            font-size: 1.3em;
            margin-bottom: 20px;
        }

        .table-container {
            margin-top: 40px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-radius: 12px;
            overflow: hidden;
        }

        th {
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }

        td {
            padding: 12px 15px;
            border-bottom: 1px solid #e2e8f0;
        }

        tr:hover {
            background: #f7fafc;
        }

        .status-passed {
            color: #48bb78;
            font-weight: bold;
        }

        .status-failed {
            color: #f56565;
            font-weight: bold;
        }
        """

    def _build_summary_cards(self, test_results: List[Dict[str, Any]]) -> str:
        """Build summary cards HTML."""
        if not test_results:
            return ""

        total_tests = len(test_results)
        latest_test = test_results[-1]

        # Calculate averages
        avg_duration = sum(r["performance"]["total_duration_seconds"] for r in test_results) / total_tests
        avg_entities = sum(r["entity_distribution"]["total_entities"] for r in test_results) / total_tests
        avg_confidence = sum(r["quality"]["avg_confidence_score"] for r in test_results) / total_tests
        passed_tests = sum(1 for r in test_results if r["quality"]["validation_passed"])

        return f"""
        <div class="card">
            <div class="card-title">Total Tests</div>
            <div class="card-value">{total_tests}</div>
        </div>
        <div class="card">
            <div class="card-title">Avg Duration</div>
            <div class="card-value">{avg_duration:.2f}s</div>
        </div>
        <div class="card">
            <div class="card-title">Avg Entities</div>
            <div class="card-value">{int(avg_entities)}</div>
        </div>
        <div class="card">
            <div class="card-title">Avg Confidence</div>
            <div class="card-value">{avg_confidence:.3f}</div>
        </div>
        <div class="card">
            <div class="card-title">Pass Rate</div>
            <div class="card-value">{(passed_tests/total_tests)*100:.1f}%</div>
        </div>
        """

    def _build_results_table(self, test_results: List[Dict[str, Any]]) -> str:
        """Build results table HTML."""
        rows = []
        for result in test_results:
            test_id = result["test_id"]
            timestamp = datetime.fromtimestamp(result["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
            document_id = result["document_id"]
            strategy = result["routing"]["strategy"]
            duration = result["performance"]["total_duration_seconds"]
            entities = result["entity_distribution"]["total_entities"]
            confidence = result["quality"]["avg_confidence_score"]
            validation = result["quality"]["validation_passed"]

            status_class = "status-passed" if validation else "status-failed"
            status_text = "✅ PASSED" if validation else "❌ FAILED"

            rows.append(f"""
            <tr>
                <td>{test_id}</td>
                <td>{timestamp}</td>
                <td>{document_id}</td>
                <td>{strategy}</td>
                <td>{duration:.2f}s</td>
                <td>{entities}</td>
                <td>{confidence:.3f}</td>
                <td class="{status_class}">{status_text}</td>
            </tr>
            """)

        return f"""
        <table>
            <thead>
                <tr>
                    <th>Test ID</th>
                    <th>Timestamp</th>
                    <th>Document</th>
                    <th>Strategy</th>
                    <th>Duration</th>
                    <th>Entities</th>
                    <th>Confidence</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """

    def _prepare_chart_data(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare data for Chart.js visualizations."""
        # Performance over time
        timestamps = [datetime.fromtimestamp(r["timestamp"]).strftime('%H:%M:%S') for r in test_results]
        durations = [r["performance"]["total_duration_seconds"] for r in test_results]
        entities_per_sec = [r["performance"]["entities_per_second"] for r in test_results]

        # Wave execution (search for most recent test with wave data)
        wave_labels = []
        wave_durations = []
        wave_entities = []

        # Search test results in reverse order for most recent test with wave data
        for test_result in reversed(test_results):
            waves = test_result.get("waves", [])
            if waves:  # Found test with wave data
                wave_labels = [f"Wave {w['wave_number']}" for w in waves]
                wave_durations = [w["duration_seconds"] for w in waves]
                wave_entities = [w["entities_extracted"] for w in waves]
                break

        # Confidence distribution (use latest test)
        latest_test = test_results[-1]
        quality = latest_test["quality"]
        confidence_data = {
            "Low (<0.7)": quality["low_confidence_count"],
            "Medium (0.7-0.9)": quality["medium_confidence_count"],
            "High (≥0.9)": quality["high_confidence_count"]
        }

        # Entity types (aggregate from latest test)
        entity_types = latest_test["entity_distribution"]["entities_by_type"]
        top_types = dict(sorted(entity_types.items(), key=lambda x: x[1], reverse=True)[:10])

        return {
            "timestamps": timestamps,
            "durations": durations,
            "entities_per_sec": entities_per_sec,
            "wave_labels": wave_labels,
            "wave_durations": wave_durations,
            "wave_entities": wave_entities,
            "confidence_labels": list(confidence_data.keys()),
            "confidence_values": list(confidence_data.values()),
            "entity_type_labels": list(top_types.keys()),
            "entity_type_values": list(top_types.values())
        }

    def _get_chart_scripts(self, chart_data: Dict[str, Any]) -> str:
        """Generate Chart.js initialization scripts."""
        return f"""
        // Performance Over Time
        new Chart(document.getElementById('performanceChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(chart_data["timestamps"])},
                datasets: [{{
                    label: 'Duration (seconds)',
                    data: {json.dumps(chart_data["durations"])},
                    borderColor: 'rgb(102, 126, 234)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: true }}
                }}
            }}
        }});

        // Wave Execution Times
        (function() {{
            const waveLabels = {json.dumps(chart_data["wave_labels"])};
            const waveDurations = {json.dumps(chart_data["wave_durations"])};
            const canvas = document.getElementById('waveTimesChart');

            if (waveLabels.length === 0 || waveDurations.length === 0) {{
                // Display informative message when no wave data
                const ctx = canvas.getContext('2d');
                canvas.height = 200;
                ctx.font = '16px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
                ctx.fillStyle = '#718096';
                ctx.textAlign = 'center';
                ctx.fillText('No multi-wave test data available.', canvas.width / 2, canvas.height / 2 - 20);
                ctx.font = '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
                ctx.fillText('Run a three_wave or four_wave test to see wave breakdown.', canvas.width / 2, canvas.height / 2 + 10);
            }} else {{
                new Chart(canvas, {{
                    type: 'bar',
                    data: {{
                        labels: waveLabels,
                        datasets: [{{
                            label: 'Duration (seconds)',
                            data: waveDurations,
                            backgroundColor: 'rgba(102, 126, 234, 0.7)'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{ display: false }}
                        }}
                    }}
                }});
            }}
        }})();

        // Entities Per Wave
        (function() {{
            const waveLabels = {json.dumps(chart_data["wave_labels"])};
            const waveEntities = {json.dumps(chart_data["wave_entities"])};
            const canvas = document.getElementById('entitiesPerWaveChart');

            if (waveLabels.length === 0 || waveEntities.length === 0) {{
                // Display informative message when no wave data
                const ctx = canvas.getContext('2d');
                canvas.height = 200;
                ctx.font = '16px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
                ctx.fillStyle = '#718096';
                ctx.textAlign = 'center';
                ctx.fillText('No multi-wave test data available.', canvas.width / 2, canvas.height / 2 - 20);
                ctx.font = '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
                ctx.fillText('Run a three_wave or four_wave test to see wave breakdown.', canvas.width / 2, canvas.height / 2 + 10);
            }} else {{
                new Chart(canvas, {{
                    type: 'bar',
                    data: {{
                        labels: waveLabels,
                        datasets: [{{
                            label: 'Entities Extracted',
                            data: waveEntities,
                            backgroundColor: 'rgba(118, 75, 162, 0.7)'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{ display: false }}
                        }}
                    }}
                }});
            }}
        }})();

        // Confidence Distribution
        new Chart(document.getElementById('confidenceChart'), {{
            type: 'pie',
            data: {{
                labels: {json.dumps(chart_data["confidence_labels"])},
                datasets: [{{
                    data: {json.dumps(chart_data["confidence_values"])},
                    backgroundColor: [
                        'rgba(245, 101, 101, 0.7)',
                        'rgba(237, 137, 54, 0.7)',
                        'rgba(72, 187, 120, 0.7)'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom' }}
                }}
            }}
        }});

        // Top Entity Types
        new Chart(document.getElementById('entityTypesChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(chart_data["entity_type_labels"])},
                datasets: [{{
                    label: 'Count',
                    data: {json.dumps(chart_data["entity_type_values"])},
                    backgroundColor: 'rgba(102, 126, 234, 0.7)'
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});

        // Throughput Metrics
        new Chart(document.getElementById('throughputChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(chart_data["timestamps"])},
                datasets: [{{
                    label: 'Entities/Second',
                    data: {json.dumps(chart_data["entities_per_sec"])},
                    borderColor: 'rgb(72, 187, 120)',
                    backgroundColor: 'rgba(72, 187, 120, 0.1)',
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: true }}
                }}
            }}
        }});
        """


if __name__ == "__main__":
    # Example usage with mock data
    logging.basicConfig(level=logging.INFO)

    mock_results = [
        {{
            "test_id": "test_001",
            "timestamp": 1234567890.0,
            "document_id": "rahimi_2024",
            "routing": {{"strategy": "three_wave"}},
            "performance": {{
                "total_duration_seconds": 0.92,
                "entities_per_second": 154.35
            }},
            "entity_distribution": {{
                "total_entities": 142,
                "entities_by_type": {{"CASE": 45, "STATUTE": 38, "DATE": 59}}
            }},
            "quality": {{
                "avg_confidence_score": 0.89,
                "low_confidence_count": 12,
                "medium_confidence_count": 48,
                "high_confidence_count": 82,
                "validation_passed": True
            }},
            "waves": [
                {{"wave_number": 1, "duration_seconds": 0.25, "entities_extracted": 65}},
                {{"wave_number": 2, "duration_seconds": 0.22, "entities_extracted": 38}},
                {{"wave_number": 3, "duration_seconds": 0.23, "entities_extracted": 25}},
                {{"wave_number": 4, "duration_seconds": 0.22, "entities_extracted": 14}}
            ]
        }}
    ]

    generator = HTMLDashboardGenerator()
    output_path = Path("/tmp/test_dashboard.html")
    generator.generate_dashboard(mock_results, output_path)
    print(f"Dashboard generated: {output_path}")
