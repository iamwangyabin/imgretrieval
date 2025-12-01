#!/usr/bin/env python3
"""
Script to detect contradictions in CSV file.
Checks if the same model_name is associated with different base_models.
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime

def detect_contradictions(csv_file):
    """
    Read CSV file and detect contradictions.
    A contradiction exists when a model_name is associated with multiple different base_models.
    """
    
    # Map: model_name -> set of base_models
    model_to_bases = defaultdict(set)
    # Map: model_name -> list of records (for details)
    model_records = defaultdict(list)
    
    total_records = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                filename = row.get('filename', '')
                base_model = row.get('base_model', 'Unknown')
                model_name = row.get('model_name', 'Unknown')
                
                if not filename:
                    continue
                
                model_to_bases[model_name].add(base_model)
                model_records[model_name].append({
                    'filename': filename,
                    'base_model': base_model,
                    'width': row.get('width', ''),
                    'height': row.get('height', ''),
                    'nsfw_level': row.get('nsfw_level', ''),
                    'model_version_name': row.get('model_version_name', ''),
                })
                
                total_records += 1
    
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)
    
    # Extract contradictions
    contradictions = {}
    for model_name, base_models in model_to_bases.items():
        if len(base_models) > 1:
            contradictions[model_name] = {
                'base_models': sorted(list(base_models)),
                'count': len(base_models),
                'total_records': len(model_records[model_name])
            }
    
    return contradictions, model_records, total_records, len(model_to_bases)

def generate_json_report(contradictions, model_records, total_records, total_models, output_file):
    """Generate JSON report for contradictions"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_records': total_records,
            'total_unique_models': total_models,
            'models_with_contradictions': len(contradictions),
            'has_contradictions': len(contradictions) > 0,
        },
        'contradictions': {}
    }
    
    for model_name in sorted(contradictions.keys()):
        contradiction = contradictions[model_name]
        report['contradictions'][model_name] = {
            'base_models': contradiction['base_models'],
            'base_model_count': contradiction['count'],
            'total_records': contradiction['total_records'],
            'records': [
                {
                    'filename': record['filename'],
                    'base_model': record['base_model'],
                    'width': record['width'],
                    'height': record['height'],
                    'nsfw_level': record['nsfw_level'],
                }
                for record in model_records[model_name]
            ]
        }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"JSON report saved to: {output_file}")

def generate_html_report(contradictions, model_records, total_records, total_models, output_file):
    """Generate HTML report for contradictions"""
    
    has_contradictions = len(contradictions) > 0
    status_text = 'Contradictions Detected!' if has_contradictions else 'No Contradictions Found!'
    status_emoji = '⚠️' if has_contradictions else '✅'
    
    # Build contradiction cards
    contradictions_html = ''
    for model_name in sorted(contradictions.keys()):
        contradiction = contradictions[model_name]
        base_models_html = ', '.join(contradiction['base_models'])
        
        records_sample = ''
        for record in model_records[model_name][:10]:
            records_sample += f"<tr><td>{record['filename']}</td><td>{record['base_model']}</td></tr>\n"
        
        if len(model_records[model_name]) > 10:
            records_sample += f"<tr><td colspan='2'>... and {len(model_records[model_name]) - 10} more records</td></tr>\n"
        
        contradictions_html += f"""        <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; margin-bottom: 20px; border-radius: 6px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
                <div style="font-size: 18px; font-weight: bold;">Model: {model_name}</div>
                <div style="background: #ffc107; color: white; padding: 5px 12px; border-radius: 20px; font-size: 12px;">{contradiction['count']} Base Models</div>
            </div>
            <div style="margin-bottom: 15px; padding: 10px; background: white; border-radius: 4px;">
                <strong>Associated Base Models:</strong><br/>{base_models_html}
            </div>
            <div style="margin-top: 15px;">
                <div style="font-size: 13px; font-weight: bold; margin-bottom: 10px;">Sample Records ({len(model_records[model_name])} total):</div>
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <tr style="background: #f8f9fa; border: 1px solid #e0e0e0;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #e0e0e0;">Filename</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid #e0e0e0;">Base Model</th>
                    </tr>
{records_sample}                </table>
            </div>
        </div>
"""
    
    if not contradictions_html:
        contradictions_html = '<p style="color: #27ae60; text-align: center; padding: 20px;">All models have consistent base_model associations. No contradictions detected.</p>'
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Model Contradiction Detection</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f5f5f5;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }}
        .stat {{
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .stat .number {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }}
        .stat .label {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}
        .content {{
            padding: 30px;
        }}
        .footer {{
            padding: 20px;
            text-align: center;
            color: #999;
            font-size: 12px;
            border-top: 1px solid #e0e0e0;
            background: #f8f9fa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Model Contradiction Detection Report</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="number">{total_records}</div>
                <div class="label">Total Records</div>
            </div>
            <div class="stat">
                <div class="number">{total_models}</div>
                <div class="label">Unique Models</div>
            </div>
            <div class="stat">
                <div class="number">{len(contradictions)}</div>
                <div class="label">Models with Contradictions</div>
            </div>
        </div>
        
        <div style="text-align: center; padding: 20px; background: #f0f0f0;">
            <h2>{status_emoji} {status_text}</h2>
        </div>
        
        <div class="content">
{contradictions_html}
        </div>
        
        <div class="footer">
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {total_records} total records, {total_models} unique models</p>
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"HTML report saved to: {output_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 detect_contradictions.py <csv_file>")
        print("Example: python3 detect_contradictions.py sample_data.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    base_name = Path(csv_file).stem
    
    print(f"Analyzing: {csv_file}")
    print("Detecting contradictions (same model across different base_models)...\n")
    
    contradictions, model_records, total_records, total_models = detect_contradictions(csv_file)
    
    json_file = f"{base_name}_contradictions.json"
    html_file = f"{base_name}_contradictions.html"
    
    # Generate reports
    generate_json_report(contradictions, model_records, total_records, total_models, json_file)
    generate_html_report(contradictions, model_records, total_records, total_models, html_file)
    
    print(f"\nAnalysis complete!")
    print(f"\nSummary:")
    print(f"  - Total Records: {total_records}")
    print(f"  - Total Unique Models: {total_models}")
    print(f"  - Models with Contradictions: {len(contradictions)}")
    
    if contradictions:
        print(f"\nContradiction Details:")
        for model_name in sorted(contradictions.keys()):
            contradiction = contradictions[model_name]
            print(f"  - {model_name}: appears in {contradiction['count']} base_models")
            print(f"    Base Models: {', '.join(contradiction['base_models'])}")
            print(f"    Total Records: {contradiction['total_records']}")
    else:
        print(f"\nNo contradictions found! All models are consistent.")
    
    print(f"\nReports generated:")
    print(f"  - {json_file}")
    print(f"  - {html_file}")

if __name__ == "__main__":
    main()
