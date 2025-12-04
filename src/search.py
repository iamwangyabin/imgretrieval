import os
import pickle
import numpy as np
import faiss
from typing import List, Tuple, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.config import INDEX_PATH, DATA_DIR, FEATURE_DIM
from src.database import get_all_features
from src.model import FeatureExtractor


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
            return []
        
        # Initialize feature extractor if needed
        if self.feature_extractor is None:
            self.feature_extractor = FeatureExtractor()
        
        # Extract feature for query image
        features, valid_indices = self.feature_extractor.extract([query_image_path])
        
        if features is None or len(valid_indices) == 0:
            return []
        
        query_vector = features[0]
        
        # Search using the vector
        return self.search_by_vector(query_vector, k)
    
    def _search_single(self, query_vector: np.ndarray, k: int) -> List[Tuple[str, float]]:
        """Helper method for single search (used by search_batch with threading)."""
        return self.search_by_vector(query_vector, k)
    
    def search_batch(self, image_paths: List[str], k: int = 10, batch_size: int = 128, 
                     num_threads: int = 8) -> Dict[str, List[Tuple[str, float]]]:
        """
        Search for similar images using a batch of query images.
        Uses DataLoader for efficient feature extraction and multi-threading for FAISS search.
        
        Args:
            image_paths: List of image paths to search
            k: Number of results to return per image
            batch_size: Batch size for feature extraction
            num_threads: Number of threads for parallel FAISS search
            
        Returns:
            Dict mapping image_path -> list of (matched_image_path, similarity_score) tuples
        """
        if self.index is None:
            return {}
        
        # Initialize feature extractor if needed
        if self.feature_extractor is None:
            self.feature_extractor = FeatureExtractor()
        
        # Extract features in batches using DataLoader
        print(f"Extracting features for {len(image_paths)} images...")
        extracted_results = self.feature_extractor.extract_batch(image_paths, batch_size=batch_size)
        
        if not extracted_results:
            print("Failed to extract features from any images")
            return {}
        
        print(f"Successfully extracted {len(extracted_results)} features")
        
        # Prepare search tasks
        search_tasks = [(path, feature) for path, feature in extracted_results]
        
        # Use thread pool for parallel FAISS search
        results = {}
        print(f"Searching with {num_threads} threads...")
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # Submit all search tasks
            future_to_path = {
                executor.submit(self._search_single, feature, k): path 
                for path, feature in search_tasks
            }
            
            # Process completed tasks
            completed = 0
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    search_results = future.result()
                    results[path] = search_results
                    completed += 1
                    if completed % 50 == 0:
                        print(f"  Completed {completed}/{len(search_tasks)} searches")
                except Exception as e:
                    print(f"Error searching for {path}: {e}")
                    results[path] = []
        
        print(f"✓ Search complete: {len(results)} results")
        return results
