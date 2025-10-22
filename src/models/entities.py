"""
Entity Extraction Service - Entity and Citation Models

This module contains Pydantic models for legal entities, citations, and relationships
extracted by the hybrid REGEX + AI workflow.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class EntityType(str, Enum):
    """Comprehensive legal entity types for classification."""
    
    # Courts and Judicial
    COURT = "COURT"
    JUDGE = "JUDGE"
    MAGISTRATE = "MAGISTRATE"
    ARBITRATOR = "ARBITRATOR"
    MEDIATOR = "MEDIATOR"
    SPECIAL_MASTER = "SPECIAL_MASTER"
    COURT_CLERK = "COURT_CLERK"
    COURT_REPORTER = "COURT_REPORTER"
    
    # Parties and Representatives
    PARTY = "PARTY"
    PLAINTIFF = "PLAINTIFF"
    DEFENDANT = "DEFENDANT"
    APPELLANT = "APPELLANT"
    APPELLEE = "APPELLEE"
    PETITIONER = "PETITIONER"
    RESPONDENT = "RESPONDENT"
    INTERVENOR = "INTERVENOR"
    AMICUS_CURIAE = "AMICUS_CURIAE"
    THIRD_PARTY = "THIRD_PARTY"
    CLASS_REPRESENTATIVE = "CLASS_REPRESENTATIVE"
    
    # Legal Professionals
    ATTORNEY = "ATTORNEY"
    LAW_FIRM = "LAW_FIRM"
    PROSECUTOR = "PROSECUTOR"
    PUBLIC_DEFENDER = "PUBLIC_DEFENDER"
    LEGAL_AID = "LEGAL_AID"
    PARALEGAL = "PARALEGAL"
    EXPERT_WITNESS = "EXPERT_WITNESS"
    LAY_WITNESS = "LAY_WITNESS"
    
    # Government and Agencies
    GOVERNMENT_ENTITY = "GOVERNMENT_ENTITY"
    FEDERAL_AGENCY = "FEDERAL_AGENCY"
    STATE_AGENCY = "STATE_AGENCY"
    LOCAL_AGENCY = "LOCAL_AGENCY"
    REGULATORY_BODY = "REGULATORY_BODY"
    LEGISLATIVE_BODY = "LEGISLATIVE_BODY"
    EXECUTIVE_OFFICE = "EXECUTIVE_OFFICE"
    
    # Documents and Filings
    DOCUMENT = "DOCUMENT"
    MOTION = "MOTION"
    BRIEF = "BRIEF"
    COMPLAINT = "COMPLAINT"
    ANSWER = "ANSWER"
    DISCOVERY_DOCUMENT = "DISCOVERY_DOCUMENT"
    DEPOSITION = "DEPOSITION"
    INTERROGATORY = "INTERROGATORY"
    AFFIDAVIT = "AFFIDAVIT"
    DECLARATION = "DECLARATION"
    EXHIBIT = "EXHIBIT"
    TRANSCRIPT = "TRANSCRIPT"
    ORDER = "ORDER"
    JUDGMENT = "JUDGMENT"
    VERDICT = "VERDICT"
    SETTLEMENT = "SETTLEMENT"
    CONTRACT = "CONTRACT"
    AGREEMENT = "AGREEMENT"
    
    # Jurisdictions and Venues
    JURISDICTION = "JURISDICTION"
    FEDERAL_JURISDICTION = "FEDERAL_JURISDICTION"
    STATE_JURISDICTION = "STATE_JURISDICTION"
    VENUE = "VENUE"
    FORUM = "FORUM"
    DISTRICT = "DISTRICT"
    CIRCUIT = "CIRCUIT"
    DIVISION = "DIVISION"
    
    # Legal Authority
    STATUTE = "STATUTE"
    REGULATION = "REGULATION"
    CASE_LAW = "CASE_LAW"
    CONSTITUTIONAL_PROVISION = "CONSTITUTIONAL_PROVISION"
    ORDINANCE = "ORDINANCE"
    EXECUTIVE_ORDER = "EXECUTIVE_ORDER"
    ADMINISTRATIVE_CODE = "ADMINISTRATIVE_CODE"
    TREATY = "TREATY"
    CONVENTION = "CONVENTION"
    
    # Legal Standards and Tests
    LEGAL_STANDARD = "LEGAL_STANDARD"
    BURDEN_OF_PROOF = "BURDEN_OF_PROOF"
    STANDARD_OF_REVIEW = "STANDARD_OF_REVIEW"
    TEST = "TEST"
    ELEMENT = "ELEMENT"
    FACTOR = "FACTOR"
    
    # Procedural Elements
    PROCEDURAL_RULE = "PROCEDURAL_RULE"
    CIVIL_PROCEDURE = "CIVIL_PROCEDURE"
    CRIMINAL_PROCEDURE = "CRIMINAL_PROCEDURE"
    APPELLATE_PROCEDURE = "APPELLATE_PROCEDURE"
    LOCAL_RULE = "LOCAL_RULE"
    STANDING_ORDER = "STANDING_ORDER"
    
    # Evidence
    EVIDENCE_TYPE = "EVIDENCE_TYPE"
    PHYSICAL_EVIDENCE = "PHYSICAL_EVIDENCE"
    DOCUMENTARY_EVIDENCE = "DOCUMENTARY_EVIDENCE"
    TESTIMONIAL_EVIDENCE = "TESTIMONIAL_EVIDENCE"
    DEMONSTRATIVE_EVIDENCE = "DEMONSTRATIVE_EVIDENCE"
    DIGITAL_EVIDENCE = "DIGITAL_EVIDENCE"
    HEARSAY = "HEARSAY"
    HEARSAY_EXCEPTION = "HEARSAY_EXCEPTION"
    
    # Claims and Causes of Action
    CAUSE_OF_ACTION = "CAUSE_OF_ACTION"
    CLAIM = "CLAIM"
    COUNT = "COUNT"
    CHARGE = "CHARGE"
    ALLEGATION = "ALLEGATION"
    DEFENSE = "DEFENSE"
    AFFIRMATIVE_DEFENSE = "AFFIRMATIVE_DEFENSE"
    COUNTERCLAIM = "COUNTERCLAIM"
    CROSS_CLAIM = "CROSS_CLAIM"
    
    # Damages and Remedies
    DAMAGES = "DAMAGES"
    COMPENSATORY_DAMAGES = "COMPENSATORY_DAMAGES"
    PUNITIVE_DAMAGES = "PUNITIVE_DAMAGES"
    STATUTORY_DAMAGES = "STATUTORY_DAMAGES"
    LIQUIDATED_DAMAGES = "LIQUIDATED_DAMAGES"
    NOMINAL_DAMAGES = "NOMINAL_DAMAGES"
    RELIEF_REQUESTED = "RELIEF_REQUESTED"
    INJUNCTION = "INJUNCTION"
    DECLARATORY_RELIEF = "DECLARATORY_RELIEF"
    EQUITABLE_RELIEF = "EQUITABLE_RELIEF"
    RESTITUTION = "RESTITUTION"
    
    # Legal Concepts and Doctrines
    LEGAL_CONCEPT = "LEGAL_CONCEPT"
    LEGAL_DOCTRINE = "LEGAL_DOCTRINE"
    PRECEDENT = "PRECEDENT"
    PRINCIPLE = "PRINCIPLE"
    LEGAL_THEORY = "LEGAL_THEORY"
    LEGAL_TERM = "LEGAL_TERM"
    LEGAL_DEFINITION = "LEGAL_DEFINITION"
    
    # Dates and Deadlines
    DATE = "DATE"
    FILING_DATE = "FILING_DATE"
    SERVICE_DATE = "SERVICE_DATE"
    HEARING_DATE = "HEARING_DATE"
    TRIAL_DATE = "TRIAL_DATE"
    DECISION_DATE = "DECISION_DATE"
    DEADLINE = "DEADLINE"
    STATUTE_OF_LIMITATIONS = "STATUTE_OF_LIMITATIONS"
    
    # Financial and Monetary
    MONETARY_AMOUNT = "MONETARY_AMOUNT"
    FEE = "FEE"
    FINE = "FINE"
    PENALTY = "PENALTY"
    AWARD = "AWARD"
    COST = "COST"
    BOND = "BOND"
    
    # Case Information
    CASE_NUMBER = "CASE_NUMBER"
    DOCKET_NUMBER = "DOCKET_NUMBER"
    CASE_CAPTION = "CASE_CAPTION"
    CASE_TYPE = "CASE_TYPE"
    CASE_STATUS = "CASE_STATUS"
    
    # Organizations and Entities
    CORPORATION = "CORPORATION"
    LLC = "LLC"
    PARTNERSHIP = "PARTNERSHIP"
    NONPROFIT = "NONPROFIT"
    TRUST = "TRUST"
    ESTATE = "ESTATE"
    UNION = "UNION"
    ASSOCIATION = "ASSOCIATION"
    
    # Intellectual Property
    PATENT = "PATENT"
    TRADEMARK = "TRADEMARK"
    COPYRIGHT = "COPYRIGHT"
    TRADE_SECRET = "TRADE_SECRET"
    
    # Criminal Law Specific
    OFFENSE = "OFFENSE"
    FELONY = "FELONY"
    MISDEMEANOR = "MISDEMEANOR"
    INFRACTION = "INFRACTION"
    SENTENCE = "SENTENCE"
    PROBATION = "PROBATION"
    PAROLE = "PAROLE"
    
    # Miscellaneous
    ADDRESS = "ADDRESS"
    EMAIL = "EMAIL"
    PHONE_NUMBER = "PHONE_NUMBER"
    BAR_NUMBER = "BAR_NUMBER"
    LEGAL_CITATION = "LEGAL_CITATION"


class CitationType(str, Enum):
    """Comprehensive legal citation types for classification."""
    
    # Case Citations
    CASE_CITATION = "CASE_CITATION"
    FEDERAL_CASE_CITATION = "FEDERAL_CASE_CITATION"
    STATE_CASE_CITATION = "STATE_CASE_CITATION"
    SUPREME_COURT_CITATION = "SUPREME_COURT_CITATION"
    APPELLATE_COURT_CITATION = "APPELLATE_COURT_CITATION"
    DISTRICT_COURT_CITATION = "DISTRICT_COURT_CITATION"
    BANKRUPTCY_COURT_CITATION = "BANKRUPTCY_COURT_CITATION"
    TAX_COURT_CITATION = "TAX_COURT_CITATION"
    MILITARY_COURT_CITATION = "MILITARY_COURT_CITATION"
    ADMINISTRATIVE_COURT_CITATION = "ADMINISTRATIVE_COURT_CITATION"
    UNPUBLISHED_CASE_CITATION = "UNPUBLISHED_CASE_CITATION"
    PARALLEL_CITATION = "PARALLEL_CITATION"
    SHORT_FORM_CITATION = "SHORT_FORM_CITATION"
    
    # Statutory Citations
    STATUTE_CITATION = "STATUTE_CITATION"
    FEDERAL_STATUTE_CITATION = "FEDERAL_STATUTE_CITATION"
    STATE_STATUTE_CITATION = "STATE_STATUTE_CITATION"
    USC_CITATION = "USC_CITATION"
    USCA_CITATION = "USCA_CITATION"
    STATE_CODE_CITATION = "STATE_CODE_CITATION"
    SESSION_LAW_CITATION = "SESSION_LAW_CITATION"
    PUBLIC_LAW_CITATION = "PUBLIC_LAW_CITATION"
    PRIVATE_LAW_CITATION = "PRIVATE_LAW_CITATION"
    
    # Regulatory Citations
    REGULATION_CITATION = "REGULATION_CITATION"
    CFR_CITATION = "CFR_CITATION"
    FEDERAL_REGISTER_CITATION = "FEDERAL_REGISTER_CITATION"
    STATE_REGULATION_CITATION = "STATE_REGULATION_CITATION"
    ADMINISTRATIVE_CODE_CITATION = "ADMINISTRATIVE_CODE_CITATION"
    EXECUTIVE_ORDER_CITATION = "EXECUTIVE_ORDER_CITATION"
    AGENCY_DECISION_CITATION = "AGENCY_DECISION_CITATION"
    ADMINISTRATIVE_RULING_CITATION = "ADMINISTRATIVE_RULING_CITATION"
    ADMINISTRATIVE_CITATION = "ADMINISTRATIVE_CITATION"  # Keep for backward compatibility
    
    # Constitutional Citations
    CONSTITUTIONAL_CITATION = "CONSTITUTIONAL_CITATION"
    US_CONSTITUTION_CITATION = "US_CONSTITUTION_CITATION"
    STATE_CONSTITUTION_CITATION = "STATE_CONSTITUTION_CITATION"
    AMENDMENT_CITATION = "AMENDMENT_CITATION"
    
    # Court Rules
    COURT_RULE_CITATION = "COURT_RULE_CITATION"
    FRCP_CITATION = "FRCP_CITATION"
    FRCRP_CITATION = "FRCRP_CITATION"
    FRE_CITATION = "FRE_CITATION"
    FRAP_CITATION = "FRAP_CITATION"
    FRBP_CITATION = "FRBP_CITATION"
    LOCAL_RULE_CITATION = "LOCAL_RULE_CITATION"
    STANDING_ORDER_CITATION = "STANDING_ORDER_CITATION"
    
    # Secondary Sources
    LAW_REVIEW_CITATION = "LAW_REVIEW_CITATION"
    LAW_JOURNAL_CITATION = "LAW_JOURNAL_CITATION"
    TREATISE_CITATION = "TREATISE_CITATION"
    HORNBOOK_CITATION = "HORNBOOK_CITATION"
    PRACTICE_GUIDE_CITATION = "PRACTICE_GUIDE_CITATION"
    LEGAL_ENCYCLOPEDIA_CITATION = "LEGAL_ENCYCLOPEDIA_CITATION"
    ALR_CITATION = "ALR_CITATION"
    RESTATEMENT_CITATION = "RESTATEMENT_CITATION"
    UNIFORM_LAW_CITATION = "UNIFORM_LAW_CITATION"
    MODEL_CODE_CITATION = "MODEL_CODE_CITATION"
    BOOK_CITATION = "BOOK_CITATION"
    
    # News and Media
    NEWSPAPER_CITATION = "NEWSPAPER_CITATION"
    MAGAZINE_CITATION = "MAGAZINE_CITATION"
    PRESS_RELEASE_CITATION = "PRESS_RELEASE_CITATION"
    NEWS_WIRE_CITATION = "NEWS_WIRE_CITATION"
    
    # Electronic Sources
    WEB_CITATION = "WEB_CITATION"
    BLOG_CITATION = "BLOG_CITATION"
    SOCIAL_MEDIA_CITATION = "SOCIAL_MEDIA_CITATION"
    DATABASE_CITATION = "DATABASE_CITATION"
    WESTLAW_CITATION = "WESTLAW_CITATION"
    LEXIS_CITATION = "LEXIS_CITATION"
    BLOOMBERG_LAW_CITATION = "BLOOMBERG_LAW_CITATION"
    
    # Legislative Materials
    CONGRESSIONAL_RECORD_CITATION = "CONGRESSIONAL_RECORD_CITATION"
    HOUSE_REPORT_CITATION = "HOUSE_REPORT_CITATION"
    SENATE_REPORT_CITATION = "SENATE_REPORT_CITATION"
    COMMITTEE_REPORT_CITATION = "COMMITTEE_REPORT_CITATION"
    HEARING_TRANSCRIPT_CITATION = "HEARING_TRANSCRIPT_CITATION"
    BILL_CITATION = "BILL_CITATION"
    RESOLUTION_CITATION = "RESOLUTION_CITATION"
    
    # International Sources
    TREATY_CITATION = "TREATY_CITATION"
    INTERNATIONAL_AGREEMENT_CITATION = "INTERNATIONAL_AGREEMENT_CITATION"
    FOREIGN_LAW_CITATION = "FOREIGN_LAW_CITATION"
    UN_DOCUMENT_CITATION = "UN_DOCUMENT_CITATION"
    ICJ_CITATION = "ICJ_CITATION"
    INTERNATIONAL_COURT_CITATION = "INTERNATIONAL_COURT_CITATION"
    
    # Practice Materials
    BRIEF_CITATION = "BRIEF_CITATION"
    MOTION_CITATION = "MOTION_CITATION"
    MEMORANDUM_CITATION = "MEMORANDUM_CITATION"
    OPINION_LETTER_CITATION = "OPINION_LETTER_CITATION"
    
    # Record Citations
    TRANSCRIPT_CITATION = "TRANSCRIPT_CITATION"
    DEPOSITION_CITATION = "DEPOSITION_CITATION"
    TRIAL_RECORD_CITATION = "TRIAL_RECORD_CITATION"
    APPELLATE_RECORD_CITATION = "APPELLATE_RECORD_CITATION"
    EXHIBIT_CITATION = "EXHIBIT_CITATION"
    
    # Specialized Citations
    PATENT_CITATION = "PATENT_CITATION"
    TRADEMARK_CITATION = "TRADEMARK_CITATION"
    COPYRIGHT_CITATION = "COPYRIGHT_CITATION"
    SEC_FILING_CITATION = "SEC_FILING_CITATION"
    IRS_CITATION = "IRS_CITATION"
    
    # Cross-References
    SUPRA_CITATION = "SUPRA_CITATION"
    INFRA_CITATION = "INFRA_CITATION"
    ID_CITATION = "ID_CITATION"
    IBID_CITATION = "IBID_CITATION"
    
    # Parenthetical Citations
    PARENTHETICAL_CITATION = "PARENTHETICAL_CITATION"
    EXPLANATORY_PARENTHETICAL = "EXPLANATORY_PARENTHETICAL"
    WEIGHT_OF_AUTHORITY_PARENTHETICAL = "WEIGHT_OF_AUTHORITY_PARENTHETICAL"
    
    # Signal Citations
    SEE_CITATION = "SEE_CITATION"
    SEE_ALSO_CITATION = "SEE_ALSO_CITATION"
    SEE_GENERALLY_CITATION = "SEE_GENERALLY_CITATION"
    CF_CITATION = "CF_CITATION"
    COMPARE_CITATION = "COMPARE_CITATION"
    CONTRA_CITATION = "CONTRA_CITATION"
    BUT_SEE_CITATION = "BUT_SEE_CITATION"
    ACCORD_CITATION = "ACCORD_CITATION"
    
    # Pinpoint Citations
    PAGE_CITATION = "PAGE_CITATION"
    PARAGRAPH_CITATION = "PARAGRAPH_CITATION"
    SECTION_CITATION = "SECTION_CITATION"
    FOOTNOTE_CITATION = "FOOTNOTE_CITATION"
    LINE_CITATION = "LINE_CITATION"


class ExtractionMethod(str, Enum):
    """Methods used for extraction in the hybrid workflow."""
    REGEX_ONLY = "regex_only"
    REGEX_WITH_AI_VALIDATION = "regex_with_ai_validation"
    REGEX_WITH_AI_ENHANCEMENT = "regex_with_ai_enhancement"
    AI_DISCOVERED = "ai_discovered"
    HYBRID_CONSENSUS = "hybrid_consensus"
    SPACY = "spacy"  # spaCy-based extraction with legal NER


class TextPosition(BaseModel):
    """Position information for extracted text in the source document."""
    
    start: int = Field(
        ..., 
        ge=0, 
        description="Character start position in source text"
    )
    end: int = Field(
        ..., 
        ge=0, 
        description="Character end position in source text"
    )
    line_number: Optional[int] = Field(
        None, 
        ge=1,
        description="Line number if available from source parsing"
    )
    context_start: Optional[int] = Field(
        None, 
        ge=0,
        description="Start position of broader context window"
    )
    context_end: Optional[int] = Field(
        None, 
        ge=0,
        description="End position of broader context window"
    )
    
    @validator('end')
    def validate_end_position(cls, v, values):
        """Ensure end position is greater than start position."""
        if 'start' in values and v <= values['start']:
            raise ValueError('End position must be greater than start position')
        return v
    
    @validator('context_end')
    def validate_context_end(cls, v, values):
        """Ensure context end is valid if provided."""
        if v is not None and 'context_start' in values and values['context_start'] is not None:
            if v <= values['context_start']:
                raise ValueError('Context end must be greater than context start')
        return v


class EntityAttributes(BaseModel):
    """Flexible attributes for legal entities with type-specific fields."""
    
    # Court-specific attributes
    court_name: Optional[str] = Field(None, description="Full court name")
    court_level: Optional[str] = Field(None, description="Court hierarchy level (trial, appellate, supreme)")
    jurisdiction: Optional[str] = Field(None, description="Geographic or subject matter jurisdiction")
    
    # Judge-specific attributes
    judge_title: Optional[str] = Field(None, description="Judicial title (Chief Justice, Justice, Judge)")
    judge_appointment_type: Optional[str] = Field(None, description="Appointment type (federal, state, elected)")
    
    # Party-specific attributes
    party_name: Optional[str] = Field(None, description="Full party name")
    party_type: Optional[str] = Field(None, description="Party role (plaintiff, defendant, appellant, etc.)")
    party_status: Optional[str] = Field(None, description="Legal status (individual, corporation, government)")
    
    # Attorney-specific attributes
    attorney_name: Optional[str] = Field(None, description="Attorney full name")
    law_firm: Optional[str] = Field(None, description="Law firm affiliation")
    bar_admission: Optional[str] = Field(None, description="Bar admission jurisdiction")
    
    # Document-specific attributes
    document_type: Optional[str] = Field(None, description="Type of legal document")
    document_title: Optional[str] = Field(None, description="Full document title")
    filing_date: Optional[str] = Field(None, description="Document filing or publication date")
    
    # Standard legal attributes
    bluebook_abbreviation: Optional[str] = Field(None, description="Standard Bluebook abbreviation")
    canonical_name: Optional[str] = Field(None, description="Standardized canonical name")
    alternate_names: List[str] = Field(default_factory=list, description="Known alternative names")
    
    # Flexible additional attributes
    additional_attributes: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional entity-specific attributes"
    )


class Entity(BaseModel):
    """Complete legal entity model with AI enhancements."""
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        description="Unique entity identifier"
    )
    text: str = Field(
        ..., 
        min_length=1,
        description="Original extracted text as found in document"
    )
    cleaned_text: str = Field(
        ..., 
        min_length=1,
        description="AI-refined and cleaned text with standardized formatting"
    )
    entity_type: EntityType = Field(
        ..., 
        description="Primary entity classification"
    )
    entity_subtype: str = Field(
        ..., 
        min_length=1,
        description="Detailed entity subclassification for fine-grained categorization"
    )
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Extraction confidence score (0.0 to 1.0)"
    )
    extraction_method: ExtractionMethod = Field(
        ..., 
        description="Method used for extraction in hybrid workflow"
    )
    position: TextPosition = Field(
        ..., 
        description="Position information in source text"
    )
    attributes: EntityAttributes = Field(
        default_factory=EntityAttributes, 
        description="Entity-specific attributes and metadata"
    )
    ai_enhancements: List[str] = Field(
        default_factory=list, 
        description="List of AI enhancements applied to this entity"
    )
    context_snippet: Optional[str] = Field(
        None, 
        max_length=1000,
        description="Surrounding text context for validation"
    )
    validation_notes: List[str] = Field(
        default_factory=list, 
        description="Validation and correction notes from AI processing"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Entity extraction timestamp"
    )
    
    @validator('text', 'cleaned_text')
    def validate_text_fields(cls, v):
        """Validate text fields are not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError('Text fields cannot be empty or whitespace only')
        return v.strip()


class CitationComponents(BaseModel):
    """Structured components of a legal citation for Bluebook compliance."""
    
    # Case citation components
    case_name: Optional[str] = Field(None, description="Case name (parties)")
    volume: Optional[str] = Field(None, description="Reporter volume number")
    reporter: Optional[str] = Field(None, description="Reporter abbreviation")
    page: Optional[str] = Field(None, description="Starting page number")
    pincite: Optional[str] = Field(None, description="Specific page reference")
    court: Optional[str] = Field(None, description="Court abbreviation")
    year: Optional[str] = Field(None, description="Decision year")
    
    # Statute citation components
    title: Optional[str] = Field(None, description="Title number or name")
    code: Optional[str] = Field(None, description="Code abbreviation (USC, CFR, etc.)")
    section: Optional[str] = Field(None, description="Section number")
    subsection: Optional[str] = Field(None, description="Subsection designation")
    
    # Law review and periodical components
    author: Optional[str] = Field(None, description="Author name(s)")
    article_title: Optional[str] = Field(None, description="Article or chapter title")
    journal: Optional[str] = Field(None, description="Journal or publication name")
    
    # Book and treatise components
    edition: Optional[str] = Field(None, description="Edition number")
    publisher: Optional[str] = Field(None, description="Publisher name")
    supplement: Optional[str] = Field(None, description="Supplement information")
    
    # Web and electronic components
    url: Optional[str] = Field(None, description="Web URL if applicable")
    access_date: Optional[str] = Field(None, description="Date of access for web sources")
    
    # Additional structured components
    additional_components: Dict[str, str] = Field(
        default_factory=dict, 
        description="Additional citation components not covered above"
    )


class Citation(BaseModel):
    """Complete legal citation model with Bluebook compliance validation."""
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        description="Unique citation identifier"
    )
    original_text: str = Field(
        ..., 
        min_length=1,
        description="Original citation text as found in document"
    )
    cleaned_citation: str = Field(
        ..., 
        min_length=1,
        description="Bluebook-compliant cleaned and formatted citation"
    )
    citation_type: CitationType = Field(
        ..., 
        description="Type of legal citation"
    )
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Extraction confidence score (0.0 to 1.0)"
    )
    extraction_method: ExtractionMethod = Field(
        ..., 
        description="Method used for extraction in hybrid workflow"
    )
    position: TextPosition = Field(
        ..., 
        description="Position information in source text"
    )
    components: CitationComponents = Field(
        default_factory=CitationComponents, 
        description="Parsed citation components for structured access"
    )
    bluebook_compliant: bool = Field(
        ..., 
        description="Whether citation meets Bluebook formatting standards"
    )
    parallel_citations: List[str] = Field(
        default_factory=list, 
        description="Parallel citation forms in other reporters"
    )
    ai_enhancements: List[str] = Field(
        default_factory=list, 
        description="List of AI enhancements applied to this citation"
    )
    validation_notes: List[str] = Field(
        default_factory=list, 
        description="Validation and correction notes from AI processing"
    )
    authority_weight: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Legal authority weight for this citation"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Citation extraction timestamp"
    )
    
    @validator('original_text', 'cleaned_citation')
    def validate_citation_text(cls, v):
        """Validate citation text fields are not empty."""
        if not v or not v.strip():
            raise ValueError('Citation text fields cannot be empty or whitespace only')
        return v.strip()


class EntityRelationship(BaseModel):
    """Relationship between legal entities with confidence scoring."""
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        description="Unique relationship identifier"
    )
    source_entity_id: str = Field(
        ..., 
        description="Source entity UUID"
    )
    target_entity_id: str = Field(
        ..., 
        description="Target entity UUID"
    )
    relationship_type: str = Field(
        ..., 
        min_length=1,
        description="Type of relationship (e.g., 'represented_by', 'decided_by', 'cited_in')"
    )
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Relationship confidence score (0.0 to 1.0)"
    )
    evidence_text: Optional[str] = Field(
        None, 
        max_length=2000,
        description="Text evidence supporting this relationship"
    )
    context_snippet: Optional[str] = Field(
        None,
        max_length=1000, 
        description="Surrounding context where relationship was identified"
    )
    extraction_method: ExtractionMethod = Field(
        ...,
        description="Method used to extract this relationship"
    )
    relationship_attributes: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional relationship-specific data and metadata"
    )
    bidirectional: bool = Field(
        False,
        description="Whether this relationship applies in both directions"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Relationship extraction timestamp"
    )
    
    @validator('source_entity_id', 'target_entity_id')
    def validate_entity_ids(cls, v):
        """Validate entity IDs are valid UUIDs."""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('Entity IDs must be valid UUID strings')
        return v
    
    @validator('target_entity_id')
    def validate_different_entities(cls, v, values):
        """Ensure source and target entities are different."""
        if 'source_entity_id' in values and v == values['source_entity_id']:
            raise ValueError('Source and target entities must be different')
        return v