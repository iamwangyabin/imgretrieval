import sqlite3
from typing import List, Tuple
from config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            status INTEGER DEFAULT 0
        )
    """)
    # 0=Pending, 1=Processed, 2=Failed
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS features (
            image_id INTEGER PRIMARY KEY,
            vector BLOB NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(image_id) REFERENCES images(id)
        )
    """)
    
    conn.commit()
    conn.close()

def insert_image(path: str) -> bool:
    """Insert a new image path. Returns True if inserted, False if already exists."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO images (path) VALUES (?)", (path,))
        inserted = cursor.rowcount > 0
        conn.commit()
        return inserted
    finally:
        conn.close()

def insert_images_batch(paths: List[str]) -> int:
    """
    Insert multiple image paths in a single transaction.
    Returns the number of new images inserted.
    """
    if not paths:
        return 0
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.executemany("INSERT OR IGNORE INTO images (path) VALUES (?)", [(p,) for p in paths])
        inserted = cursor.rowcount
        conn.commit()
        return inserted
    finally:
        conn.close()

def get_pending_images(limit: int = 32) -> List[Tuple[int, str]]:
    """Get a batch of pending images (status=0)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, path FROM images WHERE status = 0 ORDER BY id ASC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def mark_as_processed(ids: List[int]):
    """Mark images as processed (status=1)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany("UPDATE images SET status = 1 WHERE id = ?", [(i,) for i in ids])
    conn.commit()
    conn.close()

def mark_as_failed(image_id: int):
    """Mark image as failed (status=2)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE images SET status = 2 WHERE id = ?", (image_id,))
    conn.commit()
    conn.close()

def save_feature_batch(features_data: List[Tuple[int, bytes]]):
    """
    Save a batch of features.
    features_data: List of (image_id, vector_bytes)
    """
    if not features_data:
        return
        
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.executemany("""
            INSERT OR REPLACE INTO features (image_id, vector) 
            VALUES (?, ?)
        """, features_data)
        conn.commit()
    finally:
        conn.close()

def get_all_features() -> Tuple[List[str], List[bytes]]:
    """
    Get all features and their corresponding image paths.
    Returns (paths, vectors_bytes)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Join with images table to get paths, only for valid features
    cursor.execute("""
        SELECT i.path, f.vector 
        FROM features f 
        JOIN images i ON f.image_id = i.id 
        ORDER BY i.id ASC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return [], []
        
    paths = [r[0] for r in rows]
    vectors = [r[1] for r in rows]
    return paths, vectors

def get_all_processed_paths() -> List[str]:
    """Get all processed image paths sorted by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT path FROM images WHERE status = 1 ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_stats():
    """Get database statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) FROM images GROUP BY status")
    rows = cursor.fetchall()
    conn.close()
    return dict(rows)
