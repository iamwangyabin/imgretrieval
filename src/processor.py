import os
import numpy as np
from .config import BATCH_SIZE
from .database import get_pending_images, mark_as_processed, mark_as_failed, save_feature_batch
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
        features_data = [] # List of (id, bytes)
        
        # Map back to original IDs
        # valid_indices contains indices in the 'paths' list that succeeded
        valid_set = set(valid_indices)
        
        # features is a numpy array of shape (num_valid, feature_dim)
        # We need to map the j-th valid feature to the correct ID
        feature_idx = 0
        
        for i in range(len(ids)):
            if i in valid_set:
                successful_ids.append(ids[i])
                # Get the corresponding feature vector
                vector = features[feature_idx]
                features_data.append((ids[i], vector.tobytes()))
                feature_idx += 1
            else:
                failed_ids.append(ids[i])
        
        # Save features to DB
        if features_data:
            save_feature_batch(features_data)
            
        # Update database status
        if successful_ids:
            mark_as_processed(successful_ids)
        
        if failed_ids:
            for i in failed_ids:
                mark_as_failed(i)
                
        print(f"Batch complete. {len(successful_ids)} succeeded, {len(failed_ids)} failed.")
