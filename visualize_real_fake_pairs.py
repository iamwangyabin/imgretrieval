"""
Visualize Random Fake-Real Image Pairs

This script:
1. Reads pairing metadata from build_fake_real_pairs.py output
2. Randomly selects 10 pairs of fake-real images
3. Creates a visualization showing them side-by-side
"""

import os
import json
import argparse
import random
from pathlib import Path
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np


def load_pairing_metadata(output_dir: str) -> Dict:
    """Load pairing metadata from output directory."""
    metadata_path = os.path.join(output_dir, "pairing_metadata.json")
    
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    return metadata


def validate_image_path(path: str) -> bool:
    """Check if image path exists and is readable."""
    if os.path.islink(path):
        # For symlinks, follow the link
        real_path = os.path.realpath(path)
        return os.path.exists(real_path) and os.path.isfile(real_path)
    return os.path.exists(path) and os.path.isfile(path)


def load_image(image_path: str, max_size: Tuple[int, int] = (300, 300)) -> Image.Image:
    """Load and resize image."""
    try:
        # Handle symlinks
        if os.path.islink(image_path):
            image_path = os.path.realpath(image_path)
        
        img = Image.open(image_path)
        
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        
        # Resize to max_size while maintaining aspect ratio
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        return img
    except Exception as e:
        print(f"Warning: Could not load image {image_path}: {e}")
        return None


def select_valid_pairs(metadata: Dict, num_pairs: int = 10) -> List[Dict]:
    """Select pairs where both fake and real images exist."""
    pairs = metadata.get("pairs", [])
    
    valid_pairs = []
    for pair in pairs:
        fake_path = pair.get("fake_image")
        real_path = pair.get("matched_real_image")
        
        if fake_path and real_path and validate_image_path(fake_path) and validate_image_path(real_path):
            valid_pairs.append(pair)
    
    if len(valid_pairs) == 0:
        raise ValueError("No valid image pairs found in metadata")
    
    # Randomly select pairs
    selected_pairs = random.sample(valid_pairs, min(num_pairs, len(valid_pairs)))
    
    return selected_pairs


def create_visualization(pairs: List[Dict], output_path: str = "fake_real_pairs_visualization.jpg"):
    """Create and save visualization of fake-real pairs."""
    num_pairs = len(pairs)
    
    # Create figure with subplots (num_pairs rows, 2 columns)
    fig, axes = plt.subplots(num_pairs, 2, figsize=(12, 4 * num_pairs))
    
    # Handle single pair case
    if num_pairs == 1:
        axes = axes.reshape(1, -1)
    
    fig.suptitle(f"Fake-Real Image Pairs (Random Selection: {num_pairs} pairs)", 
                 fontsize=16, fontweight='bold', y=0.995)
    
    for idx, pair in enumerate(pairs):
        fake_path = pair.get("fake_image")
        real_path = pair.get("matched_real_image")
        similarity = pair.get("similarity_score", 0)
        
        # Load fake image
        fake_img = load_image(fake_path)
        if fake_img is None:
            fake_img = Image.new('RGB', (300, 300), (200, 200, 200))
        
        # Load real image
        real_img = load_image(real_path)
        if real_img is None:
            real_img = Image.new('RGB', (300, 300), (200, 200, 200))
        
        # Display fake image (left column)
        ax_fake = axes[idx, 0]
        ax_fake.imshow(fake_img)
        fake_filename = os.path.basename(fake_path)
        fake_model = pair.get("model", "unknown")
        ax_fake.set_title(f"Fake ({fake_model})\n{fake_filename[:30]}...", fontsize=10)
        ax_fake.axis('off')
        
        # Display real image (right column)
        ax_real = axes[idx, 1]
        ax_real.imshow(real_img)
        real_filename = os.path.basename(real_path)
        score_text = f"Similarity: {similarity:.4f}" if similarity else "Similarity: N/A"
        ax_real.set_title(f"Real Match\n{real_filename[:30]}... ({score_text})", fontsize=10)
        ax_real.axis('off')
    
    plt.tight_layout()
    
    # Save figure
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
    print(f"✓ Visualization saved to: {output_path}")
    
    # Also display the figure
    plt.show()


def main():
    """Command-line interface for visualizing fake-real pairs."""
    parser = argparse.ArgumentParser(
        description="Visualize random fake-real image pairs from build_fake_real_pairs.py output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python visualize_real_fake_pairs.py /path/to/output_dir
  python visualize_real_fake_pairs.py /path/to/output_dir --num-pairs 5 --output viz.jpg
  python visualize_real_fake_pairs.py /path/to/output_dir --seed 42
        """
    )
    
    parser.add_argument(
        "output_dir",
        help="Output directory from build_fake_real_pairs.py (contains pairing_metadata.json)"
    )
    
    parser.add_argument(
        "--num-pairs", "-n",
        type=int,
        default=10,
        help="Number of pairs to visualize (default: 10)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="fake_real_pairs_visualization.jpg",
        help="Output image path (default: fake_real_pairs_visualization.jpg)"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed information"
    )
    
    args = parser.parse_args()
    
    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
    
    try:
        print("="*70)
        print("Visualizing Fake-Real Image Pairs")
        print("="*70)
        print(f"\nLoading metadata from: {args.output_dir}")
        
        # Load metadata
        metadata = load_pairing_metadata(args.output_dir)
        total_pairs = len(metadata.get("pairs", []))
        print(f"Total pairs in metadata: {total_pairs}")
        
        # Select valid pairs
        print(f"\nSelecting {args.num_pairs} random valid pairs...")
        selected_pairs = select_valid_pairs(metadata, args.num_pairs)
        print(f"✓ Selected {len(selected_pairs)} valid pairs")
        
        if args.verbose:
            for i, pair in enumerate(selected_pairs, 1):
                print(f"\n  Pair {i}:")
                print(f"    Fake:  {pair.get('fake_filename')}")
                print(f"    Real:  {pair.get('matched_real_filename')}")
                print(f"    Similarity: {pair.get('similarity_score', 'N/A')}")
        
        # Create visualization
        print(f"\nCreating visualization...")
        create_visualization(selected_pairs, args.output)
        
        print("\n" + "="*70)
        print("✓ Visualization complete!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
