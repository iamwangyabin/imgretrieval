import sqlite3
import numpy as np
import os

DB_PATH = "data/db.sqlite3"

def inspect_vector():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT image_id, vector FROM features LIMIT 1")
        row = cursor.fetchone()
        
        if not row:
            print("No features found in the database.")
            return
            
        image_id, vector_blob = row
        print(f"Found feature for image_id: {image_id}")
        print(f"Blob size: {len(vector_blob)} bytes")
        
        # Deserialize
        vector = np.frombuffer(vector_blob, dtype=np.float32)
        
        print(f"Vector shape: {vector.shape}")
        print(f"Vector dtype: {vector.dtype}")
        print("-" * 20)
        print("First 20 elements:")
        print(vector[:20])
        print("-" * 20)
        print(f"Min: {vector.min()}, Max: {vector.max()}, Mean: {vector.mean()}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_vector()
