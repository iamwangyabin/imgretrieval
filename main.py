import argparse
import sys
from src.database import init_db, get_stats
from src.scanner import scan_directory
from src.processor import process_images
from src.search import SearchEngine

def main():
    parser = argparse.ArgumentParser(description="Local Image Retrieval System CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Init command
    parser_init = subparsers.add_parser("init", help="Initialize database")
    
    # Scan command
    parser_scan = subparsers.add_parser("scan", help="Scan directory for images")
    parser_scan.add_argument("path", help="Root directory to scan")
    
    # Process command
    parser_process = subparsers.add_parser("process", help="Process pending images (extract features)")
    
    # Build-index command
    parser_build = subparsers.add_parser("build-index", help="Build FAISS search index from database")
    
    # Search command
    parser_search = subparsers.add_parser("search", help="Search for similar images")
    parser_search.add_argument("query", help="Path to query image")
    parser_search.add_argument("--top-k", type=int, default=10, help="Number of results to return (default: 10)")
    
    # Stats command
    parser_stats = subparsers.add_parser("stats", help="Show system statistics")
    
    args = parser.parse_args()
    
    if args.command == "init":
        init_db()
        print("Database initialized.")
        
    elif args.command == "scan":
        init_db() # Ensure DB exists
        scan_directory(args.path)
        
    elif args.command == "process":
        process_images()
        
    elif args.command == "build-index":
        engine = SearchEngine()
        if engine.build_index():
            engine.save_index()
            print("FAISS index built and saved successfully.")
        else:
            print("Failed to build index.")
            
    elif args.command == "search":
        import os
        if not os.path.exists(args.query):
            print(f"Error: Query image not found: {args.query}")
            return
            
        engine = SearchEngine()
        if engine.index is None:
            print("Error: Index not loaded. Please run 'build-index' first.")
            return
            
        results = engine.search(args.query, k=args.top_k)
        
        if not results:
            print("No results found.")
        else:
            print(f"\nTop {len(results)} similar images:")
            print("-" * 80)
            for i, (path, score) in enumerate(results, 1):
                print(f"{i}. Score: {score:.4f} - {path}")
        
    elif args.command == "stats":
        import os
        import numpy as np
        from src.config import DB_PATH
        from src.database import get_connection
        
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
        except Exception as e:
            if "no such table" in str(e):
                print(f"\n[Error] Database tables not initialized: {e}")
                print("Tip: Run 'python main.py init' to create tables.")
                return
            else:
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
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
