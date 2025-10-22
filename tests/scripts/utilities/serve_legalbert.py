#!/usr/bin/env python3
"""
FastAPI service for serving fine-tuned LegalBERT NER model.
Provides REST API for entity extraction compatible with vLLM endpoints.
"""

import argparse
import torch
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from transformers import AutoTokenizer, AutoModelForTokenClassification
import numpy as np
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Request/Response models
class NERRequest(BaseModel):
    """Request model for NER prediction."""
    text: str = Field(..., description="Text to extract entities from")
    max_length: Optional[int] = Field(512, description="Maximum sequence length")
    return_all_scores: Optional[bool] = Field(False, description="Return confidence scores for all labels")
    aggregation_strategy: Optional[str] = Field("simple", description="How to aggregate subword tokens")

class Entity(BaseModel):
    """Entity model."""
    type: str
    text: str
    start: int
    end: int
    confidence: float
    tokens: Optional[List[str]] = None

class NERResponse(BaseModel):
    """Response model for NER prediction."""
    entities: List[Entity]
    processing_time_ms: float
    model_name: str
    total_tokens: int

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool
    gpu_available: bool
    model_name: str
    timestamp: str

class LegalBERTServer:
    """Server for LegalBERT NER model."""
    
    def __init__(self, model_path: str, device: str = "cuda", batch_size: int = 32, max_seq_length: int = 512):
        self.model_path = Path(model_path)
        self.device = device
        self.batch_size = batch_size
        self.max_seq_length = max_seq_length
        self.model = None
        self.tokenizer = None
        self.label_mapping = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def load_model(self):
        """Load the fine-tuned LegalBERT model."""
        logger.info(f"Loading model from {self.model_path}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
        
        # Load model
        self.model = AutoModelForTokenClassification.from_pretrained(str(self.model_path))
        
        # Move to device
        if self.device == "cuda" and torch.cuda.is_available():
            self.model = self.model.cuda()
            logger.info(f"Model loaded on GPU: {torch.cuda.get_device_name(0)}")
        else:
            logger.info("Model loaded on CPU")
        
        # Set to eval mode
        self.model.eval()
        
        # Load label mapping
        label_mapping_file = self.model_path / "../data/final/label_mapping.json"
        if label_mapping_file.exists():
            with open(label_mapping_file, 'r') as f:
                self.label_mapping = json.load(f)
        else:
            # Use model config
            self.label_mapping = {
                'id2label': self.model.config.id2label,
                'label2id': self.model.config.label2id
            }
        
        logger.info(f"Model loaded successfully with {len(self.label_mapping['id2label'])} labels")
    
    def predict(self, text: str, max_length: int = 512, return_all_scores: bool = False) -> Dict[str, Any]:
        """Perform NER prediction on input text."""
        start_time = datetime.now()
        
        # Tokenize
        inputs = self.tokenizer(
            text,
            truncation=True,
            padding=True,
            max_length=max_length,
            return_tensors="pt",
            return_offsets_mapping=True
        )
        
        # Get offset mapping before moving to device
        offset_mapping = inputs.pop('offset_mapping')[0].tolist()
        
        # Move to device
        if self.device == "cuda" and torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # Predict
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.argmax(outputs.logits, dim=-1)
            probabilities = torch.softmax(outputs.logits, dim=-1)
        
        # Extract entities
        entities = self._extract_entities(
            text,
            predictions[0],
            probabilities[0],
            offset_mapping,
            inputs['input_ids'][0],
            return_all_scores
        )
        
        # Calculate processing time
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            'entities': entities,
            'processing_time_ms': processing_time_ms,
            'model_name': 'legalbert-ner',
            'total_tokens': len(inputs['input_ids'][0])
        }
    
    def _extract_entities(self, text: str, predictions: torch.Tensor, 
                         probabilities: torch.Tensor, offset_mapping: List,
                         input_ids: torch.Tensor, return_all_scores: bool) -> List[Dict]:
        """Extract entities from model predictions."""
        entities = []
        current_entity = None
        
        for idx, (pred_id, probs, offsets) in enumerate(zip(predictions, probabilities, offset_mapping)):
            # Skip special tokens
            if offsets[0] == 0 and offsets[1] == 0:
                # Finish current entity if exists
                if current_entity:
                    entities.append(current_entity)
                    current_entity = None
                continue
            
            pred_id = pred_id.item()
            label = self.label_mapping['id2label'].get(str(pred_id), 'O')
            confidence = probs[pred_id].item()
            
            if label != 'O':
                # Parse BIO tag
                if '-' in label:
                    bio_tag, entity_type = label.split('-', 1)
                else:
                    bio_tag, entity_type = 'B', label
                
                token_start, token_end = offsets
                
                if bio_tag == 'B':
                    # Start new entity
                    if current_entity:
                        entities.append(current_entity)
                    
                    current_entity = {
                        'type': entity_type,
                        'text': text[token_start:token_end],
                        'start': token_start,
                        'end': token_end,
                        'confidence': confidence,
                        'tokens': [self.tokenizer.decode([input_ids[idx].item()])]
                    }
                    
                elif bio_tag == 'I' and current_entity and current_entity['type'] == entity_type:
                    # Continue entity
                    current_entity['end'] = token_end
                    current_entity['text'] = text[current_entity['start']:token_end]
                    current_entity['confidence'] = (current_entity['confidence'] + confidence) / 2
                    current_entity['tokens'].append(self.tokenizer.decode([input_ids[idx].item()]))
                    
            else:
                # End current entity
                if current_entity:
                    entities.append(current_entity)
                    current_entity = None
        
        # Add final entity
        if current_entity:
            entities.append(current_entity)
        
        # Clean up tokens field if not needed
        if not return_all_scores:
            for entity in entities:
                entity.pop('tokens', None)
        
        return entities
    
    async def predict_async(self, text: str, **kwargs) -> Dict[str, Any]:
        """Async wrapper for prediction."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.predict, text, **kwargs)

# Create FastAPI app
app = FastAPI(
    title="LegalBERT NER Service",
    description="Entity extraction service using fine-tuned LegalBERT",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global server instance
server: Optional[LegalBERTServer] = None

@app.on_event("startup")
async def startup_event():
    """Load model on startup."""
    global server
    # Model path will be set via command line args
    pass

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if server and server.model else "unhealthy",
        model_loaded=server.model is not None if server else False,
        gpu_available=torch.cuda.is_available(),
        model_name="legalbert-ner",
        timestamp=datetime.now().isoformat()
    )

@app.post("/v1/ner/predict", response_model=NERResponse)
async def predict(request: NERRequest):
    """Main prediction endpoint."""
    if not server or not server.model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        result = await server.predict_async(
            request.text,
            max_length=request.max_length,
            return_all_scores=request.return_all_scores
        )
        
        return NERResponse(**result)
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models")
async def list_models():
    """List available models."""
    return {
        "models": [
            {
                "id": "legalbert-ner",
                "object": "model",
                "created": 1700000000,
                "owned_by": "entity-extraction-service"
            }
        ]
    }

@app.post("/v1/ner/batch", response_model=List[NERResponse])
async def batch_predict(requests: List[NERRequest]):
    """Batch prediction endpoint."""
    if not server or not server.model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Process in parallel
    tasks = [server.predict_async(req.text, max_length=req.max_length) for req in requests]
    results = await asyncio.gather(*tasks)
    
    return [NERResponse(**result) for result in results]

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Serve LegalBERT NER model")
    parser.add_argument("--model-path", type=str, required=True, help="Path to model directory")
    parser.add_argument("--port", type=int, default=8081, help="Port to serve on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for inference")
    parser.add_argument("--max-seq-length", type=int, default=512, help="Maximum sequence length")
    parser.add_argument("--device", type=str, default="cuda", help="Device to use (cuda/cpu)")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    
    args = parser.parse_args()
    
    # Initialize server
    global server
    server = LegalBERTServer(
        model_path=args.model_path,
        device=args.device,
        batch_size=args.batch_size,
        max_seq_length=args.max_seq_length
    )
    
    # Load model
    try:
        server.load_model()
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise
    
    # Run server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level="info"
    )

if __name__ == "__main__":
    main()