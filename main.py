import argparse
import sys
from src.database import init_db, get_stats
from src.scanner import scan_directory
from src.processor import process_images

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
        
    elif args.command == "stats":
        stats = get_stats()
        print("System Statistics (Status: Count):")
        print(stats)
        print("0: Pending, 1: Processed, 2: Failed")
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
