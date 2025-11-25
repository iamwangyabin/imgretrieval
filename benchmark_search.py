import sys
import os
import time
import random
import numpy as np
from typing import List, Tuple

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from search import SearchEngine
from database import get_all_processed_paths

def calculate_recall(results: List[Tuple[str, float]], ground_truth: str, k: int) -> bool:
    """Check if ground_truth is in the top-k results."""
    if not results:
        return False
    top_k_paths = [r[0] for r in results[:k]]
    return ground_truth in top_k_paths

def benchmark(sample_size: int = 100, verbose: bool = True):
    """
    Benchmark the search engine performance.
    
    Args:
        sample_size: Number of queries to test
        verbose: Whether to print progress updates
    
    Returns:
        Dictionary containing benchmark results
    """
    if verbose:
        print("=" * 60)
        print("FAISS Search Engine Benchmark")
        print("=" * 60)
    
    # Initialize search engine
    if verbose:
        print("\n[1/4] Initializing Search Engine...")
    engine = SearchEngine()
    
    if not engine.index or engine.index.ntotal == 0:
        print("Error: Search index is empty. Please run 'python main.py build-index' first.")
        return None

    if verbose:
        print(f"✓ Index loaded: {engine.index.ntotal} vectors")
    
    # Get indexed paths
    indexed_paths = engine.image_paths
    if not indexed_paths:
        print("Error: Search engine has no image paths loaded.")
        return None
    
    if verbose:
        print(f"✓ Image paths loaded: {len(indexed_paths)} images")
    
    # Sample queries
    num_samples = min(sample_size, len(indexed_paths))
    if verbose:
        print(f"\n[2/4] Sampling {num_samples} query images...")
    
    query_paths = random.sample(indexed_paths, num_samples)
    
    # Run benchmark
    if verbose:
        print(f"\n[3/4] Running search benchmark...")
    
    latencies = []
    recall_1 = 0
    recall_5 = 0
    recall_10 = 0
    failed_queries = 0
    
    for i, query_path in enumerate(query_paths):
        # Check if file exists
        if not os.path.exists(query_path):
            if verbose and i < 5:  # Only warn for first few
                print(f"Warning: Query file not found: {query_path}")
            failed_queries += 1
            continue
        
        start_time = time.time()
        try:
            # Search for the query image itself
            # We expect it to be found as the top result
            results = engine.search(query_path, k=10)
            end_time = time.time()
            
            if not results:
                failed_queries += 1
                continue
                
            latencies.append((end_time - start_time) * 1000)  # Convert to ms
            
            # Calculate recall at different k values
            if calculate_recall(results, query_path, 1):
                recall_1 += 1
            if calculate_recall(results, query_path, 5):
                recall_5 += 1
            if calculate_recall(results, query_path, 10):
                recall_10 += 1
                
        except Exception as e:
            if verbose and failed_queries < 5:  # Only print first few errors
                print(f"Error processing query {query_path}: {e}")
            failed_queries += 1
            continue
        
        if verbose and (i + 1) % 20 == 0:
            print(f"  Progress: {i + 1}/{num_samples} queries processed...")
    
    # Calculate metrics
    if verbose:
        print(f"\n[4/4] Calculating metrics...")
    
    successful_queries = num_samples - failed_queries
    
    if successful_queries == 0:
        print("Error: All queries failed. Cannot calculate metrics.")
        return None
    
    avg_latency = np.mean(latencies)
    median_latency = np.median(latencies)
    p95_latency = np.percentile(latencies, 95)
    p99_latency = np.percentile(latencies, 99)
    min_latency = np.min(latencies)
    max_latency = np.max(latencies)
    
    r1_score = recall_1 / successful_queries
    r5_score = recall_5 / successful_queries
    r10_score = recall_10 / successful_queries
    
    results = {
        'total_queries': num_samples,
        'successful_queries': successful_queries,
        'failed_queries': failed_queries,
        'total_indexed': len(indexed_paths),
        'latency': {
            'mean_ms': avg_latency,
            'median_ms': median_latency,
            'p95_ms': p95_latency,
            'p99_ms': p99_latency,
            'min_ms': min_latency,
            'max_ms': max_latency,
        },
        'accuracy': {
            'recall@1': r1_score,
            'recall@5': r5_score,
            'recall@10': r10_score,
        }
    }
    
    # Print results
    print("\n" + "=" * 60)
    print("                  BENCHMARK RESULTS")
    print("=" * 60)
    print(f"\nDataset Info:")
    print(f"  Total Indexed Images:    {len(indexed_paths):,}")
    print(f"  Test Queries:            {num_samples}")
    print(f"  Successful Queries:      {successful_queries}")
    if failed_queries > 0:
        print(f"  Failed Queries:          {failed_queries}")
    
    print(f"\nLatency Metrics (milliseconds):")
    print(f"  Mean:                    {avg_latency:>8.2f} ms")
    print(f"  Median:                  {median_latency:>8.2f} ms")
    print(f"  95th Percentile (P95):   {p95_latency:>8.2f} ms")
    print(f"  99th Percentile (P99):   {p99_latency:>8.2f} ms")
    print(f"  Min:                     {min_latency:>8.2f} ms")
    print(f"  Max:                     {max_latency:>8.2f} ms")
    
    print(f"\nAccuracy Metrics:")
    print(f"  Recall@1:                {r1_score:>8.2%}")
    print(f"  Recall@5:                {r5_score:>8.2%}")
    print(f"  Recall@10:               {r10_score:>8.2%}")
    
    print("\n" + "=" * 60)
    
    # Interpretation
    print("\nInterpretation:")
    if r1_score >= 0.95:
        print("  ✓ Excellent recall - the query image itself is almost always rank #1")
    elif r1_score >= 0.80:
        print("  ✓ Good recall - most query images rank at the top")
    else:
        print("  ⚠ Lower recall - there may be issues with feature extraction or indexing")
    
    if avg_latency < 50:
        print("  ✓ Excellent latency - very fast search")
    elif avg_latency < 200:
        print("  ✓ Good latency - acceptable search speed")
    else:
        print("  ⚠ Higher latency - search may be slow for real-time use")
    
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Benchmark the FAISS search engine")
    parser.add_argument("--samples", type=int, default=100, 
                        help="Number of query samples to test (default: 100)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress progress output")
    
    args = parser.parse_args()
    
    benchmark(sample_size=args.samples, verbose=not args.quiet)
