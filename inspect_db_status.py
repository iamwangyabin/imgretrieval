import sqlite3
import numpy as np
import os
import sys

# Add src to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import DB_PATH
from src.database import get_connection, get_stats

def inspect_db_status():
    print("=== Database Status Inspection ===")
    
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at {DB_PATH}")
        return
        
    db_size = os.path.getsize(DB_PATH)
    print(f"Database file: {DB_PATH}")
    print(f"File size: {db_size / 1024 / 1024:.2f} MB")

    # 1. Check Database Statistics
    try:
        stats = get_stats()
        total_images = sum(stats.values())
        print(f"\n[Statistics]")
        print(f"Total Images: {total_images}")
        print(f"  - Pending (0):   {stats.get(0, 0)}")
        print(f"  - Processed (1): {stats.get(1, 0)}")
        print(f"  - Failed (2):    {stats.get(2, 0)}")
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            print(f"\n[Error] Database tables not initialized: {e}")
            print("Tip: Run the application initialization to create tables.")
            return
        else:
            print(f"Error getting stats: {e}")
            return
    except Exception as e:
        print(f"Error getting stats: {e}")
        return

    # 2. Sample a Feature Vector
    print(f"\n[Feature Sample]")
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get one random feature
        cursor.execute("""
            SELECT i.id, i.path, f.vector 
            FROM features f 
            JOIN images i ON f.image_id = i.id 
            ORDER BY RANDOM() 
            LIMIT 1
        """)
        row = cursor.fetchone()
        
        if not row:
            print("No features found in the database.")
            return
            
        image_id, path, vector_blob = row
        print(f"Sampled Image ID: {image_id}")
        print(f"Path: {path}")
        print(f"Blob size: {len(vector_blob)} bytes")
        
        # Deserialize
        vector = np.frombuffer(vector_blob, dtype=np.float32)
        
        print(f"Vector shape: {vector.shape}")
        print(f"Vector dtype: {vector.dtype}")
        print("-" * 20)
        print("First 20 elements:")
        print(vector[:20])
        print("-" * 20)
        print(f"Min: {vector.min():.6f}, Max: {vector.max():.6f}, Mean: {vector.mean():.6f}")
        
        # Check for NaNs or Infs
        if np.isnan(vector).any():
            print("WARNING: Vector contains NaNs!")
        if np.isinf(vector).any():
            print("WARNING: Vector contains Infs!")
            
    except Exception as e:
        print(f"Error sampling feature: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_db_status()
