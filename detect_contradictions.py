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
    
    if not contradictions:
        status_html = '<div style="text-align: center; padding: 40px; color: #27ae60;"><h2>✅ No Contradictions Found!</h2><p>All models have consistent base_model associations.</p></div>'
    else:
        status_html = '<div style="text-align: center; padding: 40px; background: #fff3cd; color: #856404;"><h2>⚠️ Contradictions Detected!</h2><p>The following models are associated with multiple base_models.</p></div>'
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Model Contradiction Detection Report</title>
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
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .header p {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .status {{
            border-bottom: 2px solid #e0e0e0;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        .stat-card .number {{
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        .stat-card .label {{
            color: #666;
            font-size: 14px;
        }}
        .stat-card.warning .number {{
            color: #ff6b6b;
        }}
        .content {{
            padding: 30px;
        }}
        .contradiction-item {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 6px;
        }}
        .contradiction-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .model-name {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }}
        .contradiction-badge {{
            background: #ffc107;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }}
        .base-models {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
        }}
        .base-model-badge {{
            background: white;
            border: 2px solid #ffc107;
            padding: 10px;
            border-radius: 6px;
            text-align: center;
            font-weight: 500;
            color: #333;
        }}
        .records-section {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e0e0e0;
        }}
        .records-title {{
            font-size: 13px;
            font-weight: bold;
            color: #666;
            margin-bottom: 10px;
        }}
        .record-item {{
            background: white;
            padding: 10px;
            margin-bottom: 5px;
            border-radius: 4px;
            font-size: 12px;
            color: #666;
            display: flex;
            justify-content: space-between;
            border: 1px solid #e0e0e0;
        }}
        .record-filename {{
            flex: 1;
            word-break: break
