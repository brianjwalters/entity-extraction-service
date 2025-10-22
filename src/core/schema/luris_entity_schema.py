"""
Luris Entity Schema V2 - Unified JSON Schema for Entity Extraction

This module defines the standardized schema for all entity extraction results,
ensuring consistent JSON output across multipass and unified strategies.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """
    Canonical entity types for LurisEntityV2 schema.

    Source: http://10.10.0.87:8007/api/v1/patterns (160 types with pattern examples)
    Generated: 2025-10-18

    This enum contains all entity types extracted from the Patterns API that have
    actual regex pattern examples. Organized into 8 categories:

    - Citations (22 types) - Legal citation formats
    - Legal Parties (12 types) - Parties in legal proceedings
    - Temporal (11 types) - Dates and time-related entities
    - Courts and Judicial (9 types) - Courts, judges, and judicial entities
    - Miscellaneous (96 types) - Other legal entities and concepts
    - Legal Professionals (4 types) - Attorneys, law firms
    - Statutory (3 types) - Statutory references
    - Financial (3 types) - Monetary amounts and financial terms

    Total: 160 entity types
    """

    # ==========================================
    # Citations (22 types)
    # ==========================================
    ADMINISTRATIVE_CITATION = "ADMINISTRATIVE_CITATION"
    CASE_CITATION = "CASE_CITATION"
    CFR_CITATIONS = "CFR_CITATIONS"
    CONSTITUTIONAL_CITATION = "CONSTITUTIONAL_CITATION"
    ELECTRONIC_CITATION = "ELECTRONIC_CITATION"
    ELECTRONIC_CITATIONS = "ELECTRONIC_CITATIONS"
    ENHANCED_CASE_CITATIONS = "ENHANCED_CASE_CITATIONS"
    HISTORICAL_CITATIONS = "HISTORICAL_CITATIONS"
    INTERNATIONAL_CITATION = "INTERNATIONAL_CITATION"
    INTERNATIONAL_CITATIONS = "INTERNATIONAL_CITATIONS"
    LAW_REVIEW_CITATION = "LAW_REVIEW_CITATION"
    PARALLEL_CITATIONS = "PARALLEL_CITATIONS"
    PATENT_CITATION = "PATENT_CITATION"
    PINPOINT_CITATIONS = "PINPOINT_CITATIONS"
    REGULATION_CITATION = "REGULATION_CITATION"
    RESTATEMENT_CITATION = "RESTATEMENT_CITATION"
    SEC_CITATION = "SEC_CITATION"
    STATUTE_CITATION = "STATUTE_CITATION"
    TREATISE_CITATION = "TREATISE_CITATION"
    TREATY_CITATION = "TREATY_CITATION"
    UNIFORM_LAW_CITATION = "UNIFORM_LAW_CITATION"
    USC_CITATIONS = "USC_CITATIONS"

    # ==========================================
    # Legal Parties (12 types)
    # ==========================================
    APPELLANT = "APPELLANT"
    APPELLEE = "APPELLEE"
    CONTRACT_PARTY = "CONTRACT_PARTY"
    DEFENDANT = "DEFENDANT"
    ENHANCED_PARTY_PATTERNS = "ENHANCED_PARTY_PATTERNS"
    INDIVIDUAL_PARTY = "INDIVIDUAL_PARTY"
    PARTY = "PARTY"
    PARTY_GROUP = "PARTY_GROUP"
    PETITIONER = "PETITIONER"
    PLAINTIFF = "PLAINTIFF"
    PRO_SE_PARTY = "PRO_SE_PARTY"
    RESPONDENT = "RESPONDENT"

    # ==========================================
    # Temporal (11 types)
    # ==========================================
    DATE = "DATE"
    DATE_RANGE = "DATE_RANGE"
    DEADLINE = "DEADLINE"
    DECISION_DATE = "DECISION_DATE"
    EFFECTIVE_DATE = "EFFECTIVE_DATE"
    EXECUTION_DATE = "EXECUTION_DATE"
    FILING_DATE = "FILING_DATE"
    LIMITATIONS_PERIOD = "LIMITATIONS_PERIOD"
    OPINION_DATE = "OPINION_DATE"
    RELATIVE_DATE = "RELATIVE_DATE"
    TERM_DATE = "TERM_DATE"

    # ==========================================
    # Courts and Judicial (9 types)
    # ==========================================
    COURT_COSTS = "COURT_COSTS"
    COURT_RULE_CITATION = "COURT_RULE_CITATION"
    ENHANCED_COURT_PATTERNS = "ENHANCED_COURT_PATTERNS"
    FEDERAL_COURTS = "FEDERAL_COURTS"
    GENERIC_COURT_REFERENCES = "GENERIC_COURT_REFERENCES"
    JUDGE = "JUDGE"
    SPECIALIZED_COURTS = "SPECIALIZED_COURTS"
    SPECIALIZED_COURT_CITATIONS = "SPECIALIZED_COURT_CITATIONS"
    STATE_COURTS = "STATE_COURTS"

    # ==========================================
    # Legal Professionals (4 types)
    # ==========================================
    ATTORNEY = "ATTORNEY"
    ATTORNEY_FEES = "ATTORNEY_FEES"
    INTERNATIONAL_LAW_FIRM = "INTERNATIONAL_LAW_FIRM"
    LAW_FIRM = "LAW_FIRM"

    # ==========================================
    # Statutory (3 types)
    # ==========================================
    CFR_TITLES = "CFR_TITLES"
    STATE_STATUTES = "STATE_STATUTES"
    USC_TITLES = "USC_TITLES"

    # ==========================================
    # Financial (3 types)
    # ==========================================
    MONETARY_AMOUNT = "MONETARY_AMOUNT"
    PER_UNIT_AMOUNT = "PER_UNIT_AMOUNT"
    THRESHOLD_AMOUNT = "THRESHOLD_AMOUNT"

    # ==========================================
    # Miscellaneous (96 types)
    # ==========================================
    ADDRESS = "ADDRESS"
    ADMINISTRATIVE = "ADMINISTRATIVE"
    ADMISSION_REQUEST = "ADMISSION_REQUEST"
    AGENCIES = "AGENCIES"
    AMENDMENTS = "AMENDMENTS"
    AMICUS_CURIAE = "AMICUS_CURIAE"
    APPEAL = "APPEAL"
    ARTICLE_REFERENCE = "ARTICLE_REFERENCE"
    BAIL = "BAIL"
    CASE_PARTIES = "CASE_PARTIES"
    CERTIORARI = "CERTIORARI"
    CIRCUITS = "CIRCUITS"
    CLASS_ACTION = "CLASS_ACTION"
    COMMERCE_CLAUSE = "COMMERCE_CLAUSE"
    CONGRESSIONAL = "CONGRESSIONAL"
    CONSTITUTIONAL = "CONSTITUTIONAL"
    CONSTITUTIONAL_AMENDMENT = "CONSTITUTIONAL_AMENDMENT"
    CONTRACT_VALUE = "CONTRACT_VALUE"
    CORPORATE_RESOLUTION = "CORPORATE_RESOLUTION"
    CORPORATION = "CORPORATION"
    DAMAGES = "DAMAGES"
    DEFAULT_JUDGMENT = "DEFAULT_JUDGMENT"
    DEFINED_TERM = "DEFINED_TERM"
    DEFINED_TERM_REFERENCE = "DEFINED_TERM_REFERENCE"
    DEMURRER = "DEMURRER"
    DEPOSITION = "DEPOSITION"
    DISCOVERY = "DISCOVERY"
    DISTRICT = "DISTRICT"
    DOUBLE_JEOPARDY = "DOUBLE_JEOPARDY"
    DUE_PROCESS = "DUE_PROCESS"
    EIGHTH_AMENDMENT = "EIGHTH_AMENDMENT"
    ENHANCED_PROCEDURAL_PATTERNS = "ENHANCED_PROCEDURAL_PATTERNS"
    ENTITY_STATUS = "ENTITY_STATUS"
    EQUAL_PROTECTION = "EQUAL_PROTECTION"
    ESTATE = "ESTATE"
    FEDERAL_AGENCY = "FEDERAL_AGENCY"
    FEDERAL_REGISTER = "FEDERAL_REGISTER"
    FEDERAL_RULES = "FEDERAL_RULES"
    FIDUCIARY = "FIDUCIARY"
    FIFTH_AMENDMENT = "FIFTH_AMENDMENT"
    FINE = "FINE"
    FISCAL_YEAR = "FISCAL_YEAR"
    FOURTH_AMENDMENT = "FOURTH_AMENDMENT"
    FREE_SPEECH = "FREE_SPEECH"
    GOVERNMENT_ENTITY = "GOVERNMENT_ENTITY"
    GOVERNMENT_LEGAL_OFFICE = "GOVERNMENT_LEGAL_OFFICE"
    GOVERNMENT_OFFICIAL = "GOVERNMENT_OFFICIAL"
    HABEAS_CORPUS = "HABEAS_CORPUS"
    HISTORICAL = "HISTORICAL"
    IMMUNITY = "IMMUNITY"
    INJUNCTION = "INJUNCTION"
    INTEREST_RATE = "INTEREST_RATE"
    INTERROGATORY = "INTERROGATORY"
    INTERVENOR = "INTERVENOR"
    JUDGMENT = "JUDGMENT"
    JUDICIAL_PANEL = "JUDICIAL_PANEL"
    JURISDICTION = "JURISDICTION"
    LATIN_TERM = "LATIN_TERM"
    LEGAL_MARKER = "LEGAL_MARKER"
    LOCATION = "LOCATION"
    MONETARY_RANGE = "MONETARY_RANGE"
    MOTION = "MOTION"
    NOTARY_BLOCK = "NOTARY_BLOCK"
    PARAGRAPH_HEADER = "PARAGRAPH_HEADER"
    PARTIES_CLAUSE = "PARTIES_CLAUSE"
    PATTERNS = "PATTERNS"
    PLEA = "PLEA"
    PRECEDENT = "PRECEDENT"
    PRECLUSION = "PRECLUSION"
    PROCEDURAL_RULE = "PROCEDURAL_RULE"
    PRODUCTION_REQUEST = "PRODUCTION_REQUEST"
    PROTECTIVE_ORDER = "PROTECTIVE_ORDER"
    PUBLIC_INTEREST_FIRM = "PUBLIC_INTEREST_FIRM"
    PUBLIC_LAWS = "PUBLIC_LAWS"
    QUARTER = "QUARTER"
    RELIGIOUS_FREEDOM = "RELIGIOUS_FREEDOM"
    RESTITUTION = "RESTITUTION"
    RES_JUDICATA = "RES_JUDICATA"
    SECTION_HEADER = "SECTION_HEADER"
    SECTION_MARKER = "SECTION_MARKER"
    SECTION_REFERENCE = "SECTION_REFERENCE"
    SECTION_SYMBOLS = "SECTION_SYMBOLS"
    SENTENCING = "SENTENCING"
    SETTLEMENT = "SETTLEMENT"
    SHORT_FORMS = "SHORT_FORMS"
    SIGNATORY_BLOCK = "SIGNATORY_BLOCK"
    SIGNATURE_LINE = "SIGNATURE_LINE"
    SIXTH_AMENDMENT = "SIXTH_AMENDMENT"
    SOVEREIGN_IMMUNITY = "SOVEREIGN_IMMUNITY"
    SPECIALIZED_JURISDICTION = "SPECIALIZED_JURISDICTION"
    STARE_DECISIS = "STARE_DECISIS"
    STATUTORY_CONSTRUCTION = "STATUTORY_CONSTRUCTION"
    SUBSECTION_MARKER = "SUBSECTION_MARKER"
    SUPREMACY_CLAUSE = "SUPREMACY_CLAUSE"
    VENUE = "VENUE"
    WITNESS_BLOCK = "WITNESS_BLOCK"

    # ==========================================
    # Backward Compatibility (Legacy Types)
    # ==========================================
    # These types may appear in legacy code but are mapped to canonical types above
    UNKNOWN = "UNKNOWN"


class ExtractionMethod(Enum):
    """Methods used for entity extraction."""
    REGEX = "regex"
    PATTERN = "pattern"
    AI_ENHANCED = "ai_enhanced"
    HYBRID = "hybrid"
    LEGACY = "legacy"
    MANUAL = "manual"


class ConfidenceLevel(Enum):
    """Confidence level categories."""
    HIGH = "high"      # 0.8 - 1.0
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"        # 0.0 - 0.5


@dataclass
class Position:
    """Standardized position information for entities."""
    start_pos: int
    end_pos: int
    
    def __post_init__(self):
        """Validate position values."""
        if self.start_pos < 0:
            self.start_pos = 0
        if self.end_pos < self.start_pos:
            self.end_pos = self.start_pos
    
    def length(self) -> int:
        """Get the length of the entity."""
        return self.end_pos - self.start_pos
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary format."""
        return {
            "start_pos": self.start_pos,
            "end_pos": self.end_pos
        }


@dataclass
class EntityMetadata:
    """Standardized metadata for extracted entities."""
    # Pattern information
    pattern_matched: Optional[str] = None
    pattern_source: Optional[str] = None
    pattern_confidence: Optional[float] = None
    
    # Context information
    sentence_context: Optional[str] = None
    paragraph_context: Optional[str] = None
    document_section: Optional[str] = None
    
    # Normalization
    normalized_value: Optional[str] = None
    canonical_form: Optional[str] = None
    
    # Relationships
    related_entities: List[str] = field(default_factory=list)
    entity_relations: Dict[str, Any] = field(default_factory=dict)
    
    # Processing info
    processing_time_ms: Optional[float] = None
    validation_status: Optional[str] = None
    quality_score: Optional[float] = None
    
    # Custom fields
    custom_attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)


@dataclass
class LurisEntityV2:
    """
    Unified entity schema for all Luris extraction strategies.
    
    This schema standardizes entity representation across multipass,
    unified, and legacy extraction methods.
    """
    # Core identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    entity_type: str = EntityType.UNKNOWN.value
    
    # Position information
    position: Position = field(default_factory=lambda: Position(0, 0))
    
    # Confidence and extraction info
    confidence: float = 0.0
    extraction_method: str = ExtractionMethod.REGEX.value
    
    # Optional classification
    subtype: Optional[str] = None
    category: Optional[str] = None
    
    # Metadata
    metadata: EntityMetadata = field(default_factory=EntityMetadata)
    
    # Timestamps
    created_at: float = field(default_factory=time.time)
    updated_at: Optional[float] = None
    
    def __post_init__(self):
        """Post-initialization validation and cleanup."""
        # Normalize entity type
        if isinstance(self.entity_type, str):
            self.entity_type = self.entity_type.upper()
            # Validate against known types
            valid_types = [e.value for e in EntityType]
            if self.entity_type not in valid_types:
                logger.warning(f"Unknown entity type: {self.entity_type}, using UNKNOWN")
                self.entity_type = EntityType.UNKNOWN.value
        
        # Ensure position is Position object
        if isinstance(self.position, dict):
            self.position = Position(
                start_pos=self.position.get('start_pos', 0),
                end_pos=self.position.get('end_pos', 0)
            )
        elif isinstance(self.position, (list, tuple)) and len(self.position) >= 2:
            self.position = Position(
                start_pos=int(self.position[0]),
                end_pos=int(self.position[1])
            )
        
        # Normalize confidence
        if self.confidence < 0.0:
            self.confidence = 0.0
        elif self.confidence > 1.0:
            self.confidence = 1.0
        
        # Ensure metadata is EntityMetadata object
        if isinstance(self.metadata, dict):
            self.metadata = EntityMetadata(**self.metadata)
        elif self.metadata is None:
            self.metadata = EntityMetadata()
    
    @property
    def start_pos(self) -> int:
        """Backward compatibility: get start position."""
        return self.position.start_pos
    
    @property 
    def end_pos(self) -> int:
        """Backward compatibility: get end position."""
        return self.position.end_pos
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level category."""
        if self.confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON serialization."""
        return {
            "id": self.id,
            "text": self.text,
            "entity_type": self.entity_type,
            "start_pos": self.position.start_pos,
            "end_pos": self.position.end_pos,
            "confidence": self.confidence,
            "extraction_method": self.extraction_method,
            "subtype": self.subtype,
            "category": self.category,
            "metadata": self.metadata.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def to_legacy_dict(self) -> Dict[str, Any]:
        """Convert to legacy dictionary format for backward compatibility."""
        return {
            "text": self.text,
            "entity_type": self.entity_type,
            "type": self.entity_type,  # Duplicate for compatibility
            "start_pos": self.position.start_pos,
            "end_pos": self.position.end_pos,
            "confidence": self.confidence,
            "extraction_method": self.extraction_method,
            "metadata": self.metadata.custom_attributes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LurisEntityV2':
        """Create LurisEntityV2 from dictionary data."""
        # Handle position data
        if 'position' in data:
            position_data = data['position']
        else:
            position_data = {
                'start_pos': data.get('start_pos', 0),
                'end_pos': data.get('end_pos', 0)
            }
        
        # Handle metadata
        metadata_data = data.get('metadata', {})
        if isinstance(metadata_data, dict):
            metadata = EntityMetadata(**metadata_data)
        else:
            metadata = EntityMetadata()
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            text=data.get('text', ''),
            entity_type=data.get('entity_type', data.get('type', EntityType.UNKNOWN.value)),
            position=Position(**position_data),
            confidence=data.get('confidence', 0.0),
            extraction_method=data.get('extraction_method', ExtractionMethod.REGEX.value),
            subtype=data.get('subtype'),
            category=data.get('category'),
            metadata=metadata,
            created_at=data.get('created_at', time.time()),
            updated_at=data.get('updated_at')
        )
    
    @classmethod
    def from_legacy_entity(cls, entity: Any) -> 'LurisEntityV2':
        """Convert legacy ExtractedEntity to LurisEntityV2."""
        if hasattr(entity, '__dict__'):
            # Object with attributes
            return cls(
                text=getattr(entity, 'text', ''),
                entity_type=getattr(entity, 'entity_type', getattr(entity, 'type', EntityType.UNKNOWN.value)),
                position=Position(
                    start_pos=getattr(entity, 'start_pos', 0),
                    end_pos=getattr(entity, 'end_pos', 0)
                ),
                confidence=getattr(entity, 'confidence', 0.0),
                extraction_method=getattr(entity, 'extraction_method', ExtractionMethod.LEGACY.value),
                metadata=EntityMetadata(
                    custom_attributes=getattr(entity, 'metadata', {})
                )
            )
        elif isinstance(entity, dict):
            # Dictionary format
            return cls.from_dict(entity)
        else:
            # Fallback
            logger.warning(f"Unknown entity format: {type(entity)}")
            return cls(text=str(entity) if entity else "")
    
    def validate(self) -> List[str]:
        """Validate entity data and return list of issues."""
        issues = []
        
        if not self.text:
            issues.append("Entity text is empty")
        
        if self.position.start_pos < 0:
            issues.append("Start position is negative")
        
        if self.position.end_pos < self.position.start_pos:
            issues.append("End position is before start position")
        
        if not (0.0 <= self.confidence <= 1.0):
            issues.append(f"Confidence {self.confidence} is not in range [0.0, 1.0]")
        
        if len(self.text) != self.position.length():
            issues.append(f"Text length ({len(self.text)}) doesn't match position length ({self.position.length()})")
        
        return issues
    
    def is_valid(self) -> bool:
        """Check if entity is valid."""
        return len(self.validate()) == 0


@dataclass
class ExtractionResultV2:
    """Unified extraction result schema."""
    # Basic information
    extraction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    strategy_used: str = "unknown"
    
    # Results
    entities: List[LurisEntityV2] = field(default_factory=list)
    citations: List[LurisEntityV2] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    
    # Processing information
    processing_time_ms: float = 0.0
    extraction_time: float = field(default_factory=time.time)
    
    # Quality metrics
    total_entities: int = 0
    confidence_distribution: Dict[str, int] = field(default_factory=dict)
    extraction_methods_used: List[str] = field(default_factory=list)
    overall_confidence: float = 0.0
    
    # Metadata
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    success: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate derived fields."""
        self.total_entities = len(self.entities)
        
        # Calculate confidence distribution
        self.confidence_distribution = {
            "high": len([e for e in self.entities if e.confidence >= 0.8]),
            "medium": len([e for e in self.entities if 0.5 <= e.confidence < 0.8]),
            "low": len([e for e in self.entities if e.confidence < 0.5])
        }
        
        # Calculate overall confidence
        if self.entities:
            self.overall_confidence = sum(e.confidence for e in self.entities) / len(self.entities)
        
        # Collect extraction methods
        methods = set(e.extraction_method for e in self.entities)
        self.extraction_methods_used = list(methods)
    
    def add_entity(self, entity: Union[LurisEntityV2, Dict[str, Any], Any]):
        """Add entity to results, converting to LurisEntityV2 if needed."""
        if isinstance(entity, LurisEntityV2):
            self.entities.append(entity)
        elif isinstance(entity, dict):
            self.entities.append(LurisEntityV2.from_dict(entity))
        else:
            self.entities.append(LurisEntityV2.from_legacy_entity(entity))
        
        # Update derived fields
        self.__post_init__()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON serialization."""
        return {
            "extraction_id": self.extraction_id,
            "document_id": self.document_id,
            "strategy_used": self.strategy_used,
            "entities": [e.to_dict() for e in self.entities],
            "citations": [c.to_dict() for c in self.citations],
            "relationships": self.relationships,
            "processing_time_ms": self.processing_time_ms,
            "extraction_time": self.extraction_time,
            "total_entities": self.total_entities,
            "confidence_distribution": self.confidence_distribution,
            "extraction_methods_used": self.extraction_methods_used,
            "overall_confidence": self.overall_confidence,
            "extraction_metadata": self.extraction_metadata,
            "quality_metrics": self.quality_metrics,
            "success": self.success,
            "warnings": self.warnings,
            "errors": self.errors
        }
    
    def to_legacy_dict(self) -> Dict[str, Any]:
        """Convert to legacy format for backward compatibility."""
        return {
            "extraction_id": self.extraction_id,
            "document_id": self.document_id,
            "strategy_used": self.strategy_used,
            "processing_time_ms": self.processing_time_ms,
            "entities": [e.to_legacy_dict() for e in self.entities],
            "citations": [c.to_legacy_dict() for c in self.citations],
            "relationships": self.relationships,
            "extraction_metadata": {
                **self.extraction_metadata,
                "total_entities": self.total_entities,
                "overall_confidence": self.overall_confidence,
                "pattern_enhanced": True
            },
            "quality_metrics": self.quality_metrics
        }


# JSON Schema definition for validation
LURIS_ENTITY_V2_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "text": {"type": "string"},
        "entity_type": {"type": "string"},
        "start_pos": {"type": "integer", "minimum": 0},
        "end_pos": {"type": "integer", "minimum": 0},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "extraction_method": {"type": "string"},
        "subtype": {"type": ["string", "null"]},
        "category": {"type": ["string", "null"]},
        "metadata": {"type": "object"},
        "created_at": {"type": "number"},
        "updated_at": {"type": ["number", "null"]}
    },
    "required": ["text", "entity_type", "start_pos", "end_pos", "confidence", "extraction_method"],
    "additionalProperties": False
}

EXTRACTION_RESULT_V2_SCHEMA = {
    "type": "object",
    "properties": {
        "extraction_id": {"type": "string"},
        "document_id": {"type": "string"},
        "strategy_used": {"type": "string"},
        "entities": {
            "type": "array",
            "items": LURIS_ENTITY_V2_SCHEMA
        },
        "citations": {
            "type": "array", 
            "items": LURIS_ENTITY_V2_SCHEMA
        },
        "relationships": {
            "type": "array",
            "items": {"type": "object"}
        },
        "processing_time_ms": {"type": "number"},
        "extraction_time": {"type": "number"},
        "total_entities": {"type": "integer"},
        "overall_confidence": {"type": "number"},
        "success": {"type": "boolean"}
    },
    "required": ["extraction_id", "document_id", "strategy_used", "entities", "success"],
    "additionalProperties": True
}