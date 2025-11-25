import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "db.sqlite3")
INDEX_PATH = os.path.join(DATA_DIR, "vector.index")


# Model
# Using timm naming convention for DINOv2 base model
MODEL_NAME = "vit_base_patch16_dinov3.lvd1689m"
FEATURE_DIM = 768

# Processing
BATCH_SIZE = 128

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)
