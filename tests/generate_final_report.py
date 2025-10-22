#!/usr/bin/env python3
"""Generate comprehensive HTML validation report for regex patterns."""

import json
from pathlib import Path
from datetime import datetime
import re
from typing import Dict, List, Any

def get_result_status(result):
    """Determine the status of a test result."""
    if result.get('error') is not None:
        return 'error'
    elif len(result.get('failed_examples', [])) > 0:
        return 'failed'
    else:
        return 'passed'

def generate_html_report():
    """Generate comprehensive HTML validation report."""
    
    # Load test results
    results_path = Path("/srv/luris/be/entity-extraction-service/tests/results/pattern_test_results.json")
    with open(results_path, 'r') as f:
        results = json.load(f)
    
    # Load corrections if available
    corrections_path = Path("/srv/luris/be/entity-extraction-service/tests/results/advanced_corrections.json")
    corrections = {}
    if corrections_path.exists():
        with open(corrections_path, 'r') as f:
            corrections_data = json.load(f)
            # Index corrections by pattern name
            if 'corrections' in corrections_data:
                for file_path, file_corrections in corrections_data['corrections'].items():
                    for pattern_name, correction_info in file_corrections.items():
                        corrections[pattern_name] = correction_info
    
    # Calculate statistics
    total_patterns = len(results['results'])
    passed_patterns = sum(1 for r in results['results'] if len(r.get('failed_examples', [])) == 0 and r.get('error') is None)
    failed_patterns = sum(1 for r in results['results'] if len(r.get('failed_examples', [])) > 0)
    error_patterns = sum(1 for r in results['results'] if r.get('error') is not None)
    pass_rate = (passed_patterns / total_patterns * 100) if total_patterns > 0 else 0
    
    # Group results by file
    results_by_file = {}
    for result in results['results']:
        file_path = result['file_path']
        if file_path not in results_by_file:
            results_by_file[file_path] = []
        results_by_file[file_path].append(result)
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Regex Pattern Validation Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            color: #2d3748;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .timestamp {{
            color: #718096;
            font-size: 0.9em;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        .pass-rate {{
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        }}
        
        .failed {{
            background: linear-gradient(135deg, #f56565 0%, #e53e3e 100%);
        }}
        
        .file-section {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }}
        
        .file-header {{
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        
        .file-name {{
            color: #4a5568;
            font-size: 1.3em;
            font-weight: 600;
        }}
        
        .file-stats {{
            display: inline-block;
            margin-left: 20px;
            font-size: 0.9em;
            color: #718096;
        }}
        
        .pattern-card {{
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.3s;
        }}
        
        .pattern-card:hover {{
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }}
        
        .pattern-card.passed {{
            border-left: 4px solid #48bb78;
        }}
        
        .pattern-card.failed {{
            border-left: 4px solid #f56565;
        }}
        
        .pattern-card.corrected {{
            border-left: 4px solid #4299e1;
            background: #ebf8ff;
        }}
        
        .pattern-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .pattern-name {{
            font-size: 1.1em;
            font-weight: 600;
            color: #2d3748;
        }}
        
        .status-badge {{
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .status-badge.passed {{
            background: #c6f6d5;
            color: #22543d;
        }}
        
        .status-badge.failed {{
            background: #fed7d7;
            color: #742a2a;
        }}
        
        .status-badge.corrected {{
            background: #bee3f8;
            color: #2c5282;
        }}
        
        .pattern-regex {{
            background: #f7fafc;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        
        .examples-section {{
            margin-top: 20px;
        }}
        
        .examples-header {{
            font-weight: 600;
            color: #4a5568;
            margin-bottom: 10px;
        }}
        
        .example-item {{
            display: flex;
            align-items: center;
            padding: 10px;
            background: #f7fafc;
            border-radius: 5px;
            margin-bottom: 8px;
        }}
        
        .example-status {{
            width: 24px;
            height: 24px;
            margin-right: 12px;
            flex-shrink: 0;
        }}
        
        .example-text {{
            flex: 1;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        
        .extracted-value {{
            margin-left: 10px;
            padding: 3px 8px;
            background: #e6fffa;
            color: #234e52;
            border-radius: 4px;
            font-size: 0.85em;
        }}
        
        .correction-section {{
            margin-top: 20px;
            padding: 15px;
            background: #ebf8ff;
            border-radius: 8px;
            border: 1px solid #90cdf4;
        }}
        
        .correction-header {{
            font-weight: 600;
            color: #2c5282;
            margin-bottom: 10px;
        }}
        
        .navigation {{
            position: fixed;
            right: 20px;
            top: 100px;
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            max-height: 70vh;
            overflow-y: auto;
            width: 250px;
        }}
        
        .nav-header {{
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 15px;
        }}
        
        .nav-item {{
            padding: 8px 12px;
            margin-bottom: 5px;
            border-radius: 5px;
            cursor: pointer;
            transition: background 0.2s;
            font-size: 0.9em;
        }}
        
        .nav-item:hover {{
            background: #f7fafc;
        }}
        
        .nav-stats {{
            font-size: 0.8em;
            color: #718096;
            margin-left: 5px;
        }}
        
        @media (max-width: 1200px) {{
            .navigation {{
                display: none;
            }}
        }}
        
        .filter-section {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }}
        
        .filter-buttons {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            padding: 8px 16px;
            border: 2px solid #e2e8f0;
            background: white;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.9em;
        }}
        
        .filter-btn:hover {{
            background: #f7fafc;
        }}
        
        .filter-btn.active {{
            background: #667eea;
            color: white;
            border-color: #667eea;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Regex Pattern Validation Report</h1>
            <div class="timestamp">Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
            
            <div class="summary">
                <div class="stat-card">
                    <div class="stat-value">{total_patterns}</div>
                    <div class="stat-label">Total Patterns</div>
                </div>
                <div class="stat-card pass-rate">
                    <div class="stat-value">{pass_rate:.1f}%</div>
                    <div class="stat-label">Pass Rate</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);">
                    <div class="stat-value">{passed_patterns}</div>
                    <div class="stat-label">Passed</div>
                </div>
                <div class="stat-card failed">
                    <div class="stat-value">{failed_patterns}</div>
                    <div class="stat-label">Failed</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);">
                    <div class="stat-value">{len(corrections)}</div>
                    <div class="stat-label">Corrected</div>
                </div>
            </div>
        </div>
        
        <div class="filter-section">
            <div class="filter-buttons">
                <button class="filter-btn active" onclick="filterPatterns('all')">All Patterns</button>
                <button class="filter-btn" onclick="filterPatterns('passed')">✅ Passed Only</button>
                <button class="filter-btn" onclick="filterPatterns('failed')">❌ Failed Only</button>
                <button class="filter-btn" onclick="filterPatterns('corrected')">🔧 Corrected</button>
            </div>
        </div>
"""
    
    # Add navigation
    html += """
        <div class="navigation">
            <div class="nav-header">Quick Navigation</div>
"""
    
    for file_path in sorted(results_by_file.keys()):
        file_results = results_by_file[file_path]
        file_passed = sum(1 for r in file_results if get_result_status(r) == 'passed')
        file_failed = sum(1 for r in file_results if get_result_status(r) == 'failed')
        file_name = Path(file_path).name
        
        html += f"""
            <div class="nav-item" onclick="scrollToFile('{file_name.replace('.yaml', '')}')">
                {file_name}
                <span class="nav-stats">({file_passed}✓ {file_failed}✗)</span>
            </div>
"""
    
    html += "</div>"
    
    # Add pattern details by file
    for file_path in sorted(results_by_file.keys()):
        file_results = results_by_file[file_path]
        file_passed = sum(1 for r in file_results if get_result_status(r) == 'passed')
        file_failed = sum(1 for r in file_results if get_result_status(r) == 'failed')
        file_name = Path(file_path).name
        
        html += f"""
        <div class="file-section" id="{file_name.replace('.yaml', '')}">
            <div class="file-header">
                <span class="file-name">📁 {file_name}</span>
                <span class="file-stats">
                    {len(file_results)} patterns | 
                    <span style="color: #48bb78;">✅ {file_passed} passed</span> | 
                    <span style="color: #f56565;">❌ {file_failed} failed</span>
                </span>
            </div>
"""
        
        for result in file_results:
            pattern_name = result['pattern_name']
            status = get_result_status(result)
            was_corrected = pattern_name in corrections
            
            card_class = "corrected" if was_corrected else status
            badge_class = "corrected" if was_corrected else status
            badge_text = "CORRECTED" if was_corrected else status.upper()
            
            html += f"""
            <div class="pattern-card {card_class}" data-status="{status}" data-corrected="{str(was_corrected).lower()}">
                <div class="pattern-header">
                    <div class="pattern-name">{pattern_name}</div>
                    <div class="status-badge {badge_class}">{badge_text}</div>
                </div>
"""
            
            # Show pattern regex
            pattern_str = result.get('pattern', 'N/A')
            if pattern_str and pattern_str != 'N/A':
                html += f"""
                <div class="pattern-regex">{html_escape(pattern_str[:500])}{'...' if len(pattern_str) > 500 else ''}</div>
"""
            
            # Show examples and test results
            if 'examples' in result and result['examples']:
                html += """
                <div class="examples-section">
                    <div class="examples-header">Examples & Test Results:</div>
"""
                
                for i, example in enumerate(result['examples']):
                    # Determine if this example passed
                    example_passed = True
                    if 'failed_examples' in result:
                        example_passed = example not in result['failed_examples']
                    
                    icon = "✅" if example_passed else "❌"
                    
                    html += f"""
                    <div class="example-item">
                        <span class="example-status">{icon}</span>
                        <span class="example-text">{html_escape(str(example))}</span>
"""
                    
                    # Show extracted value if available
                    if 'extracted_values' in result and i < len(result['extracted_values']):
                        extracted = result['extracted_values'][i]
                        if extracted:
                            html += f"""<span class="extracted-value">→ {html_escape(str(extracted))}</span>"""
                    
                    html += "</div>"
                
                html += "</div>"
            
            # Show correction if applied
            if was_corrected and pattern_name in corrections:
                correction = corrections[pattern_name]
                html += f"""
                <div class="correction-section">
                    <div class="correction-header">🔧 Pattern Corrected</div>
                    <div style="margin-top: 10px;">
                        <strong>New Pattern:</strong>
                        <div class="pattern-regex" style="margin-top: 5px;">
                            {html_escape(correction.get('corrected', 'N/A')[:500])}
                        </div>
                    </div>
                </div>
"""
            
            html += "</div>"
        
        html += "</div>"
    
    # Add JavaScript for filtering and navigation
    html += """
    <script>
        function filterPatterns(filter) {
            const buttons = document.querySelectorAll('.filter-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            const cards = document.querySelectorAll('.pattern-card');
            cards.forEach(card => {
                if (filter === 'all') {
                    card.style.display = 'block';
                } else if (filter === 'passed') {
                    card.style.display = card.dataset.status === 'passed' ? 'block' : 'none';
                } else if (filter === 'failed') {
                    card.style.display = card.dataset.status === 'failed' ? 'block' : 'none';
                } else if (filter === 'corrected') {
                    card.style.display = card.dataset.corrected === 'true' ? 'block' : 'none';
                }
            });
        }
        
        function scrollToFile(fileId) {
            const element = document.getElementById(fileId);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    </script>
</body>
</html>
"""
    
    return html

def html_escape(text):
    """Escape HTML special characters."""
    if not text:
        return ''
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))

if __name__ == "__main__":
    print("Generating comprehensive HTML validation report...")
    
    html_content = generate_html_report()
    
    # Save the report
    output_path = Path("/srv/luris/be/entity-extraction-service/tests/results/final_validation_report.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Report saved to: {output_path}")
    print(f"📊 Open the report in a browser to view the detailed results")