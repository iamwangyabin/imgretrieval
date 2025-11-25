import os
import pickle
import numpy as np
import faiss
from typing import List, Tuple, Optional
from .config import INDEX_PATH, DATA_DIR, FEATURE_DIM
from .database import get_all_features
from .model import FeatureExtractor


class SearchEngine:
    """FAISS-based image retrieval search engine."""
    
    def __init__(self):
        """Initialize the search engine. Attempts to load existing index."""
        self.index = None
        self.image_paths = []
        self.feature_extractor = None
        
        # Try to load existing index
        if os.path.exists(INDEX_PATH):
            self.load_index()
    
    def build_index(self):
        """Build FAISS index from database features."""
        print("Loading features from database...")
        paths, vectors_bytes = get_all_features()
        
        if not paths:
            print("No features found in database. Please process images first.")
            return False
        
        print(f"Found {len(paths)} processed images.")
        
        # Convert bytes back to numpy arrays
        vectors = []
        for vec_bytes in vectors_bytes:
            vec = np.frombuffer(vec_bytes, dtype=np.float32)
            vectors.append(vec)
        
        vectors = np.array(vectors, dtype=np.float32)
        
        # Verify dimensions
        if vectors.shape[1] != FEATURE_DIM:
            print(f"Warning: Feature dimension mismatch. Expected {FEATURE_DIM}, got {vectors.shape[1]}")
        
        print(f"Building FAISS index with {len(vectors)} vectors of dimension {vectors.shape[1]}...")
        
        # Create FAISS index
        # Using IndexFlatIP for exact inner product search (equivalent to cosine similarity for normalized vectors)
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)
        
        self.image_paths = paths
        
        print(f"Index built successfully. Total vectors: {self.index.ntotal}")
        return True
    
    def save_index(self):
        """Save FAISS index and image paths to disk."""
        if self.index is None:
            print("No index to save. Build index first.")
            return False
        
        # Save FAISS index
        faiss.write_index(self.index, INDEX_PATH)
        
        # Save image paths mapping
        paths_file = INDEX_PATH + ".paths.pkl"
        with open(paths_file, 'wb') as f:
            pickle.dump(self.image_paths, f)
        
        print(f"Index saved to {INDEX_PATH}")
        print(f"Paths mapping saved to {paths_file}")
        return True
    
    def load_index(self):
        """Load FAISS index and image paths from disk."""
        if not os.path.exists(INDEX_PATH):
            print(f"Index file not found: {INDEX_PATH}")
            return False
        
        paths_file = INDEX_PATH + ".paths.pkl"
        if not os.path.exists(paths_file):
            print(f"Paths mapping file not found: {paths_file}")
            return False
        
        # Load FAISS index
        self.index = faiss.read_index(INDEX_PATH)
        
        # Load image paths
        with open(paths_file, 'rb') as f:
            self.image_paths = pickle.load(f)
        
        print(f"Index loaded successfully. Total vectors: {self.index.ntotal}")
        return True
    
    def search_by_vector(self, query_vector: np.ndarray, k: int = 10) -> List[Tuple[str, float]]:
        """
        Search for similar images using a feature vector.
        
        Args:
            query_vector: Feature vector to search for (must be normalized)
            k: Number of results to return
            
        Returns:
            List of (image_path, similarity_score) tuples, sorted by similarity (highest first)
        """
        if self.index is None:
            print("Index not loaded. Please build or load index first.")
            return []
        
        # Ensure query vector is 2D array with shape (1, feature_dim)
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        
        # Ensure float32 type for FAISS
        query_vector = query_vector.astype(np.float32)
        
        # Search
        k = min(k, self.index.ntotal)  # Don't request more results than we have
        distances, indices = self.index.search(query_vector, k)
        
        # Build results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.image_paths):
                results.append((self.image_paths[idx], float(dist)))
        
        return results
    
    def search(self, query_image_path: str, k: int = 10) -> List[Tuple[str, float]]:
        """
        Search for similar images using a query image.
        
        Args:
            query_image_path: Path to the query image
            k: Number of results to return
            
        Returns:
            List of (image_path, similarity_score) tuples, sorted by similarity (highest first)
        """
        if self.index is None:
            print("Index not loaded. Please build or load index first.")
            return []
        
        # Initialize feature extractor if needed
        if self.feature_extractor is None:
            print("Initializing feature extractor...")
            self.feature_extractor = FeatureExtractor()
        
        # Extract feature for query image
        print(f"Extracting features for query image: {query_image_path}")
        features, valid_indices = self.feature_extractor.extract([query_image_path])
        
        if features is None or len(valid_indices) == 0:
            print(f"Failed to extract features from {query_image_path}")
            return []
        
        query_vector = features[0]
        
        # Search using the vector
        return self.search_by_vector(query_vector, k)
