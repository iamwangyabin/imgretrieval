"""
Build Fake-Real Image Pairs using Image Retrieval System - Batch Optimized

This script:
1. Scans the fake image directory structure
2. Extracts features for batches of fake images using PyTorch DataLoader
3. Uses FAISS index with multi-threaded search to find similar real images
4. Creates a mirrored directory structure with symlinks to matched real images
5. Records pairing metadata
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
from src.search import SearchEngine
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
    
    def mark_processed(self, image_path: str):
        """Mark image as successfully processed."""
        if image_path not in self.checkpoint_data["processed_images"]:
            self.checkpoint_data["processed_images"].append(image_path)
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
    """Scan fake directory and organize by model subdirectories."""
    model_images = {}
    
    fake_path = Path(fake_root)
    if not fake_path.exists():
        raise ValueError(f"Fake directory not found: {fake_root}")
    
    images_in_root = [
        str(f) for f in fake_path.glob('*') 
        if f.is_file() and is_valid_image(str(f))
    ]
    
    subdirs = [d for d in fake_path.iterdir() if d.is_dir()]
    
    if images_in_root and not subdirs:
        model_images['root'] = sorted(images_in_root)
        print(f"Found {len(images_in_root)} images in root directory")
    else:
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
    """Create mirrored directory structure in output."""
    fake_path_obj = Path(fake_path)
    fake_root_obj = Path(fake_root)
    
    if model_name == 'root':
        relative_path = fake_path_obj.parent.relative_to(fake_root_obj)
    else:
        model_root = fake_root_obj / model_name
        try:
            relative_path = fake_path_obj.parent.relative_to(model_root)
        except ValueError:
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
    clean: bool = False,
    batch_size: int = 128,
    num_threads: int = 8
):
    """
    Main function to build fake-real image pairs using batch processing.
    
    Args:
        fake_root: Root directory containing fake images
        output_root: Output directory for paired real images
        top_k: Number of top candidates to consider for matching
        verbose: Print progress information
        resume: Resume from previous checkpoint
        clean: Clear previous checkpoint and start fresh
        batch_size: Batch size for feature extraction
        num_threads: Number of threads for FAISS search
    """
    
    print("="*70)
    print("Building Fake-Real Image Pairs (Batch Optimized)")
    print("="*70)
    
    fake_root = os.path.abspath(fake_root)
    
    if output_root is None:
        fake_parent = os.path.dirname(fake_root)
        fake_name = os.path.basename(fake_root)
        output_root = os.path.join(fake_parent, f"{fake_name}_paired_real")
    
    output_root = os.path.abspath(output_root)
    
    print(f"\nInput (fake images):  {fake_root}")
    print(f"Output (paired real): {output_root}")
    print(f"Batch size:           {batch_size}")
    print(f"Search threads:       {num_threads}")
    
    os.makedirs(output_root, exist_ok=True)
    
    checkpoint_mgr = CheckpointManager(output_root)
    
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
    
    print("\n[Step 1] Scanning fake image directory...")
    model_images = scan_fake_directory(fake_root)
    total_fake_images = sum(len(images) for images in model_images.values())
    print(f"Total fake images found: {total_fake_images}")
    
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
    
    print("\n[Step 3] Processing fake images in batches...")
    
    pairing_data = {
        "fake_root": fake_root,
        "output_root": output_root,
        "total_fake_images": total_fake_images,
        "pairs": []
    }
    
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
    start_time = time.time()
    
    for model_name in sorted(model_images.keys()):
        images = model_images[model_name]
        print(f"\n  Processing model '{model_name}' ({len(images)} images)...")
        
        # Get unprocessed images
        unprocessed_images = [img for img in images if not checkpoint_mgr.is_processed(img)]
        
        if not unprocessed_images:
            print(f"    ⊘ All {len(images)} images already processed")
            continue
        
        # Process in batches
        for batch_start in range(0, len(unprocessed_images), batch_size):
            batch_end = min(batch_start + batch_size, len(unprocessed_images))
            batch_images = unprocessed_images[batch_start:batch_end]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(unprocessed_images) + batch_size - 1) // batch_size
            
            print(f"    Batch {batch_num}/{total_batches}: Processing {len(batch_images)} images...")
            
            # Search for matches using batch processing
            search_results = search_engine.search_batch(
                batch_images, 
                k=top_k, 
                batch_size=batch_size,
                num_threads=num_threads
            )
            
            # Process results
            for fake_image_path in batch_images:
                if fake_image_path not in search_results:
                    failed_count += 1
                    checkpoint_mgr.mark_failed(fake_image_path)
                    continue
                
                results = search_results[fake_image_path]
                
                if not results:
                    failed_count += 1
                    checkpoint_mgr.mark_failed(fake_image_path)
                    continue
                
                try:
                    # Get best match
                    best_real_path, similarity_score = results[0]
                    
                    # Create output directory
                    output_dir = create_mirror_directory(fake_root, output_root, model_name, fake_image_path)
                    fake_filename = os.path.basename(fake_image_path)
                    symlink_path = os.path.join(output_dir, fake_filename)
                    
                    # Remove existing symlink if it exists
                    if os.path.lexists(symlink_path):
                        os.remove(symlink_path)
                    
                    # Create symlink
                    real_abs_path = os.path.abspath(best_real_path)
                    os.symlink(real_abs_path, symlink_path)
                    symlink_count += 1
                    
                    # Record pairing
                    pair_info = {
                        "fake_image": fake_image_path,
                        "fake_filename": fake_filename,
                        "fake_directory": output_dir,
                        "matched_real_image": best_real_path,
                        "matched_real_filename": os.path.basename(best_real_path),
                        "symlink_path": symlink_path,
                        "similarity_score": float(similarity_score),
                        "model": model_name,
                        "rank": 1
                    }
                    pairing_data["pairs"].append(pair_info)
                    processed_count += 1
                    checkpoint_mgr.mark_processed(fake_image_path)
                    
                except Exception as e:
                    print(f"      Error processing {fake_filename}: {str(e)}")
                    failed_count += 1
                    checkpoint_mgr.mark_failed(fake_image_path)
            
            # Save checkpoint after each batch
            checkpoint_mgr.save()
            
            # Print progress
            progress = processed_count + failed_count
            elapsed = time.time() - start_time
            pct = (progress / total_fake_images) * 100 if total_fake_images > 0 else 0
            rate = progress / elapsed if elapsed > 0 else 0
            remaining_sec = (total_fake_images - progress) / rate if rate > 0 else 0
            remaining_min = remaining_sec / 60
            
            print(f"    ✓ Progress: {progress}/{total_fake_images} ({pct:.1f}%) - ~{remaining_min:.0f}min remaining")
    
    # Final checkpoint save
    checkpoint_mgr.save()
    
    # Step 4: Save metadata
    print("\n[Step 4] Saving pairing metadata...")
    
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
    
    elapsed_total = time.time() - start_time
    print(f"Total time:           {elapsed_total/60:.1f} minutes")
    print("="*70 + "\n")
    
    return pairing_data


def main():
    """Command-line interface for building fake-real pairs."""
    parser = argparse.ArgumentParser(
        description="Build fake-real image pairs using FAISS retrieval system (Batch Optimized)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_fake_real_pairs.py /path/to/fake/images
  python build_fake_real_pairs.py /path/to/fake/images --output /path/to/output --batch-size 256
  python build_fake_real_pairs.py /path/to/fake/images --resume --threads 16
        """
    )
    
    parser.add_argument(
        "fake_root",
        help="Root directory containing fake images"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output directory for paired real images"
    )
    
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=10,
        help="Number of top candidates to consider (default: 10)"
    )
    
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=128,
        help="Batch size for feature extraction (default: 128)"
    )
    
    parser.add_argument(
        "--threads", "-t",
        type=int,
        default=8,
        help="Number of threads for FAISS search (default: 8)"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress detailed progress output"
    )
    
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous checkpoint"
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
            clean=args.clean,
            batch_size=args.batch_size,
            num_threads=args.threads
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
