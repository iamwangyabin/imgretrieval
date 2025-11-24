import torch
import timm
from timm.data import resolve_data_config
from timm.data.transforms_factory import create_transform
from PIL import Image
from .config import MODEL_NAME

class FeatureExtractor:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Loading model {MODEL_NAME} on {self.device}...")
        
        # Load model using timm
        self.model = timm.create_model(MODEL_NAME, pretrained=True, num_classes=0)
        self.model.to(self.device)
        self.model.eval()

        if torch.cuda.device_count() > 1:
            print(f"Using {torch.cuda.device_count()} GPUs!")
            self.model = torch.nn.DataParallel(self.model)
        
        # Get data config and create transform using timm's built-in configuration
        config = resolve_data_config({}, model=self.model)
        self.transform = create_transform(**config)

    def preprocess(self, image_path):
        try:
            img = Image.open(image_path).convert('RGB')
            return self.transform(img)
        except Exception as e:
            print(f"Error reading {image_path}: {e}")
            return None

    def extract(self, image_paths):
        """
        Extract features for a batch of images.
        Returns:
            features: numpy array of shape (batch_size, feature_dim)
            valid_indices: list of indices in the input list that were successfully processed
        """
        tensors = []
        valid_indices = []
        
        for i, path in enumerate(image_paths):
            tensor = self.preprocess(path)
            if tensor is not None:
                tensors.append(tensor)
                valid_indices.append(i)
        
        if not tensors:
            return None, []
            
        batch = torch.stack(tensors).to(self.device)
        
        with torch.no_grad():
            features = self.model(batch)
            # L2 Normalize
            features = torch.nn.functional.normalize(features, p=2, dim=1)
            
        return features.cpu().numpy(), valid_indices
