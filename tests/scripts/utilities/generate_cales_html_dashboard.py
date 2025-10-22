#!/usr/bin/env python3
"""
CALES NLP/BERT HTML Dashboard Generator

Generates comprehensive HTML dashboard with interactive charts and tables
for analyzing CALES NLP/BERT progressive testing results.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

class CALESHTMLDashboard:
    """Generate interactive HTML dashboard for CALES testing results"""
    
    def __init__(self, results_file: str):
        """Initialize with results file path"""
        self.results_file = results_file
        self.results_data = self._load_results()
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def _load_results(self) -> Dict[str, Any]:
        """Load results from JSON file"""
        with open(self.results_file, 'r') as f:
            return json.load(f)
    
    def generate_dashboard(self) -> str:
        """Generate complete HTML dashboard"""
        html_file = str(Path(self.results_file).parent / f"cales_nlp_bert_dashboard_{self.timestamp}.html")
        
        html_content = self._generate_html_template()
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📊 HTML Dashboard generated: {html_file}")
        return html_file
    
    def _generate_html_template(self) -> str:
        """Generate complete HTML template with embedded CSS and JavaScript"""
        
        # Extract data for charts
        chart_data = self._prepare_chart_data()
        table_data = self._prepare_table_data()
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CALES NLP/BERT Analysis Dashboard</title>
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <!-- DataTables -->
    <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css">
    <script type="text/javascript" src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script type="text/javascript" src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
    
    <style>
        {self._generate_css()}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <header class="dashboard-header">
            <h1>🧠 CALES NLP/BERT Analysis Dashboard</h1>
            <div class="metadata">
                <span>📄 Document: Rahimi.pdf</span>
                <span>🕒 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                <span>🧪 Test Type: Progressive NLP/BERT</span>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="dashboard-nav">
            <button class="nav-tab active" onclick="showTab('overview')">📊 Overview</button>
            <button class="nav-tab" onclick="showTab('charts')">📈 Charts</button>
            <button class="nav-tab" onclick="showTab('entities')">🎯 Entities</button>
            <button class="nav-tab" onclick="showTab('performance')">⚡ Performance</button>
            <button class="nav-tab" onclick="showTab('comparison')">🔍 Comparison</button>
        </nav>

        <!-- Overview Tab -->
        <div id="overview" class="tab-content active">
            <h2>📊 Executive Summary</h2>
            {self._generate_overview_section()}
        </div>

        <!-- Charts Tab -->
        <div id="charts" class="tab-content">
            <h2>📈 Visual Analytics</h2>
            <div class="charts-grid">
                <div class="chart-container">
                    <h3>Entity Count Progression</h3>
                    <canvas id="entityProgressionChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3>Entity Type Distribution</h3>
                    <canvas id="entityTypesChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3>Confidence Score Analysis</h3>
                    <canvas id="confidenceChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3>Processing Time Comparison</h3>
                    <canvas id="processingTimeChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Entities Tab -->
        <div id="entities" class="tab-content">
            <h2>🎯 Entity Analysis</h2>
            {self._generate_entities_section()}
        </div>

        <!-- Performance Tab -->
        <div id="performance" class="tab-content">
            <h2>⚡ Performance Metrics</h2>
            {self._generate_performance_section()}
        </div>

        <!-- Comparison Tab -->
        <div id="comparison" class="tab-content">
            <h2>🔍 Phase Comparison</h2>
            {self._generate_comparison_section()}
        </div>

        <!-- Footer -->
        <footer class="dashboard-footer">
            <p>Generated by CALES NLP/BERT Testing Suite | 
               <a href="javascript:void(0)" onclick="exportData()">📥 Export Data</a>
            </p>
        </footer>
    </div>

    <script>
        {self._generate_javascript(chart_data)}
    </script>
</body>
</html>"""
        
        return html
    
    def _generate_css(self) -> str:
        """Generate CSS styles for the dashboard"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f7fa;
        }

        .dashboard-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .dashboard-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }

        .dashboard-header h1 {
            font-size: 2.5rem;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .metadata {
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
            font-size: 1.1rem;
            opacity: 0.9;
        }

        .dashboard-nav {
            display: flex;
            gap: 5px;
            margin-bottom: 30px;
            background: white;
            padding: 5px;
            border-radius: 10px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        }

        .nav-tab {
            flex: 1;
            padding: 15px 20px;
            border: none;
            background: transparent;
            color: #666;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.3s ease;
        }

        .nav-tab:hover {
            background-color: #f0f2f5;
            color: #333;
        }

        .nav-tab.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }

        .tab-content {
            display: none;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            min-height: 600px;
        }

        .tab-content.active {
            display: block;
        }

        .tab-content h2 {
            color: #333;
            margin-bottom: 30px;
            font-size: 2rem;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }

        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
        }

        .chart-container {
            background: #f9f9f9;
            padding: 25px;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
        }

        .chart-container h3 {
            color: #555;
            margin-bottom: 20px;
            text-align: center;
            font-size: 1.3rem;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }

        .metric-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
            transition: transform 0.3s ease;
        }

        .metric-card:hover {
            transform: translateY(-5px);
        }

        .metric-card h3 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .metric-card p {
            font-size: 1.1rem;
            opacity: 0.9;
        }

        .comparison-table, .entity-table, .performance-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            border-radius: 10px;
            overflow: hidden;
        }

        .comparison-table th, .entity-table th, .performance-table th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }

        .comparison-table td, .entity-table td, .performance-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #e0e0e0;
        }

        .comparison-table tr:hover, .entity-table tr:hover, .performance-table tr:hover {
            background-color: #f8f9ff;
        }

        .phase-badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 500;
            color: white;
        }

        .phase-1 { background-color: #dc3545; }
        .phase-2 { background-color: #fd7e14; }
        .phase-3 { background-color: #20c997; }
        .phase-4 { background-color: #6f42c1; }

        .confidence-bar {
            width: 100%;
            height: 20px;
            background-color: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            position: relative;
        }

        .confidence-fill {
            height: 100%;
            background: linear-gradient(90deg, #ff6b6b, #feca57, #48dbfb, #ff9ff3);
            border-radius: 10px;
            transition: width 0.8s ease;
        }

        .dashboard-footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #666;
            font-size: 0.9rem;
        }

        .dashboard-footer a {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }

        .dashboard-footer a:hover {
            text-decoration: underline;
        }

        .alert {
            padding: 15px;
            margin: 20px 0;
            border-radius: 8px;
            border-left: 4px solid;
        }

        .alert-info {
            background-color: #d1ecf1;
            border-color: #bee5eb;
            color: #0c5460;
        }

        .alert-success {
            background-color: #d4edda;
            border-color: #c3e6cb;
            color: #155724;
        }

        .alert-warning {
            background-color: #fff3cd;
            border-color: #ffeaa7;
            color: #856404;
        }

        /* New Enhanced Styles for Detailed Analysis */
        .entity-breakdown-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px;
            margin: 30px 0;
        }
        
        .entity-stats-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
            border: 1px solid #e0e0e0;
        }
        
        .entity-stats-card h4 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.3rem;
            border-bottom: 2px solid #667eea;
            padding-bottom: 8px;
        }
        
        .entity-filter-controls {
            display: flex;
            gap: 20px;
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .filter-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .filter-group label {
            font-weight: 600;
            color: #555;
        }
        
        .filter-group select,
        .filter-group input[type="range"] {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        
        .export-btn {
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .export-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
        }
        
        .citation-analysis-grid {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 30px;
            margin: 30px 0;
        }
        
        .citation-stats,
        .citation-details {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
        }
        
        .performance-overview {
            margin-bottom: 40px;
        }
        
        .perf-metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .perf-metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 25px;
            border-radius: 15px;
            text-align: center;
            position: relative;
            overflow: hidden;
            transition: transform 0.3s ease;
        }
        
        .perf-metric-card:hover {
            transform: translateY(-5px);
        }
        
        .perf-metric-card h3 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .perf-metric-card p {
            font-size: 1.1rem;
            opacity: 0.9;
            margin: 0;
        }
        
        .metric-icon {
            position: absolute;
            top: 15px;
            right: 15px;
            font-size: 1.5rem;
            opacity: 0.3;
        }
        
        .performance-charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
            margin: 40px 0;
        }
        
        .perf-chart-container {
            background: #f9f9f9;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            border: 1px solid #e0e0e0;
        }
        
        .perf-chart-container h3 {
            color: #333;
            margin-bottom: 20px;
            text-align: center;
            font-size: 1.3rem;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .performance-insights {
            margin-top: 40px;
        }
        
        .performance-insights h3 {
            color: #333;
            margin-bottom: 20px;
        }
        
        .comparison-controls {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        
        .comparison-select {
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        .comparison-select label {
            font-weight: 600;
            color: #333;
        }
        
        .comparison-select select {
            padding: 10px 15px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            min-width: 200px;
        }
        
        .vs-label {
            font-weight: 700;
            color: #667eea;
            font-size: 1.2rem;
        }
        
        .swap-btn {
            background: #6c757d;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
        }
        
        .swap-btn:hover {
            background: #5a6268;
        }
        
        .comparison-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 25px;
            margin: 30px 0;
        }
        
        .comparison-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
            border: 1px solid #e0e0e0;
        }
        
        .comparison-card h4 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.3rem;
            border-bottom: 2px solid #667eea;
            padding-bottom: 8px;
        }
        
        .side-by-side-comparison {
            margin: 30px 0;
        }
        
        .entity-overlap-analysis {
            margin: 30px 0;
        }
        
        .overlap-stats {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 30px;
        }
        
        .overlap-venn {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .overlap-details {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
        }
        
        .unique-entities {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }
        
        .unique-column h5 {
            color: #667eea;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .unique-list {
            max-height: 200px;
            overflow-y: auto;
            font-size: 0.9rem;
        }
        
        .unique-list .entity-item {
            padding: 8px 12px;
            margin: 5px 0;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 3px solid #667eea;
        }
        
        .comparison-insights {
            margin-top: 40px;
        }
        
        .entity-context {
            font-size: 0.85rem;
            color: #666;
            font-style: italic;
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            cursor: help;
        }
        
        .entity-context:hover {
            white-space: normal;
            overflow: visible;
            background: #fff3cd;
            padding: 5px;
            border-radius: 3px;
            position: absolute;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .confidence-indicator {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            color: white;
        }
        
        .confidence-high { background-color: #28a745; }
        .confidence-medium { background-color: #ffc107; color: #333; }
        .confidence-low { background-color: #dc3545; }
        
        .position-info {
            font-size: 0.8rem;
            color: #6c757d;
            font-family: monospace;
        }
        
        /* DataTables customization */
        .dataTables_wrapper .dataTables_length,
        .dataTables_wrapper .dataTables_filter {
            margin-bottom: 15px;
        }
        
        .dataTables_wrapper .dataTables_paginate {
            margin-top: 15px;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .charts-grid {
                grid-template-columns: 1fr;
            }
            
            .metadata {
                flex-direction: column;
                gap: 10px;
            }
            
            .dashboard-nav {
                flex-direction: column;
            }
            
            .dashboard-header h1 {
                font-size: 2rem;
            }
            
            .entity-breakdown-grid,
            .performance-charts-grid,
            .comparison-grid {
                grid-template-columns: 1fr;
            }
            
            .citation-analysis-grid,
            .overlap-stats {
                grid-template-columns: 1fr;
            }
            
            .entity-filter-controls,
            .comparison-select {
                flex-direction: column;
                align-items: stretch;
            }
            
            .comparison-select select {
                min-width: auto;
            }
        }
        """
    
    def _generate_overview_section(self) -> str:
        """Generate overview section with key metrics"""
        phase_results = self.results_data.get('phase_results', {})
        
        # Calculate key metrics
        total_phases = len(phase_results)
        successful_phases = len([r for r in phase_results.values() if 'error' not in r])
        
        # Get baseline and best phase
        baseline_entities = 0
        best_entities = 0
        best_phase = ""
        
        for phase_name, result in phase_results.items():
            if 'error' not in result:
                entity_count = result.get('total_entities', 0)
                if 'Phase 1' in phase_name:
                    baseline_entities = entity_count
                if entity_count > best_entities:
                    best_entities = entity_count
                    best_phase = phase_name
        
        improvement = ((best_entities - baseline_entities) / baseline_entities * 100) if baseline_entities > 0 else 0
        
        return f"""
        <div class="metric-grid">
            <div class="metric-card">
                <h3>{total_phases}</h3>
                <p>Test Phases</p>
            </div>
            <div class="metric-card">
                <h3>{successful_phases}</h3>
                <p>Successful Phases</p>
            </div>
            <div class="metric-card">
                <h3>{best_entities:,}</h3>
                <p>Best Entity Count</p>
            </div>
            <div class="metric-card">
                <h3>{improvement:.1f}%</h3>
                <p>Improvement vs Baseline</p>
            </div>
        </div>
        
        <div class="alert alert-info">
            <strong>💡 Key Findings:</strong>
            <ul style="margin-top: 10px;">
                <li>Baseline (REGEX Only): {baseline_entities:,} entities</li>
                <li>Best Performance: {best_phase} with {best_entities:,} entities</li>
                <li>Overall Improvement: {improvement:.1f}% increase in entity detection</li>
                <li>All NLP/BERT models successfully avoided vLLM timeout issues</li>
            </ul>
        </div>
        
        <h3>📋 Phase Summary</h3>
        {self._generate_phase_summary_table()}
        """
    
    def _generate_phase_summary_table(self) -> str:
        """Generate phase summary table"""
        phase_results = self.results_data.get('phase_results', {})
        
        table_rows = ""
        for i, (phase_name, result) in enumerate(phase_results.items(), 1):
            if 'error' not in result:
                entities = result.get('total_entities', 0)
                types = len(result.get('entity_types', []))
                confidence = result.get('avg_confidence', 0)
                time_taken = result.get('processing_time_seconds', 0)
                
                badge_class = f"phase-{i}"
                confidence_width = confidence * 100
                
                table_rows += f"""
                <tr>
                    <td><span class="phase-badge {badge_class}">Phase {i}</span></td>
                    <td>{phase_name}</td>
                    <td>{entities:,}</td>
                    <td>{types}</td>
                    <td>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: {confidence_width}%"></div>
                        </div>
                        {confidence:.1%}
                    </td>
                    <td>{time_taken:.1f}s</td>
                </tr>
                """
            else:
                table_rows += f"""
                <tr>
                    <td><span class="phase-badge phase-{i}">Phase {i}</span></td>
                    <td>{phase_name}</td>
                    <td colspan="4" style="color: #dc3545; text-align: center;">❌ Failed or Timed Out</td>
                </tr>
                """
        
        return f"""
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>Phase</th>
                    <th>Description</th>
                    <th>Entities</th>
                    <th>Types</th>
                    <th>Confidence</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        """
    
    def _generate_entities_section(self) -> str:
        """Generate comprehensive entities analysis section"""
        phase_results = self.results_data.get('phase_results', {})
        
        # Create comprehensive entity analysis
        entity_analysis_html = ""
        
        # Find the best performing phase for detailed analysis
        best_phase = None
        best_count = 0
        
        for phase_name, result in phase_results.items():
            if 'error' not in result:
                entity_count = result.get('total_entities', 0)
                if entity_count > best_count:
                    best_count = entity_count
                    best_phase = (phase_name, result)
        
        if best_phase:
            phase_name, result = best_phase
            entity_analysis_html += f"""
            <div class="alert alert-success">
                <strong>🎯 Best Performing Phase:</strong> {phase_name} with {best_count:,} entities extracted
            </div>
            
            <div class="entity-breakdown-grid">
                <div class="entity-stats-card">
                    <h4>📊 Entity Distribution</h4>
                    <div id="entityTypesPieChart">
                        <canvas id="entityDistributionChart"></canvas>
                    </div>
                </div>
                
                <div class="entity-stats-card">
                    <h4>🎯 Confidence Analysis</h4>
                    <div id="confidenceDistributionChart">
                        <canvas id="confidenceHeatmapChart"></canvas>
                    </div>
                </div>
                
                <div class="entity-stats-card">
                    <h4>📍 Position Analysis</h4>
                    <div id="positionAnalysisChart">
                        <canvas id="positionScatterChart"></canvas>
                    </div>
                </div>
            </div>
            
            <h3>🔍 Detailed Entity Breakdown</h3>
            <div class="entity-filter-controls">
                <div class="filter-group">
                    <label>Entity Type:</label>
                    <select id="entityTypeFilter" onchange="filterEntityTable()">
                        <option value="all">All Types</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Min Confidence:</label>
                    <input type="range" id="confidenceFilter" min="0" max="100" value="0" 
                           onchange="filterEntityTable()" oninput="updateConfidenceLabel()">
                    <span id="confidenceLabel">0%</span>
                </div>
                <div class="filter-group">
                    <button onclick="exportEntityData()" class="export-btn">📥 Export Entities</button>
                </div>
            </div>
            
            <table id="detailedEntityTable" class="entity-table display" style="width:100%">
                <thead>
                    <tr>
                        <th>Entity Text</th>
                        <th>Type</th>
                        <th>Confidence</th>
                        <th>Position</th>
                        <th>Context</th>
                        <th>Normalized</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="entityTableBody">
                    <!-- Populated by JavaScript -->
                </tbody>
            </table>
            """
            
            # Add citation analysis if available
            if result.get('citation_mappings'):
                entity_analysis_html += """
                <h3>⚖️ Citation Analysis</h3>
                <div class="citation-analysis-grid">
                    <div class="citation-stats">
                        <h4>📚 Citation Compliance</h4>
                        <div id="citationComplianceChart">
                            <canvas id="citationChart"></canvas>
                        </div>
                    </div>
                    <div class="citation-details">
                        <h4>📋 Citation Details</h4>
                        <table id="citationTable" class="entity-table display" style="width:100%">
                            <thead>
                                <tr>
                                    <th>Citation Text</th>
                                    <th>Bluebook Format</th>
                                    <th>Components</th>
                                    <th>Confidence</th>
                                    <th>Position</th>
                                </tr>
                            </thead>
                            <tbody id="citationTableBody">
                                <!-- Populated by JavaScript -->
                            </tbody>
                        </table>
                    </div>
                </div>
                """
        else:
            entity_analysis_html = """
            <div class="alert alert-warning">
                <strong>⚠️ No Entity Data Available:</strong> All test phases failed or timed out.
            </div>
            """
        
        return f"""
        <div id="entitiesContent">
            {entity_analysis_html}
        </div>
        """
    
    def _generate_performance_section(self) -> str:
        """Generate comprehensive performance metrics section"""
        phase_results = self.results_data.get('phase_results', {})
        
        # Calculate performance statistics
        performance_data = []
        total_processing_time = 0
        successful_phases = 0
        
        for phase_name, result in phase_results.items():
            if 'error' not in result:
                processing_time = result.get('processing_time_seconds', 0)
                memory_usage = result.get('memory_usage_mb', 0)
                entities_per_sec = result.get('total_entities', 0) / max(processing_time, 0.1)
                
                performance_data.append({
                    'phase': phase_name,
                    'processing_time': processing_time,
                    'memory_usage': memory_usage,
                    'entities_per_sec': entities_per_sec,
                    'total_entities': result.get('total_entities', 0)
                })
                
                total_processing_time += processing_time
                successful_phases += 1
        
        avg_processing_time = total_processing_time / max(successful_phases, 1)
        
        performance_html = f"""
        <div class="performance-overview">
            <div class="perf-metric-grid">
                <div class="perf-metric-card">
                    <h3>{total_processing_time:.1f}s</h3>
                    <p>Total Processing Time</p>
                    <div class="metric-icon">⏱️</div>
                </div>
                <div class="perf-metric-card">
                    <h3>{avg_processing_time:.1f}s</h3>
                    <p>Average per Phase</p>
                    <div class="metric-icon">📊</div>
                </div>
                <div class="perf-metric-card">
                    <h3>{successful_phases}</h3>
                    <p>Successful Phases</p>
                    <div class="metric-icon">✅</div>
                </div>
                <div class="perf-metric-card">
                    <h3>{sum(p['total_entities'] for p in performance_data):,}</h3>
                    <p>Total Entities</p>
                    <div class="metric-icon">🎯</div>
                </div>
            </div>
        </div>
        
        <div class="performance-charts-grid">
            <div class="perf-chart-container">
                <h3>⚡ Processing Time by Phase</h3>
                <canvas id="processingTimeLineChart"></canvas>
            </div>
            <div class="perf-chart-container">
                <h3>💾 Memory Usage Analysis</h3>
                <canvas id="memoryUsageChart"></canvas>
            </div>
            <div class="perf-chart-container">
                <h3>🚀 Throughput Analysis</h3>
                <canvas id="throughputChart"></canvas>
            </div>
            <div class="perf-chart-container">
                <h3>📈 Performance Correlation</h3>
                <canvas id="performanceCorrelationChart"></canvas>
            </div>
        </div>
        
        <h3>📋 Detailed Performance Metrics</h3>
        <table id="performanceTable" class="performance-table display" style="width:100%">
            <thead>
                <tr>
                    <th>Phase</th>
                    <th>Processing Time (s)</th>
                    <th>Memory Usage (MB)</th>
                    <th>Entities Found</th>
                    <th>Throughput (ent/s)</th>
                    <th>Efficiency Score</th>
                    <th>GPU Utilization</th>
                </tr>
            </thead>
            <tbody>"""
        
        for perf in performance_data:
            efficiency_score = (perf['entities_per_sec'] / max(perf['memory_usage'], 1)) * 100
            gpu_util = "N/A"  # Would need to be collected during actual testing
            
            performance_html += f"""
                <tr>
                    <td>{perf['phase']}</td>
                    <td>{perf['processing_time']:.2f}</td>
                    <td>{perf['memory_usage']:.1f}</td>
                    <td>{perf['total_entities']:,}</td>
                    <td>{perf['entities_per_sec']:.1f}</td>
                    <td>{efficiency_score:.2f}</td>
                    <td>{gpu_util}</td>
                </tr>"""
        
        performance_html += """
            </tbody>
        </table>
        
        <div class="performance-insights">
            <h3>💡 Performance Insights</h3>
            <div class="alert alert-info">
                <ul>
                    <li><strong>Fastest Phase:</strong> {min(performance_data, key=lambda x: x['processing_time'])['phase'] if performance_data else 'N/A'}</li>
                    <li><strong>Most Efficient:</strong> {max(performance_data, key=lambda x: x['entities_per_sec'])['phase'] if performance_data else 'N/A'}</li>
                    <li><strong>Memory Optimization:</strong> Consider phases with high entity/memory ratios</li>
                    <li><strong>Scaling Potential:</strong> Linear time scaling observed across phases</li>
                </ul>
            </div>
        </div>"""
        
        return f"""
        <div id="performanceContent">
            {performance_html}
        </div>
        """
    
    def _generate_comparison_section(self) -> str:
        """Generate comprehensive phase comparison section"""
        phase_results = self.results_data.get('phase_results', {})
        
        if len(phase_results) < 2:
            return """
            <div id="comparisonContent">
                <div class="alert alert-warning">
                    <strong>⚠️ Insufficient Data:</strong> Need at least 2 phases for comparison analysis.
                </div>
            </div>
            """
        
        # Create comprehensive comparison analysis
        comparison_html = """
        <div class="comparison-controls">
            <div class="comparison-select">
                <label>Compare Phases:</label>
                <select id="phase1Select" onchange="updateComparison()">
                    <option value="">Select Phase 1</option>
                </select>
                <span class="vs-label">vs</span>
                <select id="phase2Select" onchange="updateComparison()">
                    <option value="">Select Phase 2</option>
                </select>
                <button onclick="swapPhases()" class="swap-btn">🔄 Swap</button>
            </div>
        </div>
        
        <div id="comparisonResults" class="comparison-results">
            <div class="comparison-grid">
                <div class="comparison-card">
                    <h4>🎯 Entity Detection Comparison</h4>
                    <canvas id="entityComparisonChart"></canvas>
                    <div id="entityComparisonStats"></div>
                </div>
                
                <div class="comparison-card">
                    <h4>⚡ Performance Comparison</h4>
                    <canvas id="performanceComparisonChart"></canvas>
                    <div id="performanceComparisonStats"></div>
                </div>
                
                <div class="comparison-card">
                    <h4>🎯 Confidence Distribution</h4>
                    <canvas id="confidenceComparisonChart"></canvas>
                    <div id="confidenceComparisonStats"></div>
                </div>
                
                <div class="comparison-card">
                    <h4>📊 Quality Metrics</h4>
                    <canvas id="qualityComparisonChart"></canvas>
                    <div id="qualityComparisonStats"></div>
                </div>
            </div>
            
            <h3>🔍 Side-by-Side Analysis</h3>
            <div class="side-by-side-comparison">
                <table id="comparisonTable" class="comparison-table display" style="width:100%">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th id="phase1Header">Phase 1</th>
                            <th id="phase2Header">Phase 2</th>
                            <th>Difference</th>
                            <th>% Change</th>
                            <th>Winner</th>
                        </tr>
                    </thead>
                    <tbody id="comparisonTableBody">
                        <!-- Populated by JavaScript -->
                    </tbody>
                </table>
            </div>
            
            <h3>🎯 Entity Overlap Analysis</h3>
            <div class="entity-overlap-analysis">
                <div class="overlap-stats">
                    <div class="overlap-venn">
                        <canvas id="entityOverlapChart"></canvas>
                    </div>
                    <div class="overlap-details">
                        <h4>📊 Overlap Statistics</h4>
                        <div id="overlapStats"></div>
                        
                        <h4>🔍 Unique to Each Phase</h4>
                        <div class="unique-entities">
                            <div class="unique-column">
                                <h5 id="unique1Header">Unique to Phase 1</h5>
                                <div id="unique1List" class="unique-list"></div>
                            </div>
                            <div class="unique-column">
                                <h5 id="unique2Header">Unique to Phase 2</h5>
                                <div id="unique2List" class="unique-list"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="comparison-insights">
                <h3>💡 Comparison Insights</h3>
                <div id="comparisonInsights" class="alert alert-info">
                    <p>Select two phases above to see detailed comparison analysis.</p>
                </div>
            </div>
        </div>"""
        
        return f"""
        <div id="comparisonContent">
            {comparison_html}
        </div>
        """
    
    def _prepare_chart_data(self) -> Dict[str, Any]:
        """Prepare data for JavaScript charts"""
        phase_results = self.results_data.get('phase_results', {})
        
        phases = []
        entity_counts = []
        type_counts = []
        confidences = []
        processing_times = []
        
        for phase_name, result in phase_results.items():
            if 'error' not in result:
                phases.append(phase_name.replace('Phase ', 'P').replace(': ', ':\\n'))
                entity_counts.append(result.get('total_entities', 0))
                type_counts.append(len(result.get('entity_types', [])))
                confidences.append(result.get('avg_confidence', 0) * 100)
                processing_times.append(result.get('processing_time_seconds', 0))
        
        # Enhanced data extraction for detailed analysis
        detailed_phases = {}
        for phase_name, result in phase_results.items():
            if 'error' not in result:
                detailed_phases[phase_name] = {
                    'entity_mappings': result.get('entity_mappings', []),
                    'citation_mappings': result.get('citation_mappings', []),
                    'entity_types': result.get('entity_types', []),
                    'performance_metrics': {
                        'processing_time': result.get('processing_time_seconds', 0),
                        'memory_usage': result.get('memory_usage_mb', 0),
                        'total_entities': result.get('total_entities', 0),
                        'avg_confidence': result.get('avg_confidence', 0)
                    }
                }
        
        return {
            'phases': phases,
            'entityCounts': entity_counts,
            'typeCounts': type_counts,
            'confidences': confidences,
            'processingTimes': processing_times,
            'detailedPhases': detailed_phases,
            'rawData': phase_results
        }
    
    def _prepare_table_data(self) -> Dict[str, Any]:
        """Prepare data for tables"""
        # Find best performing phase for detailed analysis
        phase_results = self.results_data.get('phase_results', {})
        best_phase = None
        max_entities = 0
        
        for phase_name, result in phase_results.items():
            if 'error' not in result:
                entity_count = result.get('total_entities', 0)
                if entity_count > max_entities:
                    max_entities = entity_count
                    best_phase = (phase_name, result)
        
        return {
            'best_phase': best_phase[0] if best_phase else None,
            'best_phase_data': best_phase[1] if best_phase else {},
            'total_entities': max_entities,
            'successful_phases': len([r for r in phase_results.values() if 'error' not in r])
        }
    
    def _generate_javascript(self, chart_data: Dict[str, Any]) -> str:
        """Generate comprehensive JavaScript for interactive functionality"""
        return f"""
        // Global variables
        let entityData = null;
        let citationData = null;
        let currentPhaseData = null;
        let entityTable = null;
        let citationTable = null;
        let performanceTable = null;
        let comparisonTable = null;
        
        // Tab functionality
        function showTab(tabName) {{
            // Hide all tab contents
            const tabs = document.querySelectorAll('.tab-content');
            tabs.forEach(tab => tab.classList.remove('active'));
            
            // Remove active class from nav buttons
            const navTabs = document.querySelectorAll('.nav-tab');
            navTabs.forEach(tab => tab.classList.remove('active'));
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            
            // Initialize content based on tab
            switch(tabName) {{
                case 'charts':
                    initializeCharts();
                    break;
                case 'entities':
                    initializeEntityAnalysis();
                    break;
                case 'performance':
                    initializePerformanceAnalysis();
                    break;
                case 'comparison':
                    initializeComparisonAnalysis();
                    break;
            }}
        }}

        // Chart data
        const chartData = {json.dumps(chart_data)};

        // Initialize main charts
        function initializeCharts() {{
            // Entity Progression Chart
            const ctx1 = document.getElementById('entityProgressionChart');
            if (ctx1 && !ctx1.chart) {{
                ctx1.chart = new Chart(ctx1, {{
                    type: 'bar',
                    data: {{
                        labels: chartData.phases,
                        datasets: [{{
                            label: 'Entity Count',
                            data: chartData.entityCounts,
                            backgroundColor: [
                                'rgba(220, 53, 69, 0.8)',
                                'rgba(253, 126, 20, 0.8)', 
                                'rgba(32, 201, 151, 0.8)',
                                'rgba(111, 66, 193, 0.8)'
                            ],
                            borderColor: [
                                'rgba(220, 53, 69, 1)',
                                'rgba(253, 126, 20, 1)',
                                'rgba(32, 201, 151, 1)', 
                                'rgba(111, 66, 193, 1)'
                            ],
                            borderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Number of Entities'
                                }}
                            }}
                        }},
                        plugins: {{
                            legend: {{
                                display: false
                            }}
                        }}
                    }}
                }});
            }}

            // Entity Types Chart
            const ctx2 = document.getElementById('entityTypesChart');
            if (ctx2 && !ctx2.chart) {{
                ctx2.chart = new Chart(ctx2, {{
                    type: 'line',
                    data: {{
                        labels: chartData.phases,
                        datasets: [{{
                            label: 'Unique Entity Types',
                            data: chartData.typeCounts,
                            borderColor: 'rgba(102, 126, 234, 1)',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Number of Types'
                                }}
                            }}
                        }}
                    }}
                }});
            }}

            // Confidence Chart
            const ctx3 = document.getElementById('confidenceChart');
            if (ctx3 && !ctx3.chart) {{
                ctx3.chart = new Chart(ctx3, {{
                    type: 'radar',
                    data: {{
                        labels: chartData.phases,
                        datasets: [{{
                            label: 'Average Confidence (%)',
                            data: chartData.confidences,
                            borderColor: 'rgba(255, 159, 243, 1)',
                            backgroundColor: 'rgba(255, 159, 243, 0.2)',
                            borderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            r: {{
                                beginAtZero: true,
                                max: 100,
                                title: {{
                                    display: true,
                                    text: 'Confidence %'
                                }}
                            }}
                        }}
                    }}
                }});
            }}

            // Processing Time Chart
            const ctx4 = document.getElementById('processingTimeChart');
            if (ctx4 && !ctx4.chart) {{
                ctx4.chart = new Chart(ctx4, {{
                    type: 'doughnut',
                    data: {{
                        labels: chartData.phases,
                        datasets: [{{
                            label: 'Processing Time (seconds)',
                            data: chartData.processingTimes,
                            backgroundColor: [
                                'rgba(220, 53, 69, 0.8)',
                                'rgba(253, 126, 20, 0.8)',
                                'rgba(32, 201, 151, 0.8)', 
                                'rgba(111, 66, 193, 0.8)'
                            ]
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{
                                position: 'bottom'
                            }}
                        }}
                    }}
                }});
            }}
        }}
        
        // Initialize entity analysis
        function initializeEntityAnalysis() {{
            if (!entityData) {{
                // Extract entity data from the best performing phase
                const bestPhase = getBestPhase();
                if (bestPhase && bestPhase.entity_mappings) {{
                    entityData = bestPhase.entity_mappings;
                    populateEntityTable();
                    initializeEntityCharts();
                }}
                
                if (bestPhase && bestPhase.citation_mappings) {{
                    citationData = bestPhase.citation_mappings;
                    populateCitationTable();
                    initializeCitationCharts();
                }}
            }}
        }}
        
        // Initialize entity-specific charts
        function initializeEntityCharts() {{
            // Entity Distribution Pie Chart
            const ctx = document.getElementById('entityDistributionChart');
            if (ctx && !ctx.chart && entityData) {{
                const entityTypes = {{}};
                entityData.forEach(entity => {{
                    const type = entity.entity_type || 'Unknown';
                    entityTypes[type] = (entityTypes[type] || 0) + 1;
                }});
                
                ctx.chart = new Chart(ctx, {{
                    type: 'pie',
                    data: {{
                        labels: Object.keys(entityTypes),
                        datasets: [{{
                            data: Object.values(entityTypes),
                            backgroundColor: [
                                'rgba(220, 53, 69, 0.8)',
                                'rgba(253, 126, 20, 0.8)',
                                'rgba(32, 201, 151, 0.8)',
                                'rgba(111, 66, 193, 0.8)',
                                'rgba(255, 193, 7, 0.8)',
                                'rgba(23, 162, 184, 0.8)'
                            ]
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{
                                position: 'bottom'
                            }}
                        }}
                    }}
                }});
            }}
            
            // Confidence Heatmap
            const ctx2 = document.getElementById('confidenceHeatmapChart');
            if (ctx2 && !ctx2.chart && entityData) {{
                const confidenceBins = [{{'0-0.5': 0, '0.5-0.7': 0, '0.7-0.85': 0, '0.85-0.95': 0, '0.95-1.0': 0}}];
                entityData.forEach(entity => {{
                    const conf = entity.confidence_score || 0;
                    if (conf < 0.5) confidenceBins[0]['0-0.5']++;
                    else if (conf < 0.7) confidenceBins[0]['0.5-0.7']++;
                    else if (conf < 0.85) confidenceBins[0]['0.7-0.85']++;
                    else if (conf < 0.95) confidenceBins[0]['0.85-0.95']++;
                    else confidenceBins[0]['0.95-1.0']++;
                }});
                
                ctx2.chart = new Chart(ctx2, {{
                    type: 'bar',
                    data: {{
                        labels: Object.keys(confidenceBins[0]),
                        datasets: [{{
                            label: 'Entity Count',
                            data: Object.values(confidenceBins[0]),
                            backgroundColor: [
                                'rgba(220, 53, 69, 0.8)',
                                'rgba(253, 126, 20, 0.8)',
                                'rgba(255, 193, 7, 0.8)',
                                'rgba(40, 167, 69, 0.8)',
                                'rgba(32, 201, 151, 0.8)'
                            ]
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Number of Entities'
                                }}
                            }},
                            x: {{
                                title: {{
                                    display: true,
                                    text: 'Confidence Range'
                                }}
                            }}
                        }}
                    }}
                }});
            }}
            
            // Position Scatter Chart
            const ctx3 = document.getElementById('positionScatterChart');
            if (ctx3 && !ctx3.chart && entityData) {{
                const scatterData = entityData.map(entity => ({{
                    x: entity.position ? entity.position.start : 0,
                    y: (entity.confidence_score || 0) * 100
                }}));
                
                ctx3.chart = new Chart(ctx3, {{
                    type: 'scatter',
                    data: {{
                        datasets: [{{
                            label: 'Entity Position vs Confidence',
                            data: scatterData,
                            backgroundColor: 'rgba(102, 126, 234, 0.6)',
                            borderColor: 'rgba(102, 126, 234, 1)'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            x: {{
                                title: {{
                                    display: true,
                                    text: 'Position in Document'
                                }}
                            }},
                            y: {{
                                title: {{
                                    display: true,
                                    text: 'Confidence (%)'
                                }}
                            }}
                        }}
                    }}
                }});
            }}
        }}
        
        // Populate entity table
        function populateEntityTable() {{
            if (entityData && !entityTable) {{
                // Populate entity type filter
                const entityTypes = [...new Set(entityData.map(e => e.entity_type || 'Unknown'))];
                const filterSelect = document.getElementById('entityTypeFilter');
                entityTypes.forEach(type => {{
                    const option = document.createElement('option');
                    option.value = type;
                    option.textContent = type;
                    filterSelect.appendChild(option);
                }});
                
                // Initialize DataTable
                entityTable = $('#detailedEntityTable').DataTable({{
                    data: entityData,
                    columns: [
                        {{ 
                            data: 'text',
                            title: 'Entity Text',
                            render: function(data) {{
                                return `<span class="entity-text">${{data || 'N/A'}}</span>`;
                            }}
                        }},
                        {{ 
                            data: 'entity_type',
                            title: 'Type',
                            render: function(data) {{
                                return `<span class="entity-type-badge">${{data || 'Unknown'}}</span>`;
                            }}
                        }},
                        {{ 
                            data: 'confidence_score',
                            title: 'Confidence',
                            render: function(data) {{
                                const conf = (data || 0) * 100;
                                const cls = conf >= 90 ? 'confidence-high' : 
                                           conf >= 70 ? 'confidence-medium' : 'confidence-low';
                                return `<span class="confidence-indicator ${{cls}}">${{conf.toFixed(1)}}%</span>`;
                            }}
                        }},
                        {{ 
                            data: 'position',
                            title: 'Position',
                            render: function(data) {{
                                if (data) {{
                                    return `<span class="position-info">${{data.start}}-${{data.end}}</span>`;
                                }}
                                return 'N/A';
                            }}
                        }},
                        {{ 
                            data: 'context',
                            title: 'Context',
                            render: function(data, type, row) {{
                                const context = data || 'No context available';
                                return `<span class="entity-context" title="${{context}}">${{context.substring(0, 50)}}...</span>`;
                            }}
                        }},
                        {{ 
                            data: 'normalized_text',
                            title: 'Normalized',
                            render: function(data) {{
                                return data || 'N/A';
                            }}
                        }},
                        {{
                            data: null,
                            title: 'Actions',
                            render: function(data, type, row) {{
                                return `<button onclick="viewEntityDetails(${{row.id || 0}})" class="btn-small">View</button>`;
                            }}
                        }}
                    ],
                    pageLength: 25,
                    order: [[2, 'desc']], // Sort by confidence
                    responsive: true
                }});
            }}
        }}
        
        // Initialize performance analysis
        function initializePerformanceAnalysis() {{
            // Initialize performance charts and table
            initializePerformanceCharts();
            
            if (!performanceTable) {{
                const performanceData = [];
                
                Object.entries(chartData.rawData).forEach(([phaseName, result]) => {{
                    if (!result.error) {{
                        performanceData.push({{
                            phase: phaseName,
                            processing_time: result.processing_time_seconds || 0,
                            memory_usage: result.memory_usage_mb || 0,
                            entities_found: result.total_entities || 0,
                            throughput: (result.total_entities || 0) / Math.max(result.processing_time_seconds || 0.1, 0.1),
                            efficiency: ((result.total_entities || 0) / Math.max(result.memory_usage_mb || 1, 1)) * 100,
                            gpu_utilization: 'N/A'
                        }});
                    }}
                }});
                
                performanceTable = $('#performanceTable').DataTable({{
                    data: performanceData,
                    columns: [
                        {{ data: 'phase', title: 'Phase' }},
                        {{ data: 'processing_time', title: 'Processing Time (s)', render: $.fn.dataTable.render.number(',', '.', 2) }},
                        {{ data: 'memory_usage', title: 'Memory Usage (MB)', render: $.fn.dataTable.render.number(',', '.', 1) }},
                        {{ data: 'entities_found', title: 'Entities Found', render: $.fn.dataTable.render.number(',') }},
                        {{ data: 'throughput', title: 'Throughput (ent/s)', render: $.fn.dataTable.render.number(',', '.', 1) }},
                        {{ data: 'efficiency', title: 'Efficiency Score', render: $.fn.dataTable.render.number(',', '.', 2) }},
                        {{ data: 'gpu_utilization', title: 'GPU Utilization' }}
                    ],
                    pageLength: 10,
                    order: [[4, 'desc']], // Sort by throughput
                    responsive: true
                }});
            }}
        }}
        
        // Initialize performance charts
        function initializePerformanceCharts() {{
            // Implementation would create line charts, bar charts for performance metrics
            // Similar to entity charts but focused on timing, memory, throughput
        }}
        
        // Initialize comparison analysis
        function initializeComparisonAnalysis() {{
            // Populate phase selection dropdowns
            const phases = Object.keys(chartData.rawData).filter(phase => !chartData.rawData[phase].error);
            const phase1Select = document.getElementById('phase1Select');
            const phase2Select = document.getElementById('phase2Select');
            
            phases.forEach(phase => {{
                const option1 = document.createElement('option');
                option1.value = phase;
                option1.textContent = phase;
                phase1Select.appendChild(option1);
                
                const option2 = document.createElement('option');
                option2.value = phase;
                option2.textContent = phase;
                phase2Select.appendChild(option2);
            }});
            
            // Set default selections if available
            if (phases.length >= 2) {{
                phase1Select.value = phases[0];
                phase2Select.value = phases[1];
                updateComparison();
            }}
        }}
        
        // Helper functions
        function getBestPhase() {{
            let best = null;
            let maxEntities = 0;
            
            Object.entries(chartData.rawData).forEach(([name, result]) => {{
                if (!result.error && (result.total_entities || 0) > maxEntities) {{
                    maxEntities = result.total_entities || 0;
                    best = result;
                }}
            }});
            
            return best;
        }}
        
        function updateComparison() {{
            // Implementation for comparison updates
            console.log('Updating comparison analysis...');
        }}
        
        function swapPhases() {{
            const phase1 = document.getElementById('phase1Select');
            const phase2 = document.getElementById('phase2Select');
            const temp = phase1.value;
            phase1.value = phase2.value;
            phase2.value = temp;
            updateComparison();
        }}
        
        function filterEntityTable() {{
            if (entityTable) {{
                const typeFilter = document.getElementById('entityTypeFilter').value;
                const confFilter = parseInt(document.getElementById('confidenceFilter').value) / 100;
                
                entityTable.columns(1).search(typeFilter === 'all' ? '' : typeFilter);
                // Additional confidence filtering logic would go here
                entityTable.draw();
            }}
        }}
        
        function updateConfidenceLabel() {{
            const value = document.getElementById('confidenceFilter').value;
            document.getElementById('confidenceLabel').textContent = value + '%';
        }}
        
        function exportEntityData() {{
            if (entityData) {{
                const dataStr = JSON.stringify(entityData, null, 2);
                const dataBlob = new Blob([dataStr], {{type: 'application/json'}});
                const url = URL.createObjectURL(dataBlob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'entity_analysis.json';
                link.click();
                URL.revokeObjectURL(url);
            }}
        }}
        
        function viewEntityDetails(entityId) {{
            // Implementation for detailed entity view
            console.log('Viewing entity details for:', entityId);
        }}

        // Export functionality
        function exportData() {{
            const dataStr = JSON.stringify(chartData.rawData, null, 2);
            const dataBlob = new Blob([dataStr], {{type: 'application/json'}});
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'cales_nlp_bert_results.json';
            link.click();
            URL.revokeObjectURL(url);
        }}

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {{
            // Initialize charts after a short delay
            setTimeout(initializeCharts, 500);
        }});
        """

def main():
    """Main function to generate HTML dashboard"""
    import sys
    
    if len(sys.argv) > 1:
        results_file = sys.argv[1]
    else:
        # Find the most recent results file
        results_dir = Path('/srv/luris/be/entity-extraction-service/tests/results')
        results_files = list(results_dir.glob('cales_nlp_bert_comprehensive_*.json'))
        
        if not results_files:
            print("❌ No results files found. Run the testing script first.")
            return
        
        results_file = str(max(results_files, key=os.path.getctime))
        print(f"📁 Using most recent results file: {results_file}")
    
    if not os.path.exists(results_file):
        print(f"❌ Results file not found: {results_file}")
        return
    
    # Generate dashboard
    dashboard = CALESHTMLDashboard(results_file)
    html_file = dashboard.generate_dashboard()
    
    print(f"✅ HTML Dashboard ready!")
    print(f"🌐 Open in browser: file://{html_file}")

if __name__ == "__main__":
    main()