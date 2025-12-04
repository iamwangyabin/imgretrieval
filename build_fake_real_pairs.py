"""
Build Fake-Real Image Pairs using Image Retrieval System

This script:
1. Scans the fake image directory structure
2. Extracts features for each fake image
3. Uses FAISS index to find the most similar real image
4. Creates a mirrored directory structure with symlinks to matched real images
5. Records pairing metadata
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
from src.search import SearchEngine
from PIL import Image


def is_valid_image(path: str) -> bool:
    """Check if file is a valid image."""
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
    return Path(path).suffix.lower() in valid_extensions


def scan_fake_directory(fake_root: str) -> Dict[str, List[str]]:
    """
    Scan fake directory and organize by model subdirectories.
    
    Returns:
        Dict mapping model_name -> list of image paths
    """
    model_images = {}
    
    fake_path = Path(fake_root)
    if not fake_path.exists():
        raise ValueError(f"Fake directory not found: {fake_root}")
    
    # Check if this is a single-level directory with just images
    images_in_root = [
        str(f) for f in fake_path.glob('*') 
        if f.is_file() and is_valid_image(str(f))
    ]
    
    # Check if this is a multi-level directory with model subdirectories
    subdirs = [d for d in fake_path.iterdir() if d.is_dir()]
    
    if images_in_root and not subdirs:
        # Single level - all images in root
        model_images['root'] = sorted(images_in_root)
        print(f"Found {len(images_in_root)} images in root directory")
    else:
        # Multi-level - images organized by model
        for model_dir in sorted(subdirs):
            model_name = model_dir.name
            images = [
                str(f) for f in model_dir.rglob('*')
                if f.is_file() and is_valid_image(str(f))
            ]
            
            if images:
                model_images[model_name] = sorted(images)
                print(f"Found {len(images)} images in model '{model_name}'")
    
    if not model_images:
        raise ValueError(f"No valid images found in {fake_root}")
    
    return model_images


def create_mirror_directory(fake_root: str, output_root: str, model_name: str, fake_path: str) -> str:
    """
    Create mirrored directory structure in output.
    
    Returns:
        Path to the created directory
    """
    fake_path_obj = Path(fake_path)
    fake_root_obj = Path(fake_root)
    
    # Get relative path from fake_root
    if model_name == 'root':
        relative_path = fake_path_obj.parent.relative_to(fake_root_obj)
    else:
        # For model subdirectories, preserve the structure
        try:
            relative_path = fake_path_obj.parent.relative_to(fake_root_obj)
        except ValueError:
            relative_path = fake_path_obj.parent.name
    
    output_dir = Path(output_root) / model_name / relative_path
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return str(output_dir)


def build_fake_real_pairs(
    fake_root: str,
    output_root: str = None,
    top_k: int = 10,
    verbose: bool = True
):
    """
    Main function to build fake-real image pairs.
    
    Args:
        fake_root: Root directory containing fake images
        output_root: Output directory for paired real images (default: fake_root_parent/real_paired)
        top_k: Number of top candidates to consider for matching
        verbose: Print progress information
    """
    
    print("="*70)
    print("Building Fake-Real Image Pairs")
    print("="*70)
    
    # Validate input
    fake_root = os.path.abspath(fake_root)
    
    if output_root is None:
        # Default output location - sibling to fake root with "_paired_real" suffix
        fake_parent = os.path.dirname(fake_root)
        fake_name = os.path.basename(fake_root)
        output_root = os.path.join(fake_parent, f"{fake_name}_paired_real")
    
    output_root = os.path.abspath(output_root)
    
    print(f"\nInput (fake images):  {fake_root}")
    print(f"Output (paired real): {output_root}")
    
    # Create output directory
    os.makedirs(output_root, exist_ok=True)
    
    # Step 1: Scan fake directory
    print("\n[Step 1] Scanning fake image directory...")
    model_images = scan_fake_directory(fake_root)
    total_fake_images = sum(len(images) for images in model_images.values())
    print(f"Total fake images found: {total_fake_images}")
    
    # Step 2: Initialize search engine
    print("\n[Step 2] Initializing search engine...")
    search_engine = SearchEngine()
    
    if search_engine.index is None:
        raise RuntimeError(
            "No FAISS index found! Please build the real image index first:\n"
            "  python main.py init\n"
            "  python main.py scan /path/to/real/images\n"
            "  python main.py process\n"
            "  python main.py build-index"
        )
    
    print(f"✓ Index loaded with {search_engine.index.ntotal} real images")
    
    # Step 3: Process each fake image
    print("\n[Step 3] Processing fake images and finding matches...")
    
    pairing_data = {
        "fake_root": fake_root,
        "output_root": output_root,
        "total_fake_images": total_fake_images,
        "pairs": []
    }
    
    processed_count = 0
    failed_count = 0
    symlink_count = 0
    
    for model_name in sorted(model_images.keys()):
        images = model_images[model_name]
        
        print(f"\n  Processing model '{model_name}' ({len(images)} images)...")
        
        for idx, fake_image_path in enumerate(images, 1):
            try:
                # Create output directory for this image
                output_dir = create_mirror_directory(fake_root, output_root, model_name, fake_image_path)
                fake_filename = os.path.basename(fake_image_path)
                
                # Search for matching real image
                search_results = search_engine.search(fake_image_path, k=top_k)
                
                if not search_results:
                    if verbose:
                        print(f"    ✗ {fake_filename}: No matching real image found")
                    failed_count += 1
                    continue
                
                # Get the best match (first result)
                best_real_path, similarity_score = search_results[0]
                real_filename = os.path.basename(best_real_path)
                
                # Create symlink with same name as fake image
                symlink_path = os.path.join(output_dir, fake_filename)
                
                # Remove existing symlink if it exists
                if os.path.lexists(symlink_path):
                    os.remove(symlink_path)
                
                # Create symlink (absolute path)
                real_abs_path = os.path.abspath(best_real_path)
                os.symlink(real_abs_path, symlink_path)
                symlink_count += 1
                
                # Record pairing information
                pairing_data["pairs"].append({
                    "fake_image": fake_image_path,
                    "fake_filename": fake_filename,
                    "fake_directory": output_dir,
                    "matched_real_image": best_real_path,
                    "matched_real_filename": real_filename,
                    "symlink_path": symlink_path,
                    "similarity_score": float(similarity_score),
                    "model": model_name,
                    "rank": 1  # Position in search results
                })
                
                if verbose and idx % 10 == 0:
                    print(f"    ✓ Processed {idx}/{len(images)} images")
                
                processed_count += 1
                
            except Exception as e:
                print(f"    ✗ {fake_filename}: {str(e)}")
                failed_count += 1
    
    # Step 4: Summary and save metadata
    print("\n[Step 4] Saving pairing metadata...")
    
    metadata_path = os.path.join(output_root, "pairing_metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(pairing_data, f, indent=2)
    
    print(f"✓ Metadata saved to {metadata_path}")
    
    # Print summary
    print("\n" + "="*70)
    print("PAIRING SUMMARY")
    print("="*70)
    print(f"Total fake images:    {total_fake_images}")
    print(f"Successfully paired:  {processed_count}")
    print(f"Failed to pair:       {failed_count}")
    print(f"Symlinks created:     {symlink_count}")
    print(f"\nOutput directory:     {output_root}")
    print(f"Metadata file:        {metadata_path}")
    
    if processed_count > 0:
        success_rate = (processed_count / total_fake_images) * 100
        print(f"Success rate:         {success_rate:.1f}%")
    
    print("="*70 + "\n")
    
    return pairing_data


def main():
    """Command-line interface for building fake-real pairs."""
    parser = argparse.ArgumentParser(
        description="Build fake-real image pairs using FAISS retrieval system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_fake_real_pairs.py /path/to/fake/images
  python build_fake_real_pairs.py /path/to/fake/images --output /path/to/output
  python build_fake_real_pairs.py /path/to/fake/images --top-k 20
        """
    )
    
    parser.add_argument(
        "fake_root",
        help="Root directory containing fake images (can be nested by model)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output directory for paired real images (default: <fake_root_parent>/<fake_root>_paired_real)"
    )
    
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=10,
        help="Number of top candidates to consider for matching (default: 10)"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress detailed progress output"
    )
    
    args = parser.parse_args()
    
    try:
        build_fake_real_pairs(
            fake_root=args.fake_root,
            output_root=args.output,
            top_k=args.top_k,
            verbose=not args.quiet
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
