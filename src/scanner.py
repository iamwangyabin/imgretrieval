import os
from .database import insert_image

VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}

def scan_directory(root_dir: str):
    """
    Recursively scan directory and add new images to the database.
    Returns the number of new images added.
    """
    new_count = 0
    print(f"Scanning {root_dir}...")
    
    for root, _, files in os.walk(root_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in VALID_EXTENSIONS:
                full_path = os.path.join(root, file)
                if insert_image(full_path):
                    new_count += 1
                    if new_count % 1000 == 0:
                        print(f"Found {new_count} new images...")
    
    print(f"Scan complete. Added {new_count} new images.")
    return new_count
