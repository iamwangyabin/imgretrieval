#!/usr/bin/env python3
"""
Simple test script to verify that the refactored feature extraction works.
"""
import sys
import os

# Add parent directory to path so we can import src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model import FeatureExtractor
from src.config import FEATURE_DIM
import numpy as np

def test_feature_extraction():
    print("=" * 60)
    print("Testing Feature Extraction with timm")
    print("=" * 60)
    
    # Initialize the feature extractor
    print("\n1. Initializing FeatureExtractor...")
    try:
        extractor = FeatureExtractor()
        print("✓ FeatureExtractor initialized successfully!")
    except Exception as e:
        print(f"✗ Failed to initialize FeatureExtractor: {e}")
        return False
    
    # Test with a dummy image (we'll create one if no test images exist)
    print("\n2. Testing feature extraction...")
    
    # Create a temporary test image
    from PIL import Image
    import tempfile
    
    # Create a simple RGB test image
    test_img = Image.new('RGB', (224, 224), color='red')
    
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        temp_path = f.name
        test_img.save(temp_path)
    
    try:
        # Extract features
        features, valid_indices = extractor.extract([temp_path])
        
        if features is None:
            print("✗ Feature extraction failed!")
            return False
        
        print(f"✓ Feature extraction successful!")
        print(f"  - Feature shape: {features.shape}")
        print(f"  - Expected shape: (1, {FEATURE_DIM})")
        print(f"  - Valid indices: {valid_indices}")
        
        # Verify shape
        if features.shape == (1, FEATURE_DIM):
            print("✓ Feature dimensions match expected output!")
        else:
            print(f"✗ Feature dimensions mismatch! Expected (1, {FEATURE_DIM}), got {features.shape}")
            return False
        
        # Verify normalization (L2 norm should be ~1.0)
        norm = np.linalg.norm(features[0])
        print(f"  - L2 norm: {norm:.6f} (should be ~1.0)")
        
        if abs(norm - 1.0) < 0.01:
            print("✓ Features are properly normalized!")
        else:
            print(f"⚠ Features might not be normalized (norm: {norm})")
        
        # Test batch processing
        print("\n3. Testing batch processing...")
        features_batch, valid_indices_batch = extractor.extract([temp_path, temp_path, temp_path])
        
        if features_batch is not None and features_batch.shape == (3, FEATURE_DIM):
            print(f"✓ Batch processing works! Shape: {features_batch.shape}")
        else:
            print(f"✗ Batch processing failed!")
            return False
            
    finally:
        # Clean up temp file
        os.unlink(temp_path)
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_feature_extraction()
    sys.exit(0 if success else 1)
