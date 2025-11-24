import os
import numpy as np
from .config import FEATURES_PATH, BATCH_SIZE
from .database import get_pending_images, mark_as_processed, mark_as_failed
from .model import FeatureExtractor

def process_images():
    extractor = FeatureExtractor()
    
    while True:
        # Fetch batch
        rows = get_pending_images(BATCH_SIZE)
        if not rows:
            print("No pending images found.")
            break
            
        ids = [r[0] for r in rows]
        paths = [r[1] for r in rows]
        
        print(f"Processing batch of {len(paths)} images...")
        
        # Extract features
        features, valid_indices = extractor.extract(paths)
        
        if features is None:
            # All failed
            for i in ids:
                mark_as_failed(i)
            continue
            
        # Identify successful and failed IDs
        successful_ids = []
        failed_ids = []
        
        # Map back to original IDs
        # valid_indices contains indices in the 'paths' list that succeeded
        valid_set = set(valid_indices)
        
        for i in range(len(ids)):
            if i in valid_set:
                successful_ids.append(ids[i])
            else:
                failed_ids.append(ids[i])
        
        # Write to binary file
        # Append mode 'ab'
        with open(FEATURES_PATH, 'ab') as f:
            f.write(features.tobytes())
            
        # Update database
        if successful_ids:
            mark_as_processed(successful_ids)
        
        if failed_ids:
            for i in failed_ids:
                mark_as_failed(i)
                
        print(f"Batch complete. {len(successful_ids)} succeeded, {len(failed_ids)} failed.")
