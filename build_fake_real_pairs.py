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
from typing import Dict, List, Tuple, Set
from src.search import SearchEngine
from PIL import Image
import time


class CheckpointManager:
    """Manages progress checkpoints for resumable processing."""
    
    def __init__(self, output_root: str):
        """Initialize checkpoint manager."""
        self.output_root = output_root
        self.checkpoint_path = os.path.join(output_root, ".checkpoint.json")
        self.checkpoint_data = self._load_checkpoint()
    
    def _load_checkpoint(self) -> Dict:
        """Load checkpoint from file if it exists."""
        if os.path.exists(self.checkpoint_path):
            try:
                with open(self.checkpoint_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load checkpoint: {e}")
                return self._create_empty_checkpoint()
        return self._create_empty_checkpoint()
    
    def _create_empty_checkpoint(self) -> Dict:
        """Create an empty checkpoint structure."""
        return {
            "processed_images": [],
            "failed_images": [],
            "pairs_count": 0,
            "start_time": None,
            "last_update_time": None
        }
    
    def save(self):
        """Save checkpoint to file."""
        self.checkpoint_data["last_update_time"] = time.time()
        try:
            with open(self.checkpoint_path, 'w') as f:
                json.dump(self.checkpoint_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save checkpoint: {e}")
    
    def is_processed(self, image_path: str) -> bool:
        """Check if image has been processed."""
        return image_path in self.checkpoint_data["processed_images"]
    
    def mark_processed(self, image_path: str, pair_data: Dict = None):
        """Mark image as successfully processed."""
        if image_path not in self.checkpoint_data["processed_images"]:
            self.checkpoint_data["processed_images"].append(image_path)
            if pair_data:
                self.checkpoint_data["pairs_count"] += 1
    
    def mark_failed(self, image_path: str):
        """Mark image as failed."""
        if image_path not in self.checkpoint_data["failed_images"]:
            self.checkpoint_data["failed_images"].append(image_path)
    
    def get_processed_count(self) -> int:
        """Get count of processed images."""
        return len(self.checkpoint_data["processed_images"])
    
    def get_failed_count(self) -> int:
        """Get count of failed images."""
        return len(self.checkpoint_data["failed_images"])
    
    def clear(self):
        """Clear checkpoint data."""
        self.checkpoint_data = self._create_empty_checkpoint()
        self.checkpoint_data["start_time"] = time.time()
        self.save()


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
    
    # Get relative path from the model directory
    if model_name == 'root':
        relative_path = fake_path_obj.parent.relative_to(fake_root_obj)
    else:
        # For model subdirectories, get relative path from model directory
        model_root = fake_root_obj / model_name
        try:
            relative_path = fake_path_obj.parent.relative_to(model_root)
        except ValueError:
            # Fallback if path structure is unexpected
            relative_path = Path('.')
    
    output_dir = Path(output_root) / model_name / relative_path
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return str(output_dir)


def build_fake_real_pairs(
    fake_root: str,
    output_root: str = None,
    top_k: int = 10,
    verbose: bool = True,
    resume: bool = False,
    clean: bool = False
):
    """
    Main function to build fake-real image pairs.
    
    Args:
        fake_root: Root directory containing fake images
        output_root: Output directory for paired real images (default: fake_root_parent/real_paired)
        top_k: Number of top candidates to consider for matching
        verbose: Print progress information
        resume: Resume from previous checkpoint
        clean: Clear previous checkpoint and start fresh
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
    
    # Initialize checkpoint manager
    checkpoint_mgr = CheckpointManager(output_root)
    
    # Handle clean flag
    if clean:
        print("\n[Checkpoint] Clearing previous progress...")
        checkpoint_mgr.clear()
        print("✓ Checkpoint cleared, starting fresh")
    elif resume:
        processed = checkpoint_mgr.get_processed_count()
        failed = checkpoint_mgr.get_failed_count()
        if processed > 0 or failed > 0:
            print(f"\n[Checkpoint] Resuming from previous run:")
            print(f"  Previously processed: {processed}")
            print(f"  Previously failed:    {failed}")
        else:
            print("\n[Checkpoint] No previous checkpoint found, starting fresh")
    else:
        # If not resuming and checkpoint exists, warn user
        if checkpoint_mgr.get_processed_count() > 0:
            print("\n[Checkpoint] Previous progress detected!")
            print(f"  Processed: {checkpoint_mgr.get_processed_count()}")
            print(f"  Run with --resume to continue, or --clean to restart")
    
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
    
    # Load existing pairs if resuming
    metadata_path = os.path.join(output_root, "pairing_metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                existing_data = json.load(f)
                pairing_data["pairs"] = existing_data.get("pairs", [])
        except:
            pass
    
    processed_count = checkpoint_mgr.get_processed_count()
    failed_count = checkpoint_mgr.get_failed_count()
    symlink_count = len(pairing_data["pairs"])
    
    total_to_process = total_fake_images - processed_count - failed_count
    start_time = time.time()
    
    for model_name in sorted(model_images.keys()):
        images = model_images[model_name]
        
        print(f"\n  Processing model '{model_name}' ({len(images)} images)...")
        
        for idx, fake_image_path in enumerate(images, 1):
            # Skip if already processed
            if checkpoint_mgr.is_processed(fake_image_path):
                if verbose and idx % 50 == 0:
                    progress = processed_count + failed_count
                    pct = (progress / total_fake_images) * 100
                    print(f"    ⊘ Skipped {idx}/{len(images)} images (already processed, {pct:.1f}% done)")
                continue
            
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
                    checkpoint_mgr.mark_failed(fake_image_path)
                    checkpoint_mgr.save()
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
                pair_info = {
                    "fake_image": fake_image_path,
                    "fake_filename": fake_filename,
                    "fake_directory": output_dir,
                    "matched_real_image": best_real_path,
                    "matched_real_filename": real_filename,
                    "symlink_path": symlink_path,
                    "similarity_score": float(similarity_score),
                    "model": model_name,
                    "rank": 1  # Position in search results
                }
                pairing_data["pairs"].append(pair_info)
                
                processed_count += 1
                checkpoint_mgr.mark_processed(fake_image_path, pair_info)
                
                # Save checkpoint every 10 processed images
                if processed_count % 10 == 0:
                    checkpoint_mgr.save()
                    if verbose:
                        elapsed = time.time() - start_time
                        progress = processed_count + failed_count
                        pct = (progress / total_fake_images) * 100
                        rate = (processed_count + failed_count) / elapsed if elapsed > 0 else 0
                        remaining = (total_fake_images - progress) / rate if rate > 0 else 0
                        print(f"    ✓ Processed {idx}/{len(images)} images ({pct:.1f}%, ~{remaining/60:.0f}min remaining)")
                
            except Exception as e:
                fake_filename = os.path.basename(fake_image_path)
                if verbose:
                    print(f"    ✗ {fake_filename}: {str(e)}")
                failed_count += 1
                checkpoint_mgr.mark_failed(fake_image_path)
                checkpoint_mgr.save()
    
    # Final checkpoint save
    checkpoint_mgr.save()
    
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
    
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous checkpoint (skip already processed images)"
    )
    
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clear previous checkpoint and start fresh"
    )
    
    args = parser.parse_args()
    
    try:
        build_fake_real_pairs(
            fake_root=args.fake_root,
            output_root=args.output,
            top_k=args.top_k,
            verbose=not args.quiet,
            resume=args.resume,
            clean=args.clean
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
