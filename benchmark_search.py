import sys
import os
import time
import random
import numpy as np
from typing import List, Tuple

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from search import SearchEngine
from database import get_all_processed_paths

def calculate_recall(results: List[Tuple[str, float]], ground_truth: str, k: int) -> bool:
    """Check if ground_truth is in the top-k results."""
    top_k_paths = [r[0] for r in results[:k]]
    return ground_truth in top_k_paths

def benchmark(sample_size: int = 100):
    print("Initializing Search Engine...")
    engine = SearchEngine()
    
    if not engine.index or engine.index.ntotal == 0:
        print("Error: Search index is empty. Please index some images first.")
        return

    print("Fetching all processed image paths...")
    all_paths = get_all_processed_paths()
    
    if not all_paths:
        print("Error: No processed images found in database.")
        return

    # Filter paths that are actually in the index (SearchEngine.paths)
    # The SearchEngine might have a subset if not all were indexed successfully, 
    # but usually they should match if get_all_features was used.
    # Let's use engine.paths to be safe for sampling queries that definitely exist.
    indexed_paths = engine.paths
    if not indexed_paths:
         print("Error: Search engine has no paths loaded.")
         return

    print(f"Total indexed images: {len(indexed_paths)}")
    
    # Sample queries
    num_samples = min(sample_size, len(indexed_paths))
    query_paths = random.sample(indexed_paths, num_samples)
    
    print(f"Running benchmark on {num_samples} queries...")
    
    latencies = []
    recall_1 = 0
    recall_5 = 0
    recall_10 = 0
    
    for i, query_path in enumerate(query_paths):
        start_time = time.time()
        # Search for the query image itself
        # We expect it to be found as the top result (or near top)
        results = engine.search(query_path, k=10)
        end_time = time.time()
        
        latencies.append((end_time - start_time) * 1000) # ms
        
        if calculate_recall(results, query_path, 1):
            recall_1 += 1
        if calculate_recall(results, query_path, 5):
            recall_5 += 1
        if calculate_recall(results, query_path, 10):
            recall_10 += 1
            
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{num_samples} queries...")

    # Calculate metrics
    avg_latency = np.mean(latencies)
    p95_latency = np.percentile(latencies, 95)
    p99_latency = np.percentile(latencies, 99)
    
    r1_score = recall_1 / num_samples
    r5_score = recall_5 / num_samples
    r10_score = recall_10 / num_samples
    
    print("\n" + "="*40)
    print("       BENCHMARK RESULTS       ")
    print("="*40)
    print(f"Total Queries: {num_samples}")
    print("-" * 40)
    print("Latency Metrics (ms):")
    print(f"  Average: {avg_latency:.2f}")
    print(f"  P95:     {p95_latency:.2f}")
    print(f"  P99:     {p99_latency:.2f}")
    print("-" * 40)
    print("Accuracy Metrics:")
    print(f"  Recall@1:  {r1_score:.2%}")
    print(f"  Recall@5:  {r5_score:.2%}")
    print(f"  Recall@10: {r10_score:.2%}")
    print("="*40)

if __name__ == "__main__":
    benchmark()
