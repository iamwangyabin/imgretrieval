
import os
import numpy as np
import faiss
from .config import FEATURE_DIM
from .database import get_all_features
from .model import FeatureExtractor

class SearchEngine:
    def __init__(self):
        self.index = None
        self.paths = []
        self.extractor = None # Lazy load
        self.load_index()

    def load_index(self):
        """Load features from database and build FAISS index."""
        print("Loading features from database...")
        self.paths, vectors = get_all_features()
        
        if not self.paths:
            print("No features found in DB.")
            return

        # Convert list of bytes to numpy array
        # Each vector is FEATURE_DIM float32s
        # We can use np.frombuffer for each and stack, or join bytes and frombuffer
        
        # More efficient: join all bytes then frombuffer
        all_bytes = b''.join(vectors)
        self.features = np.frombuffer(all_bytes, dtype='float32').reshape(len(self.paths), FEATURE_DIM)

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
