"""
Model Initializer for CALES Entity Extraction Service

This module handles the initialization and downloading of base models from HuggingFace,
manages GPU allocation, and provides fallback mechanisms for fine-tuned models.
"""

import os
import json
import shutil
import logging
import torch
import yaml
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib
import requests
from tqdm import tqdm
from transformers import (
    AutoModel,
    AutoTokenizer,
    AutoModelForTokenClassification,
    BertForTokenClassification,
    RobertaForTokenClassification,
    LongformerForTokenClassification,
    DebertaV2ForTokenClassification,
    pipeline
)
import spacy
from spacy.cli import download as spacy_download

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Model information dataclass"""
    model_id: str
    huggingface_id: str
    architecture: str
    description: str
    entity_types: List[str]
    max_sequence_length: int
    embedding_dim: int
    download_url: str
    size_mb: int
    local_path: Optional[str] = None
    downloaded: bool = False
    download_date: Optional[str] = None
    checksum: Optional[str] = None
    gpu_allocation: Optional[int] = None
    status: str = "not_initialized"


class ModelInitializer:
    """
    Handles initialization and downloading of base models from HuggingFace.
    Manages GPU allocation and provides fallback mechanisms.
    """
    
    # Architecture mapping for model classes
    ARCHITECTURE_MAP = {
        "BertForTokenClassification": BertForTokenClassification,
        "RobertaForTokenClassification": RobertaForTokenClassification,
        "LongformerForTokenClassification": LongformerForTokenClassification,
        "DebertaV2ForTokenClassification": DebertaV2ForTokenClassification,
        "AutoModelForTokenClassification": AutoModelForTokenClassification
    }
    
    def __init__(self, config_path: str = "/srv/luris/be/entity-extraction-service/config/models_config.yaml"):
        """
        Initialize the ModelInitializer with configuration.
        
        Args:
            config_path: Path to the models configuration YAML file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.base_path = Path(self.config['model_repository']['base_path'])
        self.models_info: Dict[str, ModelInfo] = {}
        self.gpu_assignments = {0: [], 1: []}  # Track GPU assignments
        self.device_count = torch.cuda.device_count()
        
        # Create directory structure
        self._create_directory_structure()
        
        # Load model information
        self._load_model_info()
        
        # Check CUDA availability
        self.cuda_available = torch.cuda.is_available()
        if self.cuda_available:
            logger.info(f"CUDA is available with {self.device_count} GPU(s)")
            for i in range(self.device_count):
                props = torch.cuda.get_device_properties(i)
                logger.info(f"GPU {i}: {props.name} - Memory: {props.total_memory / 1024**3:.2f} GB")
        else:
            logger.warning("CUDA not available. Models will run on CPU.")
    
    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _create_directory_structure(self):
        """Create the necessary directory structure for models"""
        structure = self.config['model_repository']['structure']
        
        for category, subdir in structure.items():
            dir_path = self.base_path / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created/verified directory: {dir_path}")
    
    def _load_model_info(self):
        """Load model information from configuration"""
        base_models = self.config['available_models']['base_models']
        
        for model_name, model_config in base_models.items():
            model_info = ModelInfo(
                model_id=model_config['model_id'],
                huggingface_id=model_config['huggingface_id'],
                architecture=model_config['architecture'],
                description=model_config['description'],
                entity_types=model_config['entity_types'],
                max_sequence_length=model_config['max_sequence_length'],
                embedding_dim=model_config['embedding_dim'],
                download_url=model_config['download_url'],
                size_mb=model_config['size_mb']
            )
            self.models_info[model_name] = model_info
    
    def initialize_base_models(self, models_to_init: Optional[List[str]] = None, 
                              force_download: bool = False) -> Dict[str, bool]:
        """
        Initialize and download base models from HuggingFace.
        
        Args:
            models_to_init: List of model names to initialize. If None, initialize all.
            force_download: Force re-download even if model exists locally
            
        Returns:
            Dictionary mapping model names to initialization success status
        """
        if models_to_init is None:
            models_to_init = list(self.models_info.keys())
        
        results = {}
        
        for model_name in models_to_init:
            if model_name not in self.models_info:
                logger.error(f"Model {model_name} not found in configuration")
                results[model_name] = False
                continue
            
            try:
                success = self._initialize_model(model_name, force_download)
                results[model_name] = success
            except Exception as e:
                logger.error(f"Failed to initialize {model_name}: {e}")
                results[model_name] = False
        
        return results
    
    def _initialize_model(self, model_name: str, force_download: bool = False) -> bool:
        """
        Initialize a single model.
        
        Args:
            model_name: Name of the model to initialize
            force_download: Force re-download even if exists
            
        Returns:
            True if successful, False otherwise
        """
        model_info = self.models_info[model_name]
        model_path = self.base_path / "base" / model_name
        
        # Check if model already exists
        if model_path.exists() and not force_download:
            if self._verify_model_integrity(model_path, model_info):
                logger.info(f"Model {model_name} already exists and is valid")
                model_info.local_path = str(model_path)
                model_info.downloaded = True
                model_info.status = "ready"
                return True
            else:
                logger.warning(f"Model {model_name} exists but integrity check failed. Re-downloading...")
        
        # Special handling for SpaCy models
        if model_info.architecture == "SpacyTransformer":
            return self._initialize_spacy_model(model_name, model_info, model_path)
        
        # Download transformer models
        return self._download_transformer_model(model_name, model_info, model_path)
    
    def _download_transformer_model(self, model_name: str, model_info: ModelInfo, 
                                   model_path: Path) -> bool:
        """
        Download a transformer model from HuggingFace.
        
        Args:
            model_name: Name of the model
            model_info: ModelInfo object
            model_path: Local path to save the model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading {model_name} from HuggingFace...")
            
            # Create model directory
            model_path.mkdir(parents=True, exist_ok=True)
            
            # Determine model class
            if model_info.architecture in self.ARCHITECTURE_MAP:
                model_class = self.ARCHITECTURE_MAP[model_info.architecture]
            else:
                model_class = AutoModelForTokenClassification
            
            # Download tokenizer
            logger.info(f"Downloading tokenizer for {model_info.huggingface_id}")
            tokenizer = AutoTokenizer.from_pretrained(
                model_info.huggingface_id,
                cache_dir=str(model_path / "cache"),
                force_download=True
            )
            tokenizer.save_pretrained(str(model_path / "tokenizer"))
            
            # Download model
            logger.info(f"Downloading model weights for {model_info.huggingface_id}")
            
            # Allocate GPU
            device = self._allocate_gpu(model_info)
            
            if model_info.entity_types:  # Model is already fine-tuned for NER
                model = model_class.from_pretrained(
                    model_info.huggingface_id,
                    cache_dir=str(model_path / "cache"),
                    force_download=True
                )
            else:  # Base model needs configuration for NER
                # For base models without NER, we'll need to add a classification head later
                model = AutoModel.from_pretrained(
                    model_info.huggingface_id,
                    cache_dir=str(model_path / "cache"),
                    force_download=True
                )
            
            # Save model
            model.save_pretrained(str(model_path / "model"))
            
            # Save metadata
            self._save_model_metadata(model_path, model_info)
            
            # Update model info
            model_info.local_path = str(model_path)
            model_info.downloaded = True
            model_info.download_date = datetime.now().isoformat()
            model_info.status = "ready"
            model_info.gpu_allocation = device if device != 'cpu' else None
            
            # Calculate checksum
            model_info.checksum = self._calculate_checksum(model_path)
            
            logger.info(f"Successfully downloaded {model_name} to {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {model_name}: {e}")
            # Clean up partial download
            if model_path.exists():
                shutil.rmtree(model_path)
            return False
    
    def _initialize_spacy_model(self, model_name: str, model_info: ModelInfo, 
                               model_path: Path) -> bool:
        """
        Initialize a SpaCy model.
        
        Args:
            model_name: Name of the model
            model_info: ModelInfo object
            model_path: Local path to save the model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Initializing SpaCy model {model_name}...")
            
            # Create model directory
            model_path.mkdir(parents=True, exist_ok=True)
            
            # Check if Blackstone is needed (for legal SpaCy models)
            if "legal" in model_name.lower():
                try:
                    import pip
                    pip.main(['install', 'blackstone'])
                    logger.info("Installed Blackstone for legal NER")
                except Exception as e:
                    logger.warning(f"Could not install Blackstone: {e}")
            
            # Download SpaCy model
            model_name_spacy = model_info.huggingface_id.split('/')[-1]
            
            # Try to download the model
            try:
                spacy_download(model_name_spacy)
                logger.info(f"Downloaded SpaCy model: {model_name_spacy}")
            except Exception:
                # Fallback to standard English model if specific model not available
                logger.warning(f"Could not download {model_name_spacy}, using en_core_web_trf")
                spacy_download("en_core_web_trf")
                model_name_spacy = "en_core_web_trf"
            
            # Load and save the model
            nlp = spacy.load(model_name_spacy)
            nlp.to_disk(model_path / "spacy_model")
            
            # Save metadata
            self._save_model_metadata(model_path, model_info)
            
            # Update model info
            model_info.local_path = str(model_path)
            model_info.downloaded = True
            model_info.download_date = datetime.now().isoformat()
            model_info.status = "ready"
            
            logger.info(f"Successfully initialized SpaCy model {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SpaCy model {model_name}: {e}")
            return False
    
    def _allocate_gpu(self, model_info: ModelInfo) -> int:
        """
        Intelligently allocate GPU for a model based on size and current allocations.
        
        Args:
            model_info: ModelInfo object
            
        Returns:
            GPU device index or 'cpu' if no GPU available
        """
        if not self.cuda_available:
            return 'cpu'
        
        # Estimate GPU memory required (rough estimate)
        estimated_memory_gb = model_info.size_mb / 1024 * 2  # Factor of 2 for runtime overhead
        
        # Try to balance load across GPUs
        best_gpu = None
        min_load = float('inf')
        
        for gpu_idx in range(min(2, self.device_count)):  # Use GPU 0 and 1
            # Get current GPU memory usage
            try:
                props = torch.cuda.get_device_properties(gpu_idx)
                total_memory = props.total_memory / 1024**3
                
                # Calculate current load (number of models on this GPU)
                current_load = len(self.gpu_assignments[gpu_idx])
                
                # Simple heuristic: prefer GPU with fewer models
                if current_load < min_load:
                    min_load = current_load
                    best_gpu = gpu_idx
                    
            except Exception as e:
                logger.warning(f"Could not check GPU {gpu_idx}: {e}")
        
        if best_gpu is not None:
            self.gpu_assignments[best_gpu].append(model_info.model_id)
            logger.info(f"Allocated GPU {best_gpu} for {model_info.model_id}")
            return best_gpu
        
        return 'cpu'
    
    def _save_model_metadata(self, model_path: Path, model_info: ModelInfo):
        """Save model metadata to JSON file"""
        metadata_path = model_path / "metadata.json"
        metadata = asdict(model_info)
        metadata['initialization_date'] = datetime.now().isoformat()
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _calculate_checksum(self, model_path: Path) -> str:
        """Calculate SHA256 checksum of model files"""
        sha256_hash = hashlib.sha256()
        
        # Calculate checksum for all model files
        for file_path in model_path.rglob("*.bin"):
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def _verify_model_integrity(self, model_path: Path, model_info: ModelInfo) -> bool:
        """
        Verify the integrity of a downloaded model.
        
        Args:
            model_path: Path to the model directory
            model_info: ModelInfo object
            
        Returns:
            True if model is valid, False otherwise
        """
        # Check if essential files exist
        required_files = []
        
        if model_info.architecture == "SpacyTransformer":
            required_files = [model_path / "spacy_model" / "config.cfg"]
        else:
            required_files = [
                model_path / "model" / "config.json",
                model_path / "tokenizer" / "tokenizer_config.json"
            ]
        
        for file in required_files:
            if not file.exists():
                logger.warning(f"Required file missing: {file}")
                return False
        
        # Check metadata
        metadata_path = model_path / "metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    
                # Verify model ID matches
                if metadata.get('model_id') != model_info.model_id:
                    logger.warning("Model ID mismatch in metadata")
                    return False
                    
            except Exception as e:
                logger.warning(f"Could not read metadata: {e}")
                return False
        
        return True
    
    def check_fine_tuned_models(self) -> Dict[str, List[str]]:
        """
        Check for available fine-tuned model versions.
        
        Returns:
            Dictionary mapping model names to list of available versions
        """
        fine_tuned_path = self.base_path / "fine-tuned"
        available_models = {}
        
        if fine_tuned_path.exists():
            for model_dir in fine_tuned_path.iterdir():
                if model_dir.is_dir():
                    versions = []
                    for version_dir in model_dir.iterdir():
                        if version_dir.is_dir():
                            versions.append(version_dir.name)
                    if versions:
                        available_models[model_dir.name] = sorted(versions)
        
        return available_models
    
    def get_model_status(self) -> Dict[str, Dict]:
        """
        Get the current status of all models.
        
        Returns:
            Dictionary with model status information
        """
        status = {
            "base_models": {},
            "fine_tuned_models": {},
            "gpu_allocations": self.gpu_assignments,
            "cuda_available": self.cuda_available,
            "device_count": self.device_count
        }
        
        # Base models status
        for model_name, model_info in self.models_info.items():
            status["base_models"][model_name] = {
                "downloaded": model_info.downloaded,
                "status": model_info.status,
                "local_path": model_info.local_path,
                "gpu_allocation": model_info.gpu_allocation,
                "size_mb": model_info.size_mb
            }
        
        # Fine-tuned models status
        status["fine_tuned_models"] = self.check_fine_tuned_models()
        
        return status
    
    def cleanup_old_models(self, keep_latest: int = 3):
        """
        Clean up old model versions to save disk space.
        
        Args:
            keep_latest: Number of latest versions to keep for each model
        """
        cleanup_summary = {"deleted": [], "kept": [], "freed_space_mb": 0}
        
        fine_tuned_path = self.base_path / "fine-tuned"
        if not fine_tuned_path.exists():
            return cleanup_summary
        
        for model_dir in fine_tuned_path.iterdir():
            if model_dir.is_dir():
                versions = sorted([v for v in model_dir.iterdir() if v.is_dir()], 
                                key=lambda x: x.stat().st_mtime, reverse=True)
                
                # Keep the latest versions
                for version in versions[keep_latest:]:
                    # Calculate size before deletion
                    size_mb = sum(f.stat().st_size for f in version.rglob('*') if f.is_file()) / 1024 / 1024
                    
                    # Delete the version
                    shutil.rmtree(version)
                    cleanup_summary["deleted"].append(str(version))
                    cleanup_summary["freed_space_mb"] += size_mb
                    logger.info(f"Deleted old version: {version}")
                
                # Track kept versions
                for version in versions[:keep_latest]:
                    cleanup_summary["kept"].append(str(version))
        
        logger.info(f"Cleanup complete. Freed {cleanup_summary['freed_space_mb']:.2f} MB")
        return cleanup_summary
    
    def prepare_for_fine_tuning(self, base_model_name: str, 
                               target_path: Optional[Path] = None) -> Path:
        """
        Prepare a base model for fine-tuning by copying it to a working directory.
        
        Args:
            base_model_name: Name of the base model to prepare
            target_path: Optional target path for the prepared model
            
        Returns:
            Path to the prepared model directory
        """
        if base_model_name not in self.models_info:
            raise ValueError(f"Base model {base_model_name} not found")
        
        model_info = self.models_info[base_model_name]
        
        if not model_info.downloaded:
            raise ValueError(f"Base model {base_model_name} not downloaded. Run initialize_base_models first.")
        
        # Default target path
        if target_path is None:
            target_path = self.base_path / "staging" / f"{base_model_name}_fine_tuning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Copy base model to target
        source_path = Path(model_info.local_path)
        shutil.copytree(source_path, target_path, dirs_exist_ok=True)
        
        logger.info(f"Prepared {base_model_name} for fine-tuning at {target_path}")
        return target_path


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CALES Model Initializer")
    parser.add_argument("--init", action="store_true", help="Initialize all base models")
    parser.add_argument("--models", nargs="+", help="Specific models to initialize")
    parser.add_argument("--status", action="store_true", help="Show model status")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old models")
    parser.add_argument("--force", action="store_true", help="Force re-download")
    
    args = parser.parse_args()
    
    initializer = ModelInitializer()
    
    if args.init:
        results = initializer.initialize_base_models(
            models_to_init=args.models,
            force_download=args.force
        )
        print("Initialization results:")
        for model, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {model}")
    
    if args.status:
        status = initializer.get_model_status()
        print(json.dumps(status, indent=2))
    
    if args.cleanup:
        cleanup_summary = initializer.cleanup_old_models()
        print(f"Cleanup summary: {json.dumps(cleanup_summary, indent=2)}")