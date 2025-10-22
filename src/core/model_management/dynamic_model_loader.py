"""
Dynamic Model Loader for CALES Entity Extraction Service

This module provides intelligent model loading with priority-based selection,
caching, and seamless transition between base and fine-tuned models.
"""

import os
import json
import torch
import logging
import yaml
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import threading
from collections import OrderedDict
import gc

from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    BertForTokenClassification,
    RobertaForTokenClassification,
    LongformerForTokenClassification,
    DebertaV2ForTokenClassification,
    PreTrainedModel,
    PreTrainedTokenizer
)
import spacy
from spacy.language import Language

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelPriority(Enum):
    """Model loading priority levels"""
    SPECIFIC_VERSION = 1      # Highest priority - specific version requested
    DEPLOYED_FINE_TUNED = 2  # Deployed fine-tuned model
    LATEST_FINE_TUNED = 3    # Latest fine-tuned model
    BASE_MODEL = 4            # Lowest priority - base model fallback


@dataclass
class LoadedModel:
    """Container for loaded model information"""
    model: Union[PreTrainedModel, Language]  # Transformer or SpaCy model
    tokenizer: Optional[Union[PreTrainedTokenizer, None]]  # Tokenizer for transformer models
    model_id: str
    version: str
    model_type: str  # 'transformer' or 'spacy'
    priority: ModelPriority
    device: Union[str, int]
    loaded_at: datetime
    last_used: datetime
    usage_count: int = 0
    memory_usage_mb: float = 0.0


class ModelCache:
    """
    Thread-safe LRU cache for loaded models with memory management.
    """
    
    def __init__(self, max_size: int = 5, max_memory_gb: float = 10.0):
        """
        Initialize the model cache.
        
        Args:
            max_size: Maximum number of models to keep in cache
            max_memory_gb: Maximum total memory usage in GB
        """
        self.max_size = max_size
        self.max_memory_gb = max_memory_gb
        self.cache: OrderedDict[str, LoadedModel] = OrderedDict()
        self.lock = threading.RLock()
        self.total_memory_mb = 0.0
    
    def get(self, key: str) -> Optional[LoadedModel]:
        """Get a model from cache and update LRU order"""
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                model = self.cache.pop(key)
                self.cache[key] = model
                model.last_used = datetime.now()
                model.usage_count += 1
                return model
            return None
    
    def put(self, key: str, model: LoadedModel):
        """Add a model to cache with LRU eviction if needed"""
        with self.lock:
            # Check if we need to evict models
            while (len(self.cache) >= self.max_size or 
                   self.total_memory_mb + model.memory_usage_mb > self.max_memory_gb * 1024):
                
                if not self.cache:
                    break
                    
                # Evict least recently used model
                evicted_key, evicted_model = self.cache.popitem(last=False)
                self.total_memory_mb -= evicted_model.memory_usage_mb
                
                # Clean up GPU memory if applicable
                if evicted_model.model_type == 'transformer' and torch.cuda.is_available():
                    del evicted_model.model
                    torch.cuda.empty_cache()
                    gc.collect()
                
                logger.info(f"Evicted model {evicted_key} from cache")
            
            # Add new model
            self.cache[key] = model
            self.total_memory_mb += model.memory_usage_mb
            logger.info(f"Added model {key} to cache. Cache size: {len(self.cache)}, "
                       f"Memory: {self.total_memory_mb:.2f} MB")
    
    def clear(self):
        """Clear all models from cache"""
        with self.lock:
            for model in self.cache.values():
                if model.model_type == 'transformer' and torch.cuda.is_available():
                    del model.model
            
            self.cache.clear()
            self.total_memory_mb = 0.0
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            
            logger.info("Cleared model cache")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self.lock:
            return {
                "cache_size": len(self.cache),
                "max_size": self.max_size,
                "total_memory_mb": self.total_memory_mb,
                "max_memory_mb": self.max_memory_gb * 1024,
                "models": {
                    key: {
                        "model_id": model.model_id,
                        "version": model.version,
                        "usage_count": model.usage_count,
                        "memory_mb": model.memory_usage_mb,
                        "last_used": model.last_used.isoformat()
                    }
                    for key, model in self.cache.items()
                }
            }


class DynamicModelLoader:
    """
    Intelligently loads models with priority-based selection and caching.
    Supports seamless transition from base to fine-tuned models.
    """
    
    # Architecture mapping
    ARCHITECTURE_MAP = {
        "BertForTokenClassification": BertForTokenClassification,
        "RobertaForTokenClassification": RobertaForTokenClassification,
        "LongformerForTokenClassification": LongformerForTokenClassification,
        "DebertaV2ForTokenClassification": DebertaV2ForTokenClassification,
        "AutoModelForTokenClassification": AutoModelForTokenClassification
    }
    
    def __init__(self, 
                 config_path: str = "/srv/luris/be/entity-extraction-service/config/models_config.yaml",
                 cache_size: int = 5,
                 max_memory_gb: float = 10.0):
        """
        Initialize the DynamicModelLoader.
        
        Args:
            config_path: Path to models configuration
            cache_size: Maximum number of models to cache
            max_memory_gb: Maximum memory for cached models
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.base_path = Path(self.config['model_repository']['base_path'])
        self.cache = ModelCache(max_size=cache_size, max_memory_gb=max_memory_gb)
        
        # Track available models
        self.available_models = self._scan_available_models()
        
        # GPU management
        self.cuda_available = torch.cuda.is_available()
        self.device_count = torch.cuda.device_count() if self.cuda_available else 0
        self.gpu_allocations = {i: [] for i in range(self.device_count)}
        
        logger.info(f"DynamicModelLoader initialized. CUDA: {self.cuda_available}, "
                   f"GPUs: {self.device_count}")
    
    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _scan_available_models(self) -> Dict[str, Dict]:
        """
        Scan for all available models (base and fine-tuned).
        
        Returns:
            Dictionary of available models with their metadata
        """
        available = {
            "base": {},
            "fine_tuned": {},
            "deployed": None
        }
        
        # Scan base models
        base_path = self.base_path / "base"
        if base_path.exists():
            for model_dir in base_path.iterdir():
                if model_dir.is_dir():
                    metadata_path = model_dir / "metadata.json"
                    if metadata_path.exists():
                        with open(metadata_path, 'r') as f:
                            available["base"][model_dir.name] = json.load(f)
        
        # Scan fine-tuned models
        fine_tuned_path = self.base_path / "fine-tuned"
        if fine_tuned_path.exists():
            for model_dir in fine_tuned_path.iterdir():
                if model_dir.is_dir():
                    available["fine_tuned"][model_dir.name] = {}
                    for version_dir in sorted(model_dir.iterdir(), reverse=True):
                        if version_dir.is_dir():
                            metadata_path = version_dir / "metadata.json"
                            if metadata_path.exists():
                                with open(metadata_path, 'r') as f:
                                    available["fine_tuned"][model_dir.name][version_dir.name] = json.load(f)
        
        # Check for deployed model
        production_path = self.base_path / "production"
        if production_path.exists():
            for model_dir in production_path.iterdir():
                if model_dir.is_dir():
                    metadata_path = model_dir / "metadata.json"
                    if metadata_path.exists():
                        with open(metadata_path, 'r') as f:
                            available["deployed"] = json.load(f)
                            available["deployed"]["path"] = str(model_dir)
                        break  # Only one deployed model expected
        
        return available
    
    def load_model(self, 
                   model_name: str,
                   version: Optional[str] = None,
                   device: Optional[Union[str, int]] = None,
                   force_reload: bool = False) -> Tuple[Any, Any, Dict]:
        """
        Load a model with intelligent priority-based selection.
        
        Priority order:
        1. Specific version (if provided)
        2. Deployed fine-tuned model
        3. Latest fine-tuned model
        4. Base model
        
        Args:
            model_name: Name of the model to load
            version: Specific version to load (optional)
            device: Device to load model on (optional)
            force_reload: Force reload even if cached
            
        Returns:
            Tuple of (model, tokenizer, metadata)
        """
        # Generate cache key
        cache_key = f"{model_name}_{version or 'latest'}"
        
        # Check cache unless force reload
        if not force_reload:
            cached_model = self.cache.get(cache_key)
            if cached_model:
                logger.info(f"Loaded {cache_key} from cache")
                return (cached_model.model, 
                       cached_model.tokenizer,
                       {"model_id": cached_model.model_id,
                        "version": cached_model.version,
                        "priority": cached_model.priority.name,
                        "device": cached_model.device})
        
        # Determine which model to load based on priority
        model_path, priority, model_metadata = self._select_model(model_name, version)
        
        if model_path is None:
            raise ValueError(f"No suitable model found for {model_name}")
        
        # Determine device
        if device is None:
            device = self._allocate_device(model_name)
        
        # Load the model
        loaded_model = self._load_model_from_path(
            model_path, 
            model_metadata, 
            device,
            priority
        )
        
        # Add to cache
        self.cache.put(cache_key, loaded_model)
        
        return (loaded_model.model,
               loaded_model.tokenizer,
               {"model_id": loaded_model.model_id,
                "version": loaded_model.version,
                "priority": loaded_model.priority.name,
                "device": loaded_model.device})
    
    def _select_model(self, model_name: str, 
                     version: Optional[str] = None) -> Tuple[Optional[Path], ModelPriority, Dict]:
        """
        Select the best available model based on priority.
        
        Args:
            model_name: Name of the model
            version: Specific version requested
            
        Returns:
            Tuple of (model_path, priority, metadata)
        """
        # Priority 1: Specific version
        if version and model_name in self.available_models["fine_tuned"]:
            if version in self.available_models["fine_tuned"][model_name]:
                path = self.base_path / "fine-tuned" / model_name / version
                metadata = self.available_models["fine_tuned"][model_name][version]
                logger.info(f"Selected specific version: {model_name} v{version}")
                return path, ModelPriority.SPECIFIC_VERSION, metadata
        
        # Priority 2: Deployed fine-tuned model
        if self.available_models["deployed"]:
            deployed = self.available_models["deployed"]
            if deployed.get("model_name") == model_name or deployed.get("base_model") == model_name:
                path = Path(deployed["path"])
                logger.info(f"Selected deployed model: {deployed['model_id']}")
                return path, ModelPriority.DEPLOYED_FINE_TUNED, deployed
        
        # Priority 3: Latest fine-tuned model
        if model_name in self.available_models["fine_tuned"]:
            versions = self.available_models["fine_tuned"][model_name]
            if versions:
                # Get latest version (already sorted in reverse order)
                latest_version = next(iter(versions))
                path = self.base_path / "fine-tuned" / model_name / latest_version
                metadata = versions[latest_version]
                logger.info(f"Selected latest fine-tuned: {model_name} v{latest_version}")
                return path, ModelPriority.LATEST_FINE_TUNED, metadata
        
        # Priority 4: Base model fallback
        if model_name in self.available_models["base"]:
            path = self.base_path / "base" / model_name
            metadata = self.available_models["base"][model_name]
            logger.info(f"Falling back to base model: {model_name}")
            return path, ModelPriority.BASE_MODEL, metadata
        
        # No model found
        logger.error(f"No model found for {model_name}")
        return None, None, {}
    
    def _load_model_from_path(self, model_path: Path, metadata: Dict, 
                             device: Union[str, int], 
                             priority: ModelPriority) -> LoadedModel:
        """
        Load a model from disk.
        
        Args:
            model_path: Path to model directory
            metadata: Model metadata
            device: Device to load on
            priority: Model priority level
            
        Returns:
            LoadedModel object
        """
        architecture = metadata.get("architecture", "AutoModelForTokenClassification")
        
        # Load SpaCy models
        if architecture == "SpacyTransformer":
            return self._load_spacy_model(model_path, metadata, device, priority)
        
        # Load transformer models
        return self._load_transformer_model(model_path, metadata, device, priority, architecture)
    
    def _load_transformer_model(self, model_path: Path, metadata: Dict,
                               device: Union[str, int], priority: ModelPriority,
                               architecture: str) -> LoadedModel:
        """Load a transformer model"""
        try:
            # Load tokenizer
            tokenizer_path = model_path / "tokenizer"
            if not tokenizer_path.exists():
                tokenizer_path = model_path  # Try root directory
            
            tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_path))
            
            # Load model
            model_path_str = str(model_path / "model")
            if not Path(model_path_str).exists():
                model_path_str = str(model_path)  # Try root directory
            
            # Get model class
            if architecture in self.ARCHITECTURE_MAP:
                model_class = self.ARCHITECTURE_MAP[architecture]
            else:
                model_class = AutoModelForTokenClassification
            
            # Load model
            model = model_class.from_pretrained(model_path_str)
            
            # Move to device
            if device != 'cpu' and torch.cuda.is_available():
                model = model.to(f"cuda:{device}")
            
            # Estimate memory usage
            memory_mb = self._estimate_model_memory(model)
            
            loaded_model = LoadedModel(
                model=model,
                tokenizer=tokenizer,
                model_id=metadata.get("model_id", "unknown"),
                version=metadata.get("version", "unknown"),
                model_type="transformer",
                priority=priority,
                device=device,
                loaded_at=datetime.now(),
                last_used=datetime.now(),
                memory_usage_mb=memory_mb
            )
            
            logger.info(f"Loaded transformer model {loaded_model.model_id} on device {device}")
            return loaded_model
            
        except Exception as e:
            logger.error(f"Failed to load transformer model from {model_path}: {e}")
            raise
    
    def _load_spacy_model(self, model_path: Path, metadata: Dict,
                         device: Union[str, int], priority: ModelPriority) -> LoadedModel:
        """Load a SpaCy model"""
        try:
            spacy_path = model_path / "spacy_model"
            if not spacy_path.exists():
                spacy_path = model_path
            
            # Load SpaCy model
            nlp = spacy.load(spacy_path)
            
            # Configure for GPU if available
            if device != 'cpu' and torch.cuda.is_available():
                spacy.prefer_gpu(device)
            
            # Estimate memory (rough estimate for SpaCy)
            memory_mb = 500  # Default estimate for SpaCy models
            
            loaded_model = LoadedModel(
                model=nlp,
                tokenizer=None,  # SpaCy models have built-in tokenization
                model_id=metadata.get("model_id", "unknown"),
                version=metadata.get("version", "unknown"),
                model_type="spacy",
                priority=priority,
                device=device,
                loaded_at=datetime.now(),
                last_used=datetime.now(),
                memory_usage_mb=memory_mb
            )
            
            logger.info(f"Loaded SpaCy model {loaded_model.model_id}")
            return loaded_model
            
        except Exception as e:
            logger.error(f"Failed to load SpaCy model from {model_path}: {e}")
            raise
    
    def _allocate_device(self, model_name: str) -> Union[str, int]:
        """
        Allocate optimal device for model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Device identifier
        """
        if not self.cuda_available:
            return 'cpu'
        
        # Simple round-robin allocation between GPU 0 and 1
        min_gpu = 0
        min_count = len(self.gpu_allocations[0])
        
        for gpu_id in range(min(2, self.device_count)):
            count = len(self.gpu_allocations[gpu_id])
            if count < min_count:
                min_count = count
                min_gpu = gpu_id
        
        self.gpu_allocations[min_gpu].append(model_name)
        return min_gpu
    
    def _estimate_model_memory(self, model: PreTrainedModel) -> float:
        """
        Estimate memory usage of a model in MB.
        
        Args:
            model: The model to estimate
            
        Returns:
            Estimated memory in MB
        """
        param_size = 0
        buffer_size = 0
        
        # Calculate parameter size
        for param in model.parameters():
            param_size += param.nelement() * param.element_size()
        
        # Calculate buffer size
        for buffer in model.buffers():
            buffer_size += buffer.nelement() * buffer.element_size()
        
        # Convert to MB and add overhead
        size_mb = (param_size + buffer_size) / 1024 / 1024
        overhead_factor = 1.5  # Account for gradients and optimizer state
        
        return size_mb * overhead_factor
    
    def transition_to_fine_tuned(self, model_name: str, 
                                 fine_tuned_path: Path,
                                 version: str) -> bool:
        """
        Seamlessly transition from base to fine-tuned model.
        
        Args:
            model_name: Name of the model
            fine_tuned_path: Path to fine-tuned model
            version: Version identifier
            
        Returns:
            True if successful
        """
        try:
            # Copy fine-tuned model to repository
            target_path = self.base_path / "fine-tuned" / model_name / version
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            if fine_tuned_path != target_path:
                import shutil
                shutil.copytree(fine_tuned_path, target_path, dirs_exist_ok=True)
            
            # Update metadata
            metadata_path = target_path / "metadata.json"
            metadata = {
                "model_id": f"{model_name}_{version}",
                "model_name": model_name,
                "version": version,
                "transition_date": datetime.now().isoformat(),
                "status": "available"
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Rescan available models
            self.available_models = self._scan_available_models()
            
            # Clear cache to force reload
            self.cache.clear()
            
            logger.info(f"Successfully transitioned to fine-tuned model: {model_name} v{version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to transition to fine-tuned model: {e}")
            return False
    
    def deploy_model(self, model_name: str, version: str) -> bool:
        """
        Deploy a specific model version to production.
        
        Args:
            model_name: Name of the model
            version: Version to deploy
            
        Returns:
            True if successful
        """
        try:
            # Source path
            source_path = self.base_path / "fine-tuned" / model_name / version
            if not source_path.exists():
                logger.error(f"Model version not found: {model_name} v{version}")
                return False
            
            # Clear existing production models
            production_path = self.base_path / "production"
            if production_path.exists():
                import shutil
                shutil.rmtree(production_path)
            
            production_path.mkdir(parents=True, exist_ok=True)
            
            # Copy to production
            target_path = production_path / f"{model_name}_{version}"
            import shutil
            shutil.copytree(source_path, target_path)
            
            # Update metadata
            metadata_path = target_path / "metadata.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            metadata["deployment_date"] = datetime.now().isoformat()
            metadata["deployment_status"] = "production"
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Rescan available models
            self.available_models = self._scan_available_models()
            
            logger.info(f"Deployed model to production: {model_name} v{version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deploy model: {e}")
            return False
    
    def get_model_info(self, model_name: str, 
                       version: Optional[str] = None) -> Optional[Dict]:
        """
        Get information about a specific model.
        
        Args:
            model_name: Name of the model
            version: Specific version (optional)
            
        Returns:
            Model information dictionary or None
        """
        # Check cache first
        cache_key = f"{model_name}_{version or 'latest'}"
        cached = self.cache.get(cache_key)
        if cached:
            return {
                "model_id": cached.model_id,
                "version": cached.version,
                "status": "loaded",
                "device": cached.device,
                "usage_count": cached.usage_count,
                "memory_mb": cached.memory_usage_mb
            }
        
        # Check available models
        if version:
            if model_name in self.available_models["fine_tuned"]:
                if version in self.available_models["fine_tuned"][model_name]:
                    return self.available_models["fine_tuned"][model_name][version]
        
        # Check base models
        if model_name in self.available_models["base"]:
            return self.available_models["base"][model_name]
        
        return None
    
    def list_available_models(self) -> Dict:
        """List all available models"""
        return {
            "base_models": list(self.available_models["base"].keys()),
            "fine_tuned_models": {
                name: list(versions.keys())
                for name, versions in self.available_models["fine_tuned"].items()
            },
            "deployed_model": self.available_models["deployed"]["model_id"] 
                             if self.available_models["deployed"] else None,
            "cache_stats": self.cache.get_stats()
        }
    
    def clear_cache(self):
        """Clear the model cache"""
        self.cache.clear()
        logger.info("Model cache cleared")
    
    def refresh_available_models(self):
        """Refresh the list of available models"""
        self.available_models = self._scan_available_models()
        logger.info("Refreshed available models list")


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Dynamic Model Loader")
    parser.add_argument("--load", help="Load a specific model")
    parser.add_argument("--version", help="Model version")
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--deploy", help="Deploy a model to production")
    parser.add_argument("--cache-stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--clear-cache", action="store_true", help="Clear model cache")
    
    args = parser.parse_args()
    
    loader = DynamicModelLoader()
    
    if args.load:
        model, tokenizer, info = loader.load_model(args.load, version=args.version)
        print(f"Loaded model: {json.dumps(info, indent=2)}")
    
    if args.deploy and args.version:
        success = loader.deploy_model(args.deploy, args.version)
        print(f"Deployment {'successful' if success else 'failed'}")
    
    if args.list:
        models = loader.list_available_models()
        print(json.dumps(models, indent=2))
    
    if args.cache_stats:
        stats = loader.cache.get_stats()
        print(json.dumps(stats, indent=2))
    
    if args.clear_cache:
        loader.clear_cache()
        print("Cache cleared")