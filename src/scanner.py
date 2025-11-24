import os
from .database import insert_images_batch

VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
BATCH_SIZE = 1000

def scan_directory(root_dir: str):
    """
    Recursively scan directory and add new images to the database.
    Returns the number of new images added.
    """
    new_count = 0
    batch = []
    print(f"Scanning {root_dir}...")
    
    for root, _, files in os.walk(root_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in VALID_EXTENSIONS:
                full_path = os.path.join(root, file)
                batch.append(full_path)
                
                # Insert batch when it reaches BATCH_SIZE
                if len(batch) >= BATCH_SIZE:
                    inserted = insert_images_batch(batch)
                    new_count += inserted
                    print(f"Processed {new_count} new images...")
                    batch = []
    
    # Insert remaining images
    if batch:
        inserted = insert_images_batch(batch)
        new_count += inserted
    
    print(f"Scan complete. Added {new_count} new images.")
    return new_count
