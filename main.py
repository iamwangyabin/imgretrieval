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
        stats = get_stats()
        print("System Statistics (Status: Count):")
        print(stats)
        print("0: Pending, 1: Processed, 2: Failed")
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
