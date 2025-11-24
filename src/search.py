import os
import numpy as np
import faiss
from .config import FEATURES_PATH, FEATURE_DIM
from .database import get_all_processed_paths
from .model import FeatureExtractor

class SearchEngine:
    def __init__(self):
        self.index = None
        self.paths = []
        self.extractor = None # Lazy load
        self.load_index()

    def load_index(self):
        """Load features from disk and build FAISS index."""
        if not os.path.exists(FEATURES_PATH):
            print("No features file found.")
            return

        # Load paths
        self.paths = get_all_processed_paths()
        num_images = len(self.paths)
        
        if num_images == 0:
            print("No processed images found in DB.")
            return

        # Memory map the features file
        # The file size should be num_images * FEATURE_DIM * 4 bytes (float32)
        expected_size = num_images * FEATURE_DIM * 4
        file_size = os.path.getsize(FEATURES_PATH)
        
        if file_size != expected_size:
            print(f"Warning: File size {file_size} does not match expected size {expected_size}. Index might be out of sync.")
            # In a real system, we might want to truncate or re-process. 
            # For now, we'll try to map as many as we can.
            num_vectors = file_size // (FEATURE_DIM * 4)
            # Adjust paths if necessary
            if num_vectors < num_images:
                self.paths = self.paths[:num_vectors]
            elif num_vectors > num_images:
                 # This shouldn't happen if DB and file are in sync, but if it does, 
                 # we can only search up to what we have paths for.
                 pass

        print(f"Loading {len(self.paths)} vectors from disk...")
        self.features = np.memmap(FEATURES_PATH, dtype='float32', mode='r', shape=(len(self.paths), FEATURE_DIM))

        # Build FAISS index
        # IndexFlatIP is exact search for Inner Product (which is Cosine Similarity for normalized vectors)
        self.index = faiss.IndexFlatIP(FEATURE_DIM)
        self.index.add(self.features)
        print(f"Index built with {self.index.ntotal} vectors.")

    def search(self, query_img, k=10):
        if self.index is None or self.index.ntotal == 0:
            return []
            
        if self.extractor is None:
            self.extractor = FeatureExtractor()

        # Extract feature for query image
        # We can pass the image object directly if we modify FeatureExtractor, 
        # but for now let's assume query_img is a path or we save it temporarily.
        # Actually, Streamlit UploadedFile needs handling.
        # Let's modify FeatureExtractor to accept PIL Image or path.
        
        # For now, let's assume the caller handles saving to temp file or we update FeatureExtractor.
        # Let's update FeatureExtractor to be more flexible in a separate step if needed.
        # But wait, FeatureExtractor.preprocess takes a path. 
        # Let's assume we pass a path for now.
        
        features, _ = self.extractor.extract([query_img])
        
        if features is None:
            return []
            
        D, I = self.index.search(features, k)
        
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx != -1 and idx < len(self.paths):
                results.append((self.paths[idx], float(score)))
                
        return results
