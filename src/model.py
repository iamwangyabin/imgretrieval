import torch
import timm
from torch.utils.data import Dataset, DataLoader
from timm.data import resolve_data_config
from timm.data.transforms_factory import create_transform
from PIL import Image
import numpy as np
from src.config import MODEL_NAME, BATCH_SIZE


class ImageDataset(Dataset):
    """PyTorch Dataset for loading images."""
    
    def __init__(self, image_paths, transform):
        self.image_paths = image_paths
        self.transform = transform
        self.valid_indices = []
        self.processed_paths = []
        
        # Pre-validate images
        for i, path in enumerate(image_paths):
            try:
                img = Image.open(path).convert('RGB')
                self.valid_indices.append(i)
                self.processed_paths.append(path)
            except Exception as e:
                pass
    
    def __len__(self):
        return len(self.valid_indices)
    
    def __getitem__(self, idx):
        original_idx = self.valid_indices[idx]
        path = self.image_paths[original_idx]
        try:
            img = Image.open(path).convert('RGB')
            tensor = self.transform(img)
            return tensor, original_idx, path
        except Exception as e:
            return None, original_idx, path


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

    def extract_batch(self, image_paths, batch_size=None):
        """
        Extract features for a large batch of images using DataLoader.
        More efficient than extract() for large batches.
        
        Returns:
            results: list of tuples (image_path, feature_vector)
        """
        if batch_size is None:
            batch_size = BATCH_SIZE
        
        dataset = ImageDataset(image_paths, self.transform)
        
        if len(dataset) == 0:
            return []
        
        # Use multiple workers for faster data loading
        num_workers = 4 if self.device.type == 'cuda' else 2
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=True if self.device.type == 'cuda' else False
        )
        
        results = []
        
        with torch.no_grad():
            for batch_tensors, indices, paths in dataloader:
                # Filter out None values
                valid_mask = [t is not None for t in batch_tensors]
                valid_indices = [i for i, valid in enumerate(valid_mask) if valid]
                valid_paths = [p for p, valid in zip(paths, valid_mask) if valid]

                batch = batch_tensors.to(self.device)
                features = self.model(batch)
                features = torch.nn.functional.normalize(features, p=2, dim=1)
                features_np = features.cpu().numpy()
                
                for path, feature in zip(valid_paths, features_np):
                    results.append((path, feature))
        
        return results
