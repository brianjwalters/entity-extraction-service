"""
Relationship Extraction Models for CALES Legal Entity System

This module provides data models and machine learning model loaders
for relationship extraction between legal entities, supporting both
pattern-based and neural approaches.
"""

import os
import torch
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
from pathlib import Path

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    AutoModelForTokenClassification,
    PreTrainedModel,
    PreTrainedTokenizer,
    pipeline
)

# Configure logging
logger = logging.getLogger(__name__)


class RelationshipType(Enum):
    """Enumeration of legal relationship types"""
    
    # Law firm relationships
    REPRESENTS = "represents"
    ASSISTS = "assists"
    CO_COUNSEL = "co_counsel"
    OPPOSING_COUNSEL = "opposing_counsel"
    
    # Judge relationships
    PRESIDES_OVER = "presides_over"
    RENDERED = "rendered"
    RULED_ON = "ruled_on"
    ASSIGNED_TO = "assigned_to"
    
    # Party relationships
    SUES = "sues"
    APPEALS_AGAINST = "appeals_against"
    DEFENDS_AGAINST = "defends_against"
    SETTLES_WITH = "settles_with"
    CONTRACTS_WITH = "contracts_with"
    
    # Monetary relationships
    AWARDED_TO = "awarded_to"
    IMPOSED_ON = "imposed_on"
    PAID_BY = "paid_by"
    OWES_TO = "owes_to"
    DAMAGES_TO = "damages_to"
    
    # Date relationships
    FILED_ON = "filed_on"
    SCHEDULED_FOR = "scheduled_for"
    OCCURRED_ON = "occurred_on"
    EXPIRES_ON = "expires_on"
    EFFECTIVE_FROM = "effective_from"
    
    # Court relationships
    VENUE_FOR = "venue_for"
    REVIEWING = "reviewing"
    TRANSFERRED_FROM = "transferred_from"
    REMANDED_TO = "remanded_to"
    
    # Document relationships
    FILED_BY = "filed_by"
    AUTHORED_BY = "authored_by"
    SIGNED_BY = "signed_by"
    SUBMITTED_BY = "submitted_by"
    CONTAINS = "contains"
    REFERENCES = "references"
    
    # Citation relationships
    CITES = "cites"
    CITED_BY = "cited_by"
    DISTINGUISHES = "distinguishes"
    OVERRULES = "overrules"
    FOLLOWS = "follows"
    ESTABLISHES = "establishes"
    BASIS_FOR = "basis_for"
    
    # Corporate relationships
    OWNS = "owns"
    SUBSIDIARY_OF = "subsidiary_of"
    MERGED_WITH = "merged_with"
    ACQUIRED_BY = "acquired_by"
    EMPLOYS = "employs"
    
    # Criminal relationships
    CHARGED_WITH = "charged_with"
    CONVICTED_OF = "convicted_of"
    SENTENCED_FOR = "sentenced_for"
    PROSECUTED_BY = "prosecuted_by"
    
    # Property relationships
    OWNER_OF = "owner_of"
    TENANT_OF = "tenant_of"
    LIENHOLDER_OF = "lienholder_of"
    EASEMENT_ON = "easement_on"
    
    # Generic relationships
    RELATED_TO = "related_to"
    ASSOCIATED_WITH = "associated_with"
    MENTIONED_WITH = "mentioned_with"
    PART_OF = "part_of"


@dataclass
class EntityMention:
    """Represents a single entity mention in text"""
    entity_id: str
    entity_type: str
    entity_text: str
    start_position: int
    end_position: int
    confidence: float = 0.0
    canonical_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationshipInstance:
    """Represents a single relationship between two entities"""
    relationship_id: str
    relationship_type: RelationshipType
    source_entity: EntityMention
    target_entity: EntityMention
    confidence: float
    extraction_method: str  # 'pattern', 'dependency', 'model', 'proximity', 'coreference'
    context: str = ""
    context_start: int = 0
    context_end: int = 0
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    extracted_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert relationship instance to dictionary"""
        return {
            "relationship_id": self.relationship_id,
            "relationship_type": self.relationship_type.value,
            "source_entity": {
                "entity_id": self.source_entity.entity_id,
                "entity_type": self.source_entity.entity_type,
                "entity_text": self.source_entity.entity_text,
                "canonical_name": self.source_entity.canonical_name,
                "position": [self.source_entity.start_position, self.source_entity.end_position]
            },
            "target_entity": {
                "entity_id": self.target_entity.entity_id,
                "entity_type": self.target_entity.entity_type,
                "entity_text": self.target_entity.entity_text,
                "canonical_name": self.target_entity.canonical_name,
                "position": [self.target_entity.start_position, self.target_entity.end_position]
            },
            "confidence": self.confidence,
            "extraction_method": self.extraction_method,
            "context": self.context,
            "context_position": [self.context_start, self.context_end],
            "evidence": self.evidence,
            "metadata": self.metadata,
            "extracted_at": self.extracted_at.isoformat()
        }


@dataclass
class RelationshipExtractionResult:
    """Complete result of relationship extraction"""
    document_id: str
    relationships: List[RelationshipInstance]
    entities: List[EntityMention]
    extraction_time_ms: float
    model_used: str
    extraction_config: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary"""
        return {
            "document_id": self.document_id,
            "relationships": [r.to_dict() for r in self.relationships],
            "entities": [
                {
                    "entity_id": e.entity_id,
                    "entity_type": e.entity_type,
                    "entity_text": e.entity_text,
                    "canonical_name": e.canonical_name,
                    "position": [e.start_position, e.end_position],
                    "confidence": e.confidence
                }
                for e in self.entities
            ],
            "extraction_time_ms": self.extraction_time_ms,
            "model_used": self.model_used,
            "extraction_config": self.extraction_config,
            "statistics": self.statistics
        }


class RelationshipExtractionModel:
    """
    Custom model loader for legal relationship extraction.
    Supports Legal-BERT and other fine-tuned models.
    """
    
    def __init__(self, 
                 model_name: str = "nlpaueb/legal-bert-base-uncased",
                 model_path: Optional[str] = None,
                 device: Optional[str] = None,
                 use_dynamic_loader: bool = True):
        """
        Initialize the relationship extraction model.
        
        Args:
            model_name: Name or path of the model to load
            model_path: Custom path to fine-tuned model
            device: Device to load model on ('cpu', 'cuda', 'cuda:0', etc.)
            use_dynamic_loader: Whether to use DynamicModelLoader
        """
        self.model_name = model_name
        self.model_path = model_path or model_name
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.use_dynamic_loader = use_dynamic_loader
        
        # Model components
        self.model: Optional[PreTrainedModel] = None
        self.tokenizer: Optional[PreTrainedTokenizer] = None
        self.pipeline = None
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize model
        self._initialize_model()
    
    def _load_config(self) -> Dict:
        """Load model configuration"""
        config_path = Path(__file__).parent / "relationship_config.yaml"
        if config_path.exists():
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        
        # Default configuration
        return {
            "max_sequence_length": 512,
            "batch_size": 16,
            "confidence_threshold": 0.7,
            "relationship_labels": [r.value for r in RelationshipType],
            "entity_pair_window": 100,  # Maximum token distance between entities
            "use_context_window": True,
            "context_window_size": 50  # Tokens around entity pair
        }
    
    def _initialize_model(self):
        """Initialize the model and tokenizer"""
        try:
            if self.use_dynamic_loader and self._check_dynamic_loader():
                # Use DynamicModelLoader if available
                from ..model_management.dynamic_model_loader import DynamicModelLoader
                loader = DynamicModelLoader()
                
                # Try to load fine-tuned relationship model
                try:
                    self.model, self.tokenizer, metadata = loader.load_model(
                        "legal-relationship-extractor",
                        device=self.device
                    )
                    logger.info(f"Loaded fine-tuned relationship model: {metadata}")
                except:
                    # Fall back to base model
                    self._load_base_model()
            else:
                # Load model directly
                self._load_base_model()
            
            # Create pipeline for relationship classification
            if self.model and self.tokenizer:
                self._create_pipeline()
                
        except Exception as e:
            logger.error(f"Failed to initialize relationship model: {e}")
            raise
    
    def _check_dynamic_loader(self) -> bool:
        """Check if DynamicModelLoader is available"""
        try:
            from ..model_management.dynamic_model_loader import DynamicModelLoader
            return True
        except ImportError:
            return False
    
    def _load_base_model(self):
        """Load base model directly"""
        try:
            # Check for local fine-tuned model
            fine_tuned_path = Path("/srv/luris/be/models/relationship-extraction")
            if fine_tuned_path.exists():
                self.model_path = str(fine_tuned_path)
                logger.info(f"Loading fine-tuned model from {self.model_path}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            
            # Load model for sequence classification (relationship classification)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_path,
                num_labels=len(self.config["relationship_labels"]),
                ignore_mismatched_sizes=True  # Allow loading with different number of labels
            )
            
            # Move to device
            if self.device != 'cpu':
                self.model = self.model.to(self.device)
            
            logger.info(f"Loaded model {self.model_name} on device {self.device}")
            
        except Exception as e:
            logger.warning(f"Failed to load fine-tuned model, falling back to base: {e}")
            
            # Fall back to base Legal-BERT
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                num_labels=len(self.config["relationship_labels"])
            )
            
            if self.device != 'cpu':
                self.model = self.model.to(self.device)
    
    def _create_pipeline(self):
        """Create HuggingFace pipeline for inference"""
        self.pipeline = pipeline(
            "text-classification",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if self.device.startswith('cuda') else -1,
            max_length=self.config["max_sequence_length"],
            truncation=True
        )
    
    def predict_relationship(self, 
                            text: str,
                            entity1: EntityMention,
                            entity2: EntityMention) -> Tuple[RelationshipType, float]:
        """
        Predict relationship between two entities.
        
        Args:
            text: Document text
            entity1: First entity
            entity2: Second entity
            
        Returns:
            Tuple of (relationship_type, confidence_score)
        """
        if not self.pipeline:
            raise RuntimeError("Model pipeline not initialized")
        
        # Extract context around entities
        context = self._extract_entity_context(text, entity1, entity2)
        
        # Format input for classification
        input_text = self._format_input(context, entity1, entity2)
        
        # Get predictions
        results = self.pipeline(input_text)
        
        if results:
            top_result = results[0]
            relationship_type = self._label_to_relationship_type(top_result['label'])
            confidence = top_result['score']
            
            if confidence >= self.config["confidence_threshold"]:
                return relationship_type, confidence
        
        return RelationshipType.RELATED_TO, 0.5  # Default fallback
    
    def _extract_entity_context(self, 
                               text: str,
                               entity1: EntityMention,
                               entity2: EntityMention) -> str:
        """Extract context window around entity pair"""
        if not self.config.get("use_context_window", True):
            return text
        
        # Find boundaries
        start = min(entity1.start_position, entity2.start_position)
        end = max(entity1.end_position, entity2.end_position)
        
        # Expand window
        window_size = self.config.get("context_window_size", 50)
        
        # Find word boundaries
        context_start = max(0, start - window_size)
        context_end = min(len(text), end + window_size)
        
        # Expand to word boundaries
        while context_start > 0 and text[context_start] not in ' \n\t':
            context_start -= 1
        while context_end < len(text) and text[context_end] not in ' \n\t':
            context_end += 1
        
        return text[context_start:context_end].strip()
    
    def _format_input(self, 
                     context: str,
                     entity1: EntityMention,
                     entity2: EntityMention) -> str:
        """
        Format input for relationship classification.
        Uses special tokens to mark entities.
        """
        # Mark entities in context with special tokens
        marked_text = context
        
        # Replace entity mentions with marked versions
        # Sort by position to handle overlapping mentions
        replacements = [
            (entity1.entity_text, f"[E1:{entity1.entity_type}]{entity1.entity_text}[/E1]"),
            (entity2.entity_text, f"[E2:{entity2.entity_type}]{entity2.entity_text}[/E2]")
        ]
        
        for original, replacement in replacements:
            marked_text = marked_text.replace(original, replacement, 1)
        
        return marked_text
    
    def _label_to_relationship_type(self, label: str) -> RelationshipType:
        """Convert model label to RelationshipType"""
        try:
            # Handle LABEL_X format from transformers
            if label.startswith("LABEL_"):
                idx = int(label.split("_")[1])
                label = self.config["relationship_labels"][idx]
            
            return RelationshipType(label)
        except (ValueError, IndexError):
            return RelationshipType.RELATED_TO
    
    def batch_predict(self, 
                     text: str,
                     entity_pairs: List[Tuple[EntityMention, EntityMention]],
                     batch_size: Optional[int] = None) -> List[Tuple[RelationshipType, float]]:
        """
        Predict relationships for multiple entity pairs.
        
        Args:
            text: Document text
            entity_pairs: List of entity pairs
            batch_size: Batch size for processing
            
        Returns:
            List of (relationship_type, confidence) tuples
        """
        batch_size = batch_size or self.config.get("batch_size", 16)
        results = []
        
        for i in range(0, len(entity_pairs), batch_size):
            batch = entity_pairs[i:i + batch_size]
            
            # Prepare batch inputs
            batch_inputs = []
            for entity1, entity2 in batch:
                context = self._extract_entity_context(text, entity1, entity2)
                input_text = self._format_input(context, entity1, entity2)
                batch_inputs.append(input_text)
            
            # Process batch
            if self.pipeline:
                batch_results = self.pipeline(batch_inputs)
                
                for result_list in batch_results:
                    if isinstance(result_list, list):
                        top_result = result_list[0] if result_list else None
                    else:
                        top_result = result_list
                    
                    if top_result:
                        rel_type = self._label_to_relationship_type(top_result['label'])
                        confidence = top_result['score']
                        results.append((rel_type, confidence))
                    else:
                        results.append((RelationshipType.RELATED_TO, 0.5))
        
        return results
    
    def fine_tune(self, 
                 training_data: List[Dict],
                 validation_data: Optional[List[Dict]] = None,
                 output_dir: str = "/srv/luris/be/models/relationship-extraction",
                 epochs: int = 3,
                 learning_rate: float = 2e-5):
        """
        Fine-tune the model on legal relationship data.
        
        Args:
            training_data: List of training examples
            validation_data: Optional validation data
            output_dir: Directory to save fine-tuned model
            epochs: Number of training epochs
            learning_rate: Learning rate for optimization
        """
        from transformers import TrainingArguments, Trainer
        from torch.utils.data import Dataset
        
        class RelationshipDataset(Dataset):
            def __init__(self, data, tokenizer, max_length=512):
                self.data = data
                self.tokenizer = tokenizer
                self.max_length = max_length
            
            def __len__(self):
                return len(self.data)
            
            def __getitem__(self, idx):
                item = self.data[idx]
                encoding = self.tokenizer(
                    item['text'],
                    truncation=True,
                    padding='max_length',
                    max_length=self.max_length,
                    return_tensors='pt'
                )
                
                return {
                    'input_ids': encoding['input_ids'].flatten(),
                    'attention_mask': encoding['attention_mask'].flatten(),
                    'labels': torch.tensor(item['label'], dtype=torch.long)
                }
        
        # Create datasets
        train_dataset = RelationshipDataset(training_data, self.tokenizer)
        val_dataset = RelationshipDataset(validation_data, self.tokenizer) if validation_data else None
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=8,
            per_device_eval_batch_size=8,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir=f"{output_dir}/logs",
            learning_rate=learning_rate,
            evaluation_strategy="epoch" if val_dataset else "no",
            save_strategy="epoch",
            load_best_model_at_end=True if val_dataset else False,
        )
        
        # Create trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            tokenizer=self.tokenizer,
        )
        
        # Train
        trainer.train()
        
        # Save model
        trainer.save_model(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        # Save metadata
        metadata = {
            "model_name": "legal-relationship-extractor",
            "base_model": self.model_name,
            "fine_tuned_date": datetime.now().isoformat(),
            "epochs": epochs,
            "training_samples": len(training_data),
            "validation_samples": len(validation_data) if validation_data else 0
        }
        
        with open(f"{output_dir}/metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Fine-tuned model saved to {output_dir}")
    
    def evaluate(self, test_data: List[Dict]) -> Dict[str, float]:
        """
        Evaluate model performance on test data.
        
        Args:
            test_data: List of test examples with ground truth
            
        Returns:
            Dictionary of evaluation metrics
        """
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
        
        predictions = []
        true_labels = []
        
        for item in test_data:
            # Get prediction
            entity1 = EntityMention(**item['entity1'])
            entity2 = EntityMention(**item['entity2'])
            
            rel_type, confidence = self.predict_relationship(
                item['text'],
                entity1,
                entity2
            )
            
            predictions.append(rel_type.value)
            true_labels.append(item['true_relationship'])
        
        # Calculate metrics
        accuracy = accuracy_score(true_labels, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            true_labels, 
            predictions, 
            average='weighted'
        )
        
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "total_samples": len(test_data)
        }
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded model"""
        return {
            "model_name": self.model_name,
            "model_path": self.model_path,
            "device": str(self.device),
            "num_labels": len(self.config["relationship_labels"]),
            "max_sequence_length": self.config["max_sequence_length"],
            "confidence_threshold": self.config["confidence_threshold"],
            "model_loaded": self.model is not None,
            "tokenizer_loaded": self.tokenizer is not None,
            "pipeline_ready": self.pipeline is not None
        }