#!/usr/bin/env python3
"""
Script to analyze CSV file and group images by base_model and model_name.
Outputs formatted report to HTML and JSON files.
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime

def analyze_csv(csv_file):
    """
    Read CSV file and analyze the hierarchical structure of models.
    Groups images by base_model -> model_name
    """
    
    hierarchy = defaultdict(lambda: defaultdict(list))
    total_images = 0
    unique_base_models = set()
    unique_models = set()
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                filename = row.get('filename', '')
                base_model = row.get('base_model', 'Unknown')
                model_name = row.get('model_name', 'Unknown')
                
                if not filename:
                    continue
                
                hierarchy[base_model][model_name].append({
                    'filename': filename,
                    'width': row.get('width', ''),
                    'height': row.get('height', ''),
                    'nsfw_level': row.get('nsfw_level', ''),
                    'model_version_name': row.get('model_version_name', ''),
                })
                
                total_images += 1
                unique_base_models.add(base_model)
                unique_models.add(model_name)
    
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)
    
    return hierarchy, total_images, unique_base_models, unique_models

def generate_json_report(hierarchy, total_images, unique_base_models, unique_models, output_file):
    """Generate JSON report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_images': total_images,
            'unique_base_models': len(unique_base_models),
            'unique_model_names': len(unique_models),
            'base_models': sorted(list(unique_base_models)),
        },
        'hierarchy': {}
    }
    
    for base_model in sorted(hierarchy.keys()):
        models = hierarchy[base_model]
        total_in_base = sum(len(imgs) for imgs in models.values())
        
        report['hierarchy'][base_model] = {
            'total_images': total_in_base,
            'model_count': len(models),
            'models': {}
        }
        
        for model_name in sorted(models.keys()):
            images = models[model_name]
            report['hierarchy'][base_model]['models'][model_name] = {
                'image_count': len(images),
                'images': [
                    {
                        'filename': img['filename'],
                        'width': img['width'],
                        'height': img['height'],
                        'nsfw_level': img['nsfw_level'],
                    }
                    for img in images
                ]
            }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"JSON report saved to: {output_file}")

def generate_html_report(hierarchy, total_images, unique_base_models, unique_models, output_file):
    """Generate HTML report"""
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Model Analysis Report</title>
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
        .content {{
            padding: 30px;
        }}
        .base-model-section {{
            margin-bottom: 40px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }}
        .base-model-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            font-size: 18px;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .model-count {{
            background: rgba(255,255,255,0.2);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 13px;
        }}
        .models-container {{
            padding: 20px;
            background: #f8f9fa;
        }}
        .model {{
            background: white;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }}
        .model-name {{
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
            font-size: 15px;
        }}
        .model-stats {{
            display: flex;
            gap: 20px;
            font-size: 13px;
            color: #666;
        }}
        .progress-bar {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .bar {{
            flex: 1;
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
        }}
        .bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
        }}
        .image-list {{
            margin-top: 10px;
            font-size: 12px;
            color: #666;
            padding-top: 10px;
            border-top: 1px solid #e0e0e0;
        }}
        .image-item {{
            padding: 5px 0;
            display: flex;
            justify-content: space-between;
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
            <h1>📊 Model Hierarchy Analysis Report</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="number">{total_images}</div>
                <div class="label">Total Images</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(unique_base_models)}</div>
                <div class="label">Base Models</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(unique_models)}</div>
                <div class="label">Model Names</div>
            </div>
        </div>
        
        <div class="content">
"""
    
    for base_model in sorted(hierarchy.keys()):
        models = hierarchy[base_model]
        total_in_base = sum(len(imgs) for imgs in models.values())
        
        html += f"""
            <div class="base-model-section">
                <div class="base-model-header">
                    <span>📦 {base_model}</span>
                    <span class="model-count">{total_in_base} images</span>
                </div>
                <div class="models-container">
"""
        
        for model_name in sorted(models.keys()):
            images = models[model_name]
            image_count = len(images)
            percentage = (image_count / total_images) * 100
            
            html += f"""
                    <div class="model">
                        <div class="model-name">🎨 {model_name}</div>
                        <div class="model-stats">
                            <div class="progress-bar">
                                <span>{image_count} images ({percentage:.1f}%)</span>
                                <div class="bar">
                                    <div class="bar-fill" style="width: {min(percentage*2, 100)}%"></div>
                                </div>
                            </div>
                        </div>
                        <div class="image-list">
"""
            
            for img in images[:5]:
                html += f"""
                            <div class="image-item">
                                <span>{img['filename']}</span>
                                <span>{img['width']}x{img['height']}</span>
                            </div>
"""
            
            if len(images) > 5:
                html += f"""
                            <div class="image-item" style="color: #999;">
                                ... and {len(images) - 5} more images
                            </div>
"""
            
            html += """
                        </div>
                    </div>
"""
        
        html += """
                </div>
            </div>
"""
    
    html += f"""
        </div>
        
        <div class="footer">
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total {total_images} images organized in {len(unique_base_models)} base models with {len(unique_models)} model variants</p>
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
        print("Usage: python3 analyze_models.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    base_name = Path(csv_file).stem
    
    print(f"Analyzing: {csv_file}")
    
    hierarchy, total_images, unique_base_models, unique_models = analyze_csv(csv_file)
    
    json_file = f"{base_name}_report.json"
    html_file = f"{base_name}_report.html"
    
    generate_json_report(hierarchy, total_images, unique_base_models, unique_models, json_file)
    generate_html_report(hierarchy, total_images, unique_base_models, unique_models, html_file)
    
    print(f"\nAnalysis complete!")
    print(f"Reports generated:")
    print(f"  - {json_file}")
    print(f"  - {html_file}")

if __name__ == "__main__":
    main()
