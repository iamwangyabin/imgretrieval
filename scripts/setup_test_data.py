import os
from PIL import Image
import random

def create_test_images(num_images=10):
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "test_images")
    os.makedirs(base_dir, exist_ok=True)
    
    print(f"Generating {num_images} test images in {base_dir}...")
    
    for i in range(num_images):
        # Generate random color image
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        img = Image.new('RGB', (224, 224), color)
        img.save(os.path.join(base_dir, f"img_{i}.jpg"))
        
    print("Done.")
    return base_dir

if __name__ == "__main__":
    create_test_images()
