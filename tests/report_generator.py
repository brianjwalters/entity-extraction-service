#!/usr/bin/env python3
"""
Comprehensive HTML Report Generator for vLLM Optimization Tests
Generates interactive HTML reports with entity values, performance metrics, and visualizations
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import re
from collections import defaultdict, Counter
import statistics

class VLLMOptimizationReportGenerator:
    """Generate comprehensive HTML reports for vLLM optimization test results"""
    
    def __init__(self, results_dir: str = None):
        """Initialize report generator with results directory"""
        self.results_dir = Path(results_dir or "/srv/luris/be/entity-extraction-service/tests/results")
        self.test_results = []
        self.all_entities = []
        self.entity_type_counts = defaultdict(int)
        self.entity_values_by_type = defaultdict(list)
        
    def load_test_results(self, pattern: str = "vllm_test_*.json") -> List[Dict]:
        """Load all test result JSON files matching pattern"""
        test_files = sorted(self.results_dir.glob(pattern))
        
        for test_file in test_files:
            try:
                with open(test_file, 'r') as f:
                    data = json.load(f)
                    # Add filename for reference
                    data['_filename'] = test_file.name
                    self.test_results.append(data)
                    
                    # Extract all entities for detailed display
                    if 'extracted_entities' in data:
                        for entity in data['extracted_entities']:
                            entity['_test_config'] = data.get('config_id', 'unknown')
                            entity['_extraction_time'] = data.get('extraction_time', 0)
                            self.all_entities.append(entity)
                            
                            # Count by type
                            entity_type = entity.get('type', 'unknown')
                            entity_value = entity.get('value', '')
                            self.entity_type_counts[entity_type] += 1
                            self.entity_values_by_type[entity_type].append({
                                'value': entity_value,
                                'confidence': entity.get('confidence', 0),
                                'config': entity['_test_config']
                            })
                            
            except Exception as e:
                print(f"Error loading {test_file}: {e}")
                
        return self.test_results
    
    def find_best_configurations(self) -> Dict[str, Any]:
        """Analyze results to find best configurations"""
        if not self.test_results:
            return {}
            
        # Sort by different metrics
        fastest = min(self.test_results, key=lambda x: x.get('extraction_time', float('inf')))
        most_entities = max(self.test_results, key=lambda x: x.get('entity_count', 0))
        
        # Calculate balanced score (normalized)
        max_entities = max(r.get('entity_count', 0) for r in self.test_results)
        min_time = min(r.get('extraction_time', float('inf')) for r in self.test_results)
        max_time = max(r.get('extraction_time', 0) for r in self.test_results)
        
        for result in self.test_results:
            entities_score = result.get('entity_count', 0) / max_entities if max_entities > 0 else 0
            time_score = 1 - ((result.get('extraction_time', max_time) - min_time) / (max_time - min_time)) if max_time > min_time else 0
            result['_balanced_score'] = (entities_score + time_score) / 2
            
        best_balanced = max(self.test_results, key=lambda x: x.get('_balanced_score', 0))
        
        return {
            'fastest': fastest,
            'most_entities': most_entities,
            'best_balanced': best_balanced
        }
    
    def generate_entity_table_html(self, entities: List[Dict], table_id: str = "entityTable") -> str:
        """Generate HTML for searchable entity table"""
        if not entities:
            return "<p>No entities extracted</p>"
            
        rows = []
        for entity in entities:
            confidence = entity.get('confidence', 0)
            confidence_class = 'high-confidence' if confidence > 0.9 else 'medium-confidence' if confidence > 0.7 else 'low-confidence'
            
            row = f"""
                <tr class="{confidence_class}">
                    <td>{entity.get('type', 'unknown')}</td>
                    <td class="entity-value">{entity.get('value', '')}</td>
                    <td>{confidence:.3f}</td>
                    <td>{entity.get('document', 'N/A')}</td>
                    <td>{entity.get('strategy', 'N/A')}</td>
                    <td>{entity.get('_test_config', 'N/A')}</td>
                </tr>
            """
            rows.append(row)
            
        return f"""
        <div class="entity-table-container">
            <div class="table-controls">
                <input type="text" id="{table_id}Search" class="search-box" placeholder="Search entities...">
                <select id="{table_id}TypeFilter" class="type-filter">
                    <option value="">All Entity Types</option>
                    {''.join(f'<option value="{t}">{t}</option>' for t in sorted(self.entity_type_counts.keys()))}
                </select>
                <button onclick="exportTableToCSV('{table_id}')" class="export-btn">Export to CSV</button>
            </div>
            <table id="{table_id}" class="entity-table">
                <thead>
                    <tr>
                        <th onclick="sortTable('{table_id}', 0)">Entity Type ↕</th>
                        <th onclick="sortTable('{table_id}', 1)">Entity Value ↕</th>
                        <th onclick="sortTable('{table_id}', 2)">Confidence ↕</th>
                        <th onclick="sortTable('{table_id}', 3)">Document ↕</th>
                        <th onclick="sortTable('{table_id}', 4)">Strategy ↕</th>
                        <th onclick="sortTable('{table_id}', 5)">Config ↕</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """
    
    def generate_configuration_matrix_html(self) -> str:
        """Generate performance matrix table for all configurations"""
        if not self.test_results:
            return "<p>No test results available</p>"
            
        rows = []
        for result in sorted(self.test_results, key=lambda x: x.get('config_id', '')):
            extraction_time = result.get('extraction_time', 0)
            entity_count = result.get('entity_count', 0)
            gpu_util = result.get('gpu_utilization', 0)
            
            # Color coding for performance
            time_class = 'good' if extraction_time < 2 else 'average' if extraction_time < 5 else 'poor'
            entity_class = 'good' if entity_count > 150 else 'average' if entity_count > 100 else 'poor'
            gpu_class = 'good' if 40 <= gpu_util <= 80 else 'average' if 20 <= gpu_util <= 90 else 'poor'
            
            row = f"""
                <tr class="config-row" onclick="showConfigDetails('{result.get('config_id', 'unknown')}')">
                    <td>{result.get('config_id', 'N/A')}</td>
                    <td>{result.get('gpu_setup', 'N/A')}</td>
                    <td>{result.get('gpu_memory_utilization', 'N/A')}%</td>
                    <td>{result.get('max_batch_size', 'N/A')}</td>
                    <td class="{time_class}">{extraction_time:.2f}s</td>
                    <td class="{entity_class}">{entity_count}</td>
                    <td class="{gpu_class}">{gpu_util:.1f}%</td>
                    <td>{result.get('temperature', 'N/A')}°C</td>
                    <td>{result.get('throughput', 0):.1f} tok/s</td>
                </tr>
            """
            rows.append(row)
            
        return f"""
        <div class="matrix-container">
            <table id="configMatrix" class="config-matrix">
                <thead>
                    <tr>
                        <th onclick="sortTable('configMatrix', 0)">Config ID ↕</th>
                        <th onclick="sortTable('configMatrix', 1)">GPU Setup ↕</th>
                        <th onclick="sortTable('configMatrix', 2)">Memory % ↕</th>
                        <th onclick="sortTable('configMatrix', 3)">Batch Size ↕</th>
                        <th onclick="sortTable('configMatrix', 4)">Time (s) ↕</th>
                        <th onclick="sortTable('configMatrix', 5)">Entities ↕</th>
                        <th onclick="sortTable('configMatrix', 6)">GPU Util % ↕</th>
                        <th onclick="sortTable('configMatrix', 7)">Temp °C ↕</th>
                        <th onclick="sortTable('configMatrix', 8)">Throughput ↕</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """
    
    def generate_charts_data(self) -> Dict[str, Any]:
        """Prepare data for Chart.js visualizations"""
        chart_data = {
            'configs': [],
            'extraction_times': [],
            'entity_counts': [],
            'gpu_utilizations': [],
            'temperatures': [],
            'throughputs': [],
            'entity_type_distribution': {}
        }
        
        for result in sorted(self.test_results, key=lambda x: x.get('config_id', '')):
            chart_data['configs'].append(result.get('config_id', 'unknown'))
            chart_data['extraction_times'].append(result.get('extraction_time', 0))
            chart_data['entity_counts'].append(result.get('entity_count', 0))
            chart_data['gpu_utilizations'].append(result.get('gpu_utilization', 0))
            chart_data['temperatures'].append(result.get('temperature', 0))
            chart_data['throughputs'].append(result.get('throughput', 0))
            
        # Entity type distribution
        chart_data['entity_type_distribution'] = dict(self.entity_type_counts)
        
        return chart_data
    
    def generate_html_report(self, output_file: str = None) -> str:
        """Generate complete HTML report with all sections"""
        if output_file is None:
            output_file = self.results_dir / "vllm_optimization_report.html"
            
        # Load all test results
        self.load_test_results()
        
        # Find best configurations
        best_configs = self.find_best_configurations()
        
        # Prepare chart data
        chart_data = self.generate_charts_data()
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>vLLM Optimization Report - Entity Extraction Analysis</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --primary-color: #2563eb;
            --secondary-color: #10b981;
            --danger-color: #ef4444;
            --warning-color: #f59e0b;
            --bg-color: #ffffff;
            --text-color: #1f2937;
            --border-color: #e5e7eb;
            --hover-bg: #f3f4f6;
        }}
        
        [data-theme="dark"] {{
            --bg-color: #1f2937;
            --text-color: #f9fafb;
            --border-color: #374151;
            --hover-bg: #374151;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            transition: all 0.3s ease;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        
        .timestamp {{
            opacity: 0.9;
            font-size: 0.9rem;
        }}
        
        .theme-toggle {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            z-index: 1000;
        }}
        
        .section {{
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }}
        
        h2 {{
            color: var(--primary-color);
            margin-bottom: 20px;
            font-size: 1.8rem;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 10px;
        }}
        
        h3 {{
            color: var(--text-color);
            margin: 15px 0;
            font-size: 1.3rem;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .summary-card h4 {{
            font-size: 1.2rem;
            margin-bottom: 10px;
            opacity: 0.9;
        }}
        
        .summary-card .metric {{
            font-size: 2rem;
            font-weight: bold;
            margin: 10px 0;
        }}
        
        .summary-card .details {{
            font-size: 0.9rem;
            opacity: 0.85;
            margin-top: 10px;
        }}
        
        .entity-table-container {{
            margin-top: 20px;
            overflow-x: auto;
        }}
        
        .table-controls {{
            display: flex;
            gap: 15px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        
        .search-box, .type-filter {{
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            background: var(--bg-color);
            color: var(--text-color);
            font-size: 0.95rem;
        }}
        
        .search-box {{
            flex: 1;
            min-width: 200px;
        }}
        
        .export-btn {{
            background: var(--secondary-color);
            color: white;
            border: none;
            padding: 8px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s ease;
        }}
        
        .export-btn:hover {{
            background: #059669;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--bg-color);
        }}
        
        th {{
            background: var(--primary-color);
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        th:hover {{
            background: #1d4ed8;
        }}
        
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        tr:hover {{
            background: var(--hover-bg);
        }}
        
        .entity-value {{
            font-family: 'Courier New', monospace;
            font-weight: 500;
            color: var(--primary-color);
        }}
        
        .high-confidence {{
            background: rgba(16, 185, 129, 0.1);
        }}
        
        .medium-confidence {{
            background: rgba(245, 158, 11, 0.1);
        }}
        
        .low-confidence {{
            background: rgba(239, 68, 68, 0.1);
        }}
        
        .good {{
            color: var(--secondary-color);
            font-weight: 600;
        }}
        
        .average {{
            color: var(--warning-color);
            font-weight: 600;
        }}
        
        .poor {{
            color: var(--danger-color);
            font-weight: 600;
        }}
        
        .config-row {{
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .config-row:hover {{
            background: var(--hover-bg);
            transform: translateX(5px);
        }}
        
        .chart-container {{
            margin: 20px 0;
            padding: 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }}
        
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        canvas {{
            max-height: 400px;
        }}
        
        .collapsible {{
            background: var(--primary-color);
            color: white;
            cursor: pointer;
            padding: 15px;
            width: 100%;
            border: none;
            text-align: left;
            outline: none;
            font-size: 1.1rem;
            font-weight: 500;
            border-radius: 5px;
            margin-top: 10px;
            transition: all 0.3s ease;
        }}
        
        .collapsible:hover {{
            background: #1d4ed8;
        }}
        
        .collapsible:after {{
            content: '\\002B';
            color: white;
            float: right;
            font-weight: bold;
            font-size: 1.2rem;
        }}
        
        .active:after {{
            content: "\\2212";
        }}
        
        .collapsible-content {{
            padding: 0 18px;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease;
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            border-top: none;
            border-radius: 0 0 5px 5px;
        }}
        
        .entity-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        
        .stat-card {{
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary-color);
        }}
        
        .stat-label {{
            font-size: 0.9rem;
            color: var(--text-color);
            opacity: 0.8;
            margin-top: 5px;
        }}
        
        .recommendation-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        
        .recommendation-box h4 {{
            font-size: 1.3rem;
            margin-bottom: 15px;
        }}
        
        .recommendation-box ul {{
            list-style: none;
            padding-left: 0;
        }}
        
        .recommendation-box li {{
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }}
        
        .recommendation-box li:last-child {{
            border-bottom: none;
        }}
        
        @media print {{
            .theme-toggle, .export-btn {{
                display: none;
            }}
            
            body {{
                background: white;
                color: black;
            }}
            
            .section {{
                page-break-inside: avoid;
            }}
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            h1 {{
                font-size: 1.8rem;
            }}
            
            .chart-grid {{
                grid-template-columns: 1fr;
            }}
            
            .summary-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <button class="theme-toggle" onclick="toggleTheme()">🌙 Dark Mode</button>
    
    <div class="container">
        <header>
            <h1>vLLM Optimization Report</h1>
            <p class="timestamp">Generated: {timestamp}</p>
            <p>Entity Extraction Performance Analysis</p>
        </header>
        
        <!-- Executive Summary -->
        <section class="section">
            <h2>Executive Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <h4>⚡ Fastest Configuration</h4>
                    <div class="metric">{best_configs.get('fastest', {}).get('config_id', 'N/A')}</div>
                    <div class="details">
                        Extraction Time: {best_configs.get('fastest', {}).get('extraction_time', 0):.2f}s<br>
                        Entities Found: {best_configs.get('fastest', {}).get('entity_count', 0)}<br>
                        GPU Setup: {best_configs.get('fastest', {}).get('gpu_setup', 'N/A')}
                    </div>
                </div>
                
                <div class="summary-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                    <h4>🎯 Most Accurate</h4>
                    <div class="metric">{best_configs.get('most_entities', {}).get('config_id', 'N/A')}</div>
                    <div class="details">
                        Entities Found: {best_configs.get('most_entities', {}).get('entity_count', 0)}<br>
                        Extraction Time: {best_configs.get('most_entities', {}).get('extraction_time', 0):.2f}s<br>
                        GPU Setup: {best_configs.get('most_entities', {}).get('gpu_setup', 'N/A')}
                    </div>
                </div>
                
                <div class="summary-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
                    <h4>⚖️ Best Balanced</h4>
                    <div class="metric">{best_configs.get('best_balanced', {}).get('config_id', 'N/A')}</div>
                    <div class="details">
                        Balance Score: {best_configs.get('best_balanced', {}).get('_balanced_score', 0):.2%}<br>
                        Entities: {best_configs.get('best_balanced', {}).get('entity_count', 0)} | Time: {best_configs.get('best_balanced', {}).get('extraction_time', 0):.2f}s<br>
                        GPU Setup: {best_configs.get('best_balanced', {}).get('gpu_setup', 'N/A')}
                    </div>
                </div>
            </div>
            
            <div class="entity-stats">
                <div class="stat-card">
                    <div class="stat-value">{len(self.all_entities):,}</div>
                    <div class="stat-label">Total Entities Extracted</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(self.entity_type_counts)}</div>
                    <div class="stat-label">Unique Entity Types</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(self.test_results)}</div>
                    <div class="stat-label">Configurations Tested</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{sum(r.get('extraction_time', 0) for r in self.test_results):.1f}s</div>
                    <div class="stat-label">Total Test Time</div>
                </div>
            </div>
        </section>
        
        <!-- Configuration Performance Matrix -->
        <section class="section">
            <h2>Configuration Performance Matrix</h2>
            <p>Click on any configuration row to see detailed extraction results</p>
            {self.generate_configuration_matrix_html()}
        </section>
        
        <!-- Entity Extraction Results -->
        <section class="section">
            <h2>🔍 Entity Extraction Results (ALL VALUES)</h2>
            <p>Complete list of all {len(self.all_entities):,} entities extracted across all test configurations</p>
            
            <button class="collapsible">View All Extracted Entities</button>
            <div class="collapsible-content">
                {self.generate_entity_table_html(self.all_entities, "allEntitiesTable")}
            </div>
            
            <h3>Entity Type Distribution</h3>
            <div class="chart-container">
                <canvas id="entityTypePieChart"></canvas>
            </div>
            
            <h3>Most Common Entity Values by Type</h3>
            <div id="commonEntitiesContainer"></div>
        </section>
        
        <!-- Performance Visualizations -->
        <section class="section">
            <h2>📊 Performance Visualizations</h2>
            <div class="chart-grid">
                <div class="chart-container">
                    <h3>Extraction Time Comparison</h3>
                    <canvas id="extractionTimeChart"></canvas>
                </div>
                
                <div class="chart-container">
                    <h3>Entity Count by Configuration</h3>
                    <canvas id="entityCountChart"></canvas>
                </div>
                
                <div class="chart-container">
                    <h3>GPU Utilization</h3>
                    <canvas id="gpuUtilChart"></canvas>
                </div>
                
                <div class="chart-container">
                    <h3>Speed vs Accuracy</h3>
                    <canvas id="speedAccuracyChart"></canvas>
                </div>
                
                <div class="chart-container">
                    <h3>Throughput Performance</h3>
                    <canvas id="throughputChart"></canvas>
                </div>
                
                <div class="chart-container">
                    <h3>Temperature Monitoring</h3>
                    <canvas id="temperatureChart"></canvas>
                </div>
            </div>
        </section>
        
        <!-- Detailed Test Results -->
        <section class="section">
            <h2>📋 Detailed Test Results</h2>
            <p>Click to expand individual configuration results</p>
            <div id="detailedResults"></div>
        </section>
        
        <!-- Recommendations -->
        <section class="section">
            <h2>💡 Recommendations</h2>
            <div class="recommendation-box">
                <h4>Optimal Production Configuration</h4>
                <ul>
                    <li>✅ <strong>Recommended Config:</strong> {best_configs.get('best_balanced', {}).get('config_id', 'N/A')}</li>
                    <li>✅ <strong>GPU Setup:</strong> {best_configs.get('best_balanced', {}).get('gpu_setup', 'Dual GPU recommended')}</li>
                    <li>✅ <strong>Memory Utilization:</strong> {best_configs.get('best_balanced', {}).get('gpu_memory_utilization', '85')}%</li>
                    <li>✅ <strong>Batch Size:</strong> {best_configs.get('best_balanced', {}).get('max_batch_size', '32')}</li>
                    <li>✅ <strong>Expected Performance:</strong> ~{best_configs.get('best_balanced', {}).get('entity_count', 150)} entities in {best_configs.get('best_balanced', {}).get('extraction_time', 3):.1f}s</li>
                </ul>
            </div>
            
            <div class="recommendation-box" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <h4>Deployment Command</h4>
                <ul>
                    <li>
                        <code style="background: rgba(0,0,0,0.2); padding: 10px; border-radius: 5px; display: block;">
                        vllm serve mistralai/Mistral-Nemo-Instruct-2407 \\<br>
                        &nbsp;&nbsp;--gpu-memory-utilization {best_configs.get('best_balanced', {}).get('gpu_memory_utilization', '0.85')} \\<br>
                        &nbsp;&nbsp;--max-model-len 131072 \\<br>
                        &nbsp;&nbsp;--max-batch-size {best_configs.get('best_balanced', {}).get('max_batch_size', '32')} \\<br>
                        &nbsp;&nbsp;--port 8080
                        </code>
                    </li>
                </ul>
            </div>
        </section>
    </div>
    
    <script>
        // Chart data from Python
        const chartData = {json.dumps(chart_data, indent=2)};
        
        // Theme toggle
        function toggleTheme() {{
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            
            const btn = document.querySelector('.theme-toggle');
            btn.textContent = newTheme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode';
        }}
        
        // Table sorting
        function sortTable(tableId, columnIndex) {{
            const table = document.getElementById(tableId);
            const tbody = table.getElementsByTagName('tbody')[0];
            const rows = Array.from(tbody.getElementsByTagName('tr'));
            
            const isNumeric = !isNaN(parseFloat(rows[0]?.cells[columnIndex]?.textContent));
            
            rows.sort((a, b) => {{
                let aVal = a.cells[columnIndex].textContent.trim();
                let bVal = b.cells[columnIndex].textContent.trim();
                
                if (isNumeric) {{
                    aVal = parseFloat(aVal) || 0;
                    bVal = parseFloat(bVal) || 0;
                    return aVal - bVal;
                }} else {{
                    return aVal.localeCompare(bVal);
                }}
            }});
            
            // Toggle sort direction
            if (table.getAttribute('data-sort-dir') === 'asc') {{
                rows.reverse();
                table.setAttribute('data-sort-dir', 'desc');
            }} else {{
                table.setAttribute('data-sort-dir', 'asc');
            }}
            
            // Reattach rows
            rows.forEach(row => tbody.appendChild(row));
        }}
        
        // Table search and filter
        document.addEventListener('DOMContentLoaded', function() {{
            // Search functionality for all entity tables
            document.querySelectorAll('.search-box').forEach(searchBox => {{
                searchBox.addEventListener('keyup', function() {{
                    const tableId = this.id.replace('Search', '');
                    filterTable(tableId);
                }});
            }});
            
            // Type filter functionality
            document.querySelectorAll('.type-filter').forEach(filter => {{
                filter.addEventListener('change', function() {{
                    const tableId = this.id.replace('TypeFilter', '');
                    filterTable(tableId);
                }});
            }});
            
            // Initialize collapsibles
            const collapsibles = document.getElementsByClassName("collapsible");
            for (let i = 0; i < collapsibles.length; i++) {{
                collapsibles[i].addEventListener("click", function() {{
                    this.classList.toggle("active");
                    const content = this.nextElementSibling;
                    if (content.style.maxHeight) {{
                        content.style.maxHeight = null;
                    }} else {{
                        content.style.maxHeight = content.scrollHeight + "px";
                    }}
                }});
            }}
            
            // Initialize charts
            initializeCharts();
            
            // Generate common entities display
            generateCommonEntities();
            
            // Generate detailed results
            generateDetailedResults();
        }});
        
        function filterTable(tableId) {{
            const table = document.getElementById(tableId);
            const searchBox = document.getElementById(tableId + 'Search');
            const typeFilter = document.getElementById(tableId + 'TypeFilter');
            const searchValue = searchBox?.value.toLowerCase() || '';
            const typeValue = typeFilter?.value || '';
            
            const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            
            for (let row of rows) {{
                const entityType = row.cells[0].textContent;
                const entityValue = row.cells[1].textContent.toLowerCase();
                
                const matchesSearch = !searchValue || entityValue.includes(searchValue);
                const matchesType = !typeValue || entityType === typeValue;
                
                row.style.display = matchesSearch && matchesType ? '' : 'none';
            }}
        }}
        
        // Export table to CSV
        function exportTableToCSV(tableId) {{
            const table = document.getElementById(tableId);
            const rows = table.querySelectorAll('tr');
            const csv = [];
            
            for (let row of rows) {{
                const cells = row.querySelectorAll('td, th');
                const rowData = Array.from(cells).map(cell => {{
                    let text = cell.textContent.replace(/"/g, '""');
                    return `"${{text}}"`;
                }});
                csv.push(rowData.join(','));
            }}
            
            const blob = new Blob([csv.join('\\n')], {{ type: 'text/csv' }});
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.setAttribute('href', url);
            a.setAttribute('download', `${{tableId}}_export.csv`);
            a.click();
        }}
        
        // Initialize all charts
        function initializeCharts() {{
            // Entity Type Pie Chart
            const pieCtx = document.getElementById('entityTypePieChart').getContext('2d');
            new Chart(pieCtx, {{
                type: 'pie',
                data: {{
                    labels: Object.keys(chartData.entity_type_distribution),
                    datasets: [{{
                        data: Object.values(chartData.entity_type_distribution),
                        backgroundColor: [
                            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                            '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
                        ]
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'right'
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${{label}}: ${{value}} (${{percentage}}%)`;
                                }}
                            }}
                        }}
                    }}
                }}
            }});
            
            // Extraction Time Chart
            const timeCtx = document.getElementById('extractionTimeChart').getContext('2d');
            new Chart(timeCtx, {{
                type: 'bar',
                data: {{
                    labels: chartData.configs,
                    datasets: [{{
                        label: 'Extraction Time (seconds)',
                        data: chartData.extraction_times,
                        backgroundColor: 'rgba(37, 99, 235, 0.5)',
                        borderColor: 'rgba(37, 99, 235, 1)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }});
            
            // Entity Count Chart
            const countCtx = document.getElementById('entityCountChart').getContext('2d');
            new Chart(countCtx, {{
                type: 'bar',
                data: {{
                    labels: chartData.configs,
                    datasets: [{{
                        label: 'Entities Extracted',
                        data: chartData.entity_counts,
                        backgroundColor: 'rgba(16, 185, 129, 0.5)',
                        borderColor: 'rgba(16, 185, 129, 1)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }});
            
            // GPU Utilization Chart
            const gpuCtx = document.getElementById('gpuUtilChart').getContext('2d');
            new Chart(gpuCtx, {{
                type: 'line',
                data: {{
                    labels: chartData.configs,
                    datasets: [{{
                        label: 'GPU Utilization (%)',
                        data: chartData.gpu_utilizations,
                        borderColor: 'rgba(245, 158, 11, 1)',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        tension: 0.4
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            max: 100
                        }}
                    }}
                }}
            }});
            
            // Speed vs Accuracy Scatter Plot
            const scatterCtx = document.getElementById('speedAccuracyChart').getContext('2d');
            const scatterData = chartData.configs.map((config, i) => ({{
                x: chartData.extraction_times[i],
                y: chartData.entity_counts[i],
                label: config
            }}));
            
            new Chart(scatterCtx, {{
                type: 'scatter',
                data: {{
                    datasets: [{{
                        label: 'Speed vs Accuracy',
                        data: scatterData,
                        backgroundColor: 'rgba(147, 51, 234, 0.5)',
                        borderColor: 'rgba(147, 51, 234, 1)',
                        pointRadius: 8,
                        pointHoverRadius: 10
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return `${{context.raw.label}}: ${{context.raw.x.toFixed(2)}}s, ${{context.raw.y}} entities`;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            title: {{
                                display: true,
                                text: 'Extraction Time (seconds)'
                            }}
                        }},
                        y: {{
                            title: {{
                                display: true,
                                text: 'Entities Extracted'
                            }},
                            beginAtZero: true
                        }}
                    }}
                }}
            }});
            
            // Throughput Chart
            const throughputCtx = document.getElementById('throughputChart').getContext('2d');
            new Chart(throughputCtx, {{
                type: 'line',
                data: {{
                    labels: chartData.configs,
                    datasets: [{{
                        label: 'Throughput (tokens/sec)',
                        data: chartData.throughputs,
                        borderColor: 'rgba(239, 68, 68, 1)',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.4
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }});
            
            // Temperature Chart
            const tempCtx = document.getElementById('temperatureChart').getContext('2d');
            new Chart(tempCtx, {{
                type: 'line',
                data: {{
                    labels: chartData.configs,
                    datasets: [{{
                        label: 'GPU Temperature (°C)',
                        data: chartData.temperatures,
                        borderColor: 'rgba(59, 130, 246, 1)',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.4
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }});
        }}
        
        // Generate common entities display
        function generateCommonEntities() {{
            const container = document.getElementById('commonEntitiesContainer');
            const entityValuesByType = {json.dumps({k: v[:10] for k, v in self.entity_values_by_type.items()})};
            
            let html = '<div class="entity-type-grid">';
            for (const [type, values] of Object.entries(entityValuesByType)) {{
                html += `
                    <div class="entity-type-card">
                        <h4>${{type}} (Top 10)</h4>
                        <ul>
                `;
                
                values.forEach((item, index) => {{
                    html += `<li>${{index + 1}}. "${{item.value}}" (conf: ${{item.confidence.toFixed(3)}})</li>`;
                }});
                
                html += `
                        </ul>
                    </div>
                `;
            }}
            html += '</div>';
            
            container.innerHTML = html;
        }}
        
        // Generate detailed results section
        function generateDetailedResults() {{
            const container = document.getElementById('detailedResults');
            const testResults = {json.dumps(self.test_results[:5])};  // Limit to first 5 for performance
            
            let html = '';
            testResults.forEach(result => {{
                html += `
                    <button class="collapsible">Configuration ${{result.config_id}} - ${{result.entity_count}} entities in ${{result.extraction_time.toFixed(2)}}s</button>
                    <div class="collapsible-content">
                        <div class="config-details">
                            <h4>Configuration Details</h4>
                            <ul>
                                <li>GPU Setup: ${{result.gpu_setup}}</li>
                                <li>Memory Utilization: ${{result.gpu_memory_utilization}}%</li>
                                <li>Batch Size: ${{result.max_batch_size}}</li>
                                <li>Temperature: ${{result.temperature}}°C</li>
                                <li>Throughput: ${{result.throughput}} tokens/sec</li>
                            </ul>
                            
                            <h4>Extracted Entities Sample</h4>
                            <p>Showing first 20 entities from this configuration:</p>
                            <table class="entity-table">
                                <thead>
                                    <tr>
                                        <th>Type</th>
                                        <th>Value</th>
                                        <th>Confidence</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                
                const entities = result.extracted_entities || [];
                entities.slice(0, 20).forEach(entity => {{
                    html += `
                        <tr>
                            <td>${{entity.type}}</td>
                            <td class="entity-value">${{entity.value}}</td>
                            <td>${{entity.confidence.toFixed(3)}}</td>
                        </tr>
                    `;
                }});
                
                html += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
            }});
            
            container.innerHTML = html;
            
            // Re-initialize collapsibles for dynamic content
            const collapsibles = container.getElementsByClassName("collapsible");
            for (let i = 0; i < collapsibles.length; i++) {{
                collapsibles[i].addEventListener("click", function() {{
                    this.classList.toggle("active");
                    const content = this.nextElementSibling;
                    if (content.style.maxHeight) {{
                        content.style.maxHeight = null;
                    }} else {{
                        content.style.maxHeight = content.scrollHeight + "px";
                    }}
                }});
            }}
        }}
        
        // Show configuration details
        function showConfigDetails(configId) {{
            alert(`Configuration details for ${{configId}} would be shown here in a modal or expanded view.`);
        }}
    </script>
</body>
</html>
"""
        
        # Write the HTML report
        with open(output_file, 'w') as f:
            f.write(html_content)
            
        print(f"HTML report generated: {output_file}")
        return str(output_file)


def main():
    """Main entry point for report generation"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate HTML report for vLLM optimization tests')
    parser.add_argument('--results-dir', type=str, 
                       default='/srv/luris/be/entity-extraction-service/tests/results',
                       help='Directory containing test result JSON files')
    parser.add_argument('--output', type=str,
                       help='Output HTML file path')
    parser.add_argument('--pattern', type=str, default='vllm_test_*.json',
                       help='Pattern for test result files')
    
    args = parser.parse_args()
    
    # Generate report
    generator = VLLMOptimizationReportGenerator(args.results_dir)
    output_file = generator.generate_html_report(args.output)
    
    print(f"\n✅ Report generation complete!")
    print(f"📊 Processed {len(generator.test_results)} test configurations")
    print(f"🔍 Found {len(generator.all_entities)} total entities")
    print(f"📈 Identified {len(generator.entity_type_counts)} unique entity types")
    print(f"📄 Report saved to: {output_file}")
    print(f"\nOpen the report in a web browser to view interactive visualizations and entity details.")


if __name__ == "__main__":
    main()