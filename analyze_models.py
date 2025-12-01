#!/usr/bin/env python3
"""
Script to analyze CSV file and group images by base_model and model_name.
Shows hierarchical statistics before organizing files.
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

def analyze_csv(csv_file):
    """
    Read CSV file and analyze the hierarchical structure of models.
    Groups images by base_model -> model_name
    """
    
    # Data structure: base_model -> model_name -> list of image info
    hierarchy = defaultdict(lambda: defaultdict(list))
    
    # Statistics
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

def print_statistics(hierarchy, total_images, unique_base_models, unique_models):
    """Print summary statistics"""
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total Images: {total_images}")
    print(f"Unique Base Models: {len(unique_base_models)}")
    print(f"Unique Model Names: {len(unique_models)}")
    print()

def print_hierarchy(hierarchy):
    """Print hierarchical tree structure"""
    print("=" * 80)
    print("HIERARCHICAL STRUCTURE")
    print("=" * 80)
    
    # Sort base_models
    for base_model in sorted(hierarchy.keys()):
        models = hierarchy[base_model]
        total_in_base = sum(len(imgs) for imgs in models.values())
        
        print(f"\n📦 BASE_MODEL: {base_model}")
        print(f"   Total Images: {total_in_base}")
        print(f"   Model Variants: {len(models)}")
        
        # Sort models within each base_model
        for model_name in sorted(models.keys()):
            images = models[model_name]
            print(f"   ├─ 🎨 {model_name}")
            print(f"   │  Images: {len(images)}")
            
            # Show first 3 images as examples
            for i, img in enumerate(images[:3]):
                prefix = "   │  ├─" if i < 2 else "   │  └─"
                print(f"{prefix} {img['filename']} ({img['width']}x{img['height']})")
            
            if len(images) > 3:
                print(f"   │  └─ ... and {len(images) - 3} more images")

def print_detailed_breakdown(hierarchy):
    """Print detailed breakdown by base_model"""
    print("\n" + "=" * 80)
    print("DETAILED BREAKDOWN")
    print("=" * 80)
    
    for base_model in sorted(hierarchy.keys()):
        models = hierarchy[base_model]
        total_in_base = sum(len(imgs) for imgs in models.values())
        
        print(f"\n{base_model}:")
        print(f"  Total: {total_in_base} images")
        
        model_stats = []
        for model_name in sorted(models.keys()):
            count = len(models[model_name])
            model_stats.append((model_name, count))
        
        # Sort by count descending
        model_stats.sort(key=lambda x: x[1], reverse=True)
        
        for model_name, count in model_stats:
            percentage = (count / total_in_base) * 100
            bar = "█" * int(percentage / 2)
            print(f"    {model_name}: {count:5d} images ({percentage:5.1f}%) {bar}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_models.py <csv_file>")
        print()
        print("Example:")
        print("  python analyze_models.py merged_all_tables.csv")
        print()
        print("This script will:")
        print("  1. Read the CSV file")
        print("  2. Group images by base_model and model_name")
        print("  3. Show statistics and hierarchical structure")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    print(f"Analyzing: {csv_file}\n")
    
    # Analyze the CSV
    hierarchy, total_images, unique_base_models, unique_models = analyze_csv(csv_file)
    
    # Print all information
    print_statistics(hierarchy, total_images, unique_base_models, unique_models)
    print_hierarchy(hierarchy)
    print_detailed_breakdown(hierarchy)
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()
