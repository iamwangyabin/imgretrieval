"""
Visual Test for Image Retrieval System

This script:
1. Randomly selects N query images from the database
2. For each query, performs a search and retrieves top K similar images
3. Creates a visual grid showing query images and their retrieval results
"""

import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from src.database import get_all_processed_paths
from src.search import SearchEngine


def load_and_resize_image(image_path, target_size=(150, 150)):
    """Load and resize an image to target size."""
    try:
        img = Image.open(image_path).convert('RGB')
        img.thumbnail(target_size, Image.Resampling.LANCZOS)
        
        # Create a new image with white background
        result = Image.new('RGB', target_size, (255, 255, 255))
        # Center the thumbnail
        offset = ((target_size[0] - img.size[0]) // 2, (target_size[1] - img.size[1]) // 2)
        result.paste(img, offset)
        return result
    except Exception as e:
        print(f"Error loading {image_path}: {e}")
        # Return a blank white image with error text
        result = Image.new('RGB', target_size, (255, 255, 255))
        return result


def add_label(img, text, position='top', color=(0, 0, 0), bg_color=(255, 255, 255)):
    """Add a text label to an image."""
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fall back to default if not available
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
    except:
        font = ImageFont.load_default()
    
    # Get text size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Create position
    if position == 'top':
        x = (img.width - text_width) // 2
        y = 5
    elif position == 'bottom':
        x = (img.width - text_width) // 2
        y = img.height - text_height - 5
    else:
        x, y = position
    
    # Draw background rectangle
    padding = 2
    draw.rectangle(
        [(x - padding, y - padding), (x + text_width + padding, y + text_height + padding)],
        fill=bg_color
    )
    
    # Draw text
    draw.text((x, y), text, fill=color, font=font)
    
    return img


def create_retrieval_grid(query_paths, search_results, output_path, top_k=10):
    """
    Create a grid visualization of retrieval results.
    
    Args:
        query_paths: List of query image paths
        search_results: List of search results (each is a list of (path, score) tuples)
        output_path: Path to save the output image
        top_k: Number of top results to show per query
    """
    n_queries = len(query_paths)
    
    # Image settings
    img_size = 150
    gap = 10
    query_gap = 30  # Extra gap between different queries
    
    # Calculate grid dimensions
    cols = top_k + 1  # query + top_k results
    
    # Calculate canvas size
    canvas_width = cols * img_size + (cols - 1) * gap + 40  # 40 for margins
    canvas_height = n_queries * img_size + (n_queries - 1) * (gap + query_gap) + 40 + 30  # 30 for title
    
    # Create canvas
    canvas = Image.new('RGB', (canvas_width, canvas_height), (240, 240, 240))
    draw = ImageDraw.Draw(canvas)
    
    # Add title
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except:
        title_font = ImageFont.load_default()
    
    title = f"Image Retrieval Test: {n_queries} Queries × Top-{top_k} Results"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((canvas_width - title_width) // 2, 10), title, fill=(0, 0, 0), font=title_font)
    
    # Process each query
    for query_idx, (query_path, results) in enumerate(zip(query_paths, search_results)):
        # Calculate y position for this row
        y_offset = 40 + query_idx * (img_size + gap + query_gap)
        
        # Load and add query image
        x_offset = 20
        query_img = load_and_resize_image(query_path, (img_size, img_size))
        
        # Add label for filename and id below the image
        filename = os.path.basename(query_path)
        query_id = query_idx + 1
        label_text = f"{filename}\nID: {query_id}"
        query_img = add_label(query_img, f"Query {query_id}", position='top', 
                              color=(255, 255, 255), bg_color=(0, 100, 200))
        query_img = add_label(query_img, label_text, position=(5, img_size - 30),
                              color=(0, 0, 0), bg_color=(255, 255, 255))
        
        # Add border to query image
        bordered_query = Image.new('RGB', (img_size + 4, img_size + 4), (0, 100, 200))
        bordered_query.paste(query_img, (2, 2))
        canvas.paste(bordered_query, (x_offset - 2, y_offset - 2))
        
        # Add arrow
        arrow_x = x_offset + img_size + 5
        arrow_y = y_offset + img_size // 2
        draw.polygon(
            [(arrow_x, arrow_y), (arrow_x + 15, arrow_y - 8), (arrow_x + 15, arrow_y + 8)],
            fill=(100, 100, 100)
        )
        
        # Add top-k results
        for rank, (result_path, score) in enumerate(results[:top_k]):
            x_offset = 20 + (rank + 1) * (img_size + gap) + 20  # +20 for arrow space
            
            result_img = load_and_resize_image(result_path, (img_size, img_size))
            
            # Check if it's the same as query (self-match)
            is_self_match = os.path.abspath(result_path) == os.path.abspath(query_path)
            
            # Add rank and score label
            label = f"#{rank + 1}"
            if is_self_match:
                label += " (self)"
                border_color = (0, 200, 0)
            else:
                border_color = (200, 200, 200)
            
            result_img = add_label(result_img, label, position='top',
                                  color=(50, 50, 50), bg_color=(255, 255, 200))
            
            # Add filename and id label below image
            filename = os.path.basename(result_path)
            result_id = rank + 1
            file_label = f"{filename}\nID: {result_id}"
            result_img = add_label(result_img, file_label, position=(5, img_size - 30),
                                  color=(0, 0, 0), bg_color=(255, 255, 255))
            
            # Add score at bottom
            score_text = f"{score:.3f}"
            result_img = add_label(result_img, score_text, position='bottom',
                                  color=(50, 50, 50), bg_color=(255, 255, 255))
            
            # Add border
            bordered_result = Image.new('RGB', (img_size + 2, img_size + 2), border_color)
            bordered_result.paste(result_img, (1, 1))
            canvas.paste(bordered_result, (x_offset - 1, y_offset - 1))
    
    # Save the result
    canvas.save(output_path, quality=95)
    print(f"\nVisualization saved to: {output_path}")
    print(f"Image size: {canvas_width}x{canvas_height} pixels")
    
    return canvas


def run_retrieval_test(n_queries=10, top_k=10, output_path="retrieval_test_results.jpg"):
    """
    Run the retrieval test.
    
    Args:
        n_queries: Number of random queries to test
        top_k: Number of top results to retrieve per query
        output_path: Path to save the visualization
    """
    print("="*60)
    print("Image Retrieval Visual Test")
    print("="*60)
    
    # Initialize search engine
    print("\n1. Initializing search engine...")
    search_engine = SearchEngine()
    
    if search_engine.index is None:
        print("Error: No index found. Please build index first using main.py")
        return
    
    print(f"   ✓ Index loaded with {search_engine.index.ntotal} images")
    
    # Get all processed images
    print("\n2. Loading processed images from database...")
    all_paths = get_all_processed_paths()
    
    if len(all_paths) == 0:
        print("Error: No processed images found in database")
        return
    
    print(f"   ✓ Found {len(all_paths)} processed images")
    
    # Randomly sample queries
    print(f"\n3. Randomly selecting {n_queries} query images...")
    if len(all_paths) < n_queries:
        print(f"   Warning: Only {len(all_paths)} images available, using all of them")
        query_paths = all_paths
    else:
        query_paths = random.sample(all_paths, n_queries)
    
    for i, path in enumerate(query_paths, 1):
        print(f"   Query {i}: {os.path.basename(path)}")
    
    # Perform searches
    print(f"\n4. Performing searches (top-{top_k} results per query)...")
    search_results = []
    
    for i, query_path in enumerate(query_paths, 1):
        print(f"   Searching {i}/{len(query_paths)}: {os.path.basename(query_path)}")
        results = search_engine.search(query_path, k=top_k)
        search_results.append(results)
        
        if results:
            print(f"      ✓ Found {len(results)} results, top score: {results[0][1]:.4f}")
    
    # Create visualization
    print(f"\n5. Creating visualization grid...")
    create_retrieval_grid(query_paths, search_results, output_path, top_k)
    
    # Print summary statistics
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Total queries: {len(query_paths)}")
    print(f"Top-K: {top_k}")
    print(f"Total searches performed: {len(search_results)}")
    
    # Calculate some statistics
    self_match_count = 0
    avg_top1_score = 0
    
    for query_path, results in zip(query_paths, search_results):
        if results:
            # Check if top-1 is self-match
            if os.path.abspath(results[0][0]) == os.path.abspath(query_path):
                self_match_count += 1
            avg_top1_score += results[0][1]
    
    if search_results:
        avg_top1_score /= len(search_results)
        self_match_rate = self_match_count / len(search_results) * 100
        
        print(f"Self-match rate (top-1): {self_match_rate:.1f}% ({self_match_count}/{len(search_results)})")
        print(f"Average top-1 score: {avg_top1_score:.4f}")
    
    print("="*60)
    print(f"\n✓ Test complete! Check the output: {output_path}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Visual test for image retrieval system")
    parser.add_argument("--queries", "-q", type=int, default=10,
                       help="Number of random queries to test (default: 10)")
    parser.add_argument("--topk", "-k", type=int, default=10,
                       help="Number of top results to retrieve (default: 10)")
    parser.add_argument("--output", "-o", type=str, default="retrieval_test_results.jpg",
                       help="Output image path (default: retrieval_test_results.jpg)")
    parser.add_argument("--seed", "-s", type=int, default=None,
                       help="Random seed for reproducibility (default: None)")
    
    args = parser.parse_args()
    
    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)
        print(f"Random seed set to: {args.seed}")
    
    run_retrieval_test(
        n_queries=args.queries,
        top_k=args.topk,
        output_path=args.output
    )
