"""
Entity Types Routes for Entity Extraction Service

Provides endpoints to retrieve available entity and citation types
for use by other services like GraphRAG.
"""

import logging
from typing import Dict, List, Any
from fastapi import APIRouter, Request, HTTPException, Query, Response
from fastapi import Path as PathParam
from pydantic import BaseModel, Field

# CLAUDE.md Compliant: Absolute import
from src.models.entities import EntityType, CitationType

logger = logging.getLogger(__name__)

router = APIRouter()


class EntityTypeInfo(BaseModel):
    """Information about a specific entity type."""
    type: str = Field(..., description="Entity type enum value")
    name: str = Field(..., description="Human-readable name")
    category: str = Field(..., description="Category grouping")
    description: str = Field(..., description="Description of the entity type")
    regex_supported: bool = Field(..., description="Whether regex patterns exist for this type")
    ai_enhanced: bool = Field(..., description="Whether AI enhancement is available")
    pattern_count: int = Field(0, description="Number of regex patterns for this type")
    pattern_examples: List[str] = Field(default_factory=list, description="Example regex patterns")
    examples: List[str] = Field(default_factory=list, description="Real-world examples of this entity type")


class CitationTypeInfo(BaseModel):
    """Information about a specific citation type."""
    type: str = Field(..., description="Citation type enum value")
    name: str = Field(..., description="Human-readable name")
    category: str = Field(..., description="Category grouping")
    description: str = Field(..., description="Description of the citation type")
    regex_supported: bool = Field(..., description="Whether regex patterns exist for this type")
    examples: List[str] = Field(default_factory=list, description="Example citations")
    pattern_count: int = Field(0, description="Number of regex patterns for this type")
    pattern_examples: List[str] = Field(default_factory=list, description="Example regex patterns")


class EntityTypesResponse(BaseModel):
    """Response containing all available entity and citation types."""
    entity_types: List[EntityTypeInfo] = Field(..., description="List of entity types")
    citation_types: List[CitationTypeInfo] = Field(..., description="List of citation types")
    total_entity_types: int = Field(..., description="Total number of entity types")
    total_citation_types: int = Field(..., description="Total number of citation types")
    categories: Dict[str, List[str]] = Field(..., description="Types grouped by category")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


def categorize_entity_type(entity_type: str) -> str:
    """Categorize an entity type based on its name."""
    
    # Courts and Judicial
    if entity_type in ["COURT", "JUDGE", "MAGISTRATE", "ARBITRATOR", "MEDIATOR", 
                       "SPECIAL_MASTER", "COURT_CLERK", "COURT_REPORTER"]:
        return "Courts and Judicial"
    
    # Parties and Representatives
    elif entity_type in ["PARTY", "PLAINTIFF", "DEFENDANT", "APPELLANT", "APPELLEE",
                         "PETITIONER", "RESPONDENT", "INTERVENOR", "AMICUS_CURIAE",
                         "THIRD_PARTY", "CLASS_REPRESENTATIVE"]:
        return "Parties and Representatives"
    
    # Legal Professionals
    elif entity_type in ["ATTORNEY", "LAW_FIRM", "PROSECUTOR", "PUBLIC_DEFENDER",
                         "LEGAL_AID", "PARALEGAL", "EXPERT_WITNESS", "LAY_WITNESS"]:
        return "Legal Professionals"
    
    # Government and Agencies
    elif entity_type in ["GOVERNMENT_ENTITY", "FEDERAL_AGENCY", "STATE_AGENCY",
                         "LOCAL_AGENCY", "REGULATORY_BODY", "LEGISLATIVE_BODY",
                         "EXECUTIVE_OFFICE"]:
        return "Government and Agencies"
    
    # Documents and Filings
    elif entity_type in ["DOCUMENT", "MOTION", "BRIEF", "COMPLAINT", "ANSWER",
                         "DISCOVERY_DOCUMENT", "DEPOSITION", "INTERROGATORY",
                         "AFFIDAVIT", "DECLARATION", "EXHIBIT", "TRANSCRIPT",
                         "ORDER", "JUDGMENT", "VERDICT", "SETTLEMENT",
                         "CONTRACT", "AGREEMENT"]:
        return "Documents and Filings"
    
    # Jurisdictions and Venues
    elif entity_type in ["JURISDICTION", "FEDERAL_JURISDICTION", "STATE_JURISDICTION",
                         "VENUE", "FORUM", "DISTRICT", "CIRCUIT", "DIVISION"]:
        return "Jurisdictions and Venues"
    
    # Legal Authority
    elif entity_type in ["STATUTE", "REGULATION", "CASE_LAW", "CONSTITUTIONAL_PROVISION",
                         "ORDINANCE", "EXECUTIVE_ORDER", "ADMINISTRATIVE_CODE",
                         "TREATY", "CONVENTION"]:
        return "Legal Authority"
    
    # Legal Standards and Tests
    elif entity_type in ["LEGAL_STANDARD", "BURDEN_OF_PROOF", "STANDARD_OF_REVIEW",
                         "TEST", "ELEMENT", "FACTOR"]:
        return "Legal Standards and Tests"
    
    # Procedural Elements
    elif entity_type in ["PROCEDURAL_RULE", "CIVIL_PROCEDURE", "CRIMINAL_PROCEDURE",
                         "APPELLATE_PROCEDURE", "LOCAL_RULE", "STANDING_ORDER"]:
        return "Procedural Elements"
    
    # Evidence
    elif entity_type in ["EVIDENCE_TYPE", "PHYSICAL_EVIDENCE", "DOCUMENTARY_EVIDENCE",
                         "TESTIMONIAL_EVIDENCE", "DEMONSTRATIVE_EVIDENCE",
                         "DIGITAL_EVIDENCE", "HEARSAY", "HEARSAY_EXCEPTION"]:
        return "Evidence"
    
    # Claims and Causes of Action
    elif entity_type in ["CAUSE_OF_ACTION", "CLAIM", "COUNT", "CHARGE", "ALLEGATION",
                         "DEFENSE", "AFFIRMATIVE_DEFENSE", "COUNTERCLAIM", "CROSS_CLAIM"]:
        return "Claims and Causes of Action"
    
    # Damages and Remedies
    elif entity_type in ["DAMAGES", "COMPENSATORY_DAMAGES", "PUNITIVE_DAMAGES",
                         "STATUTORY_DAMAGES", "LIQUIDATED_DAMAGES", "NOMINAL_DAMAGES",
                         "RELIEF_REQUESTED", "INJUNCTION", "DECLARATORY_RELIEF",
                         "EQUITABLE_RELIEF", "RESTITUTION"]:
        return "Damages and Remedies"
    
    # Legal Concepts and Doctrines
    elif entity_type in ["LEGAL_CONCEPT", "LEGAL_DOCTRINE", "PRECEDENT", "PRINCIPLE",
                         "LEGAL_THEORY", "LEGAL_TERM", "LEGAL_DEFINITION"]:
        return "Legal Concepts and Doctrines"
    
    # Dates and Deadlines
    elif entity_type in ["DATE", "FILING_DATE", "SERVICE_DATE", "HEARING_DATE",
                         "TRIAL_DATE", "DECISION_DATE", "DEADLINE",
                         "STATUTE_OF_LIMITATIONS"]:
        return "Dates and Deadlines"
    
    # Financial and Monetary
    elif entity_type in ["MONETARY_AMOUNT", "FEE", "FINE", "PENALTY", "AWARD",
                         "COST", "BOND"]:
        return "Financial and Monetary"
    
    # Case Information
    elif entity_type in ["CASE_NUMBER", "DOCKET_NUMBER", "CASE_CAPTION",
                         "CASE_TYPE", "CASE_STATUS"]:
        return "Case Information"
    
    # Organizations and Entities
    elif entity_type in ["CORPORATION", "LLC", "PARTNERSHIP", "NONPROFIT",
                         "TRUST", "ESTATE", "UNION", "ASSOCIATION"]:
        return "Organizations and Entities"
    
    # Intellectual Property
    elif entity_type in ["PATENT", "TRADEMARK", "COPYRIGHT", "TRADE_SECRET"]:
        return "Intellectual Property"
    
    # Criminal Law Specific
    elif entity_type in ["OFFENSE", "FELONY", "MISDEMEANOR", "INFRACTION",
                         "SENTENCE", "PROBATION", "PAROLE"]:
        return "Criminal Law Specific"
    
    # Miscellaneous
    else:
        return "Miscellaneous"


def categorize_citation_type(citation_type: str) -> str:
    """Categorize a citation type based on its name."""
    
    if "CASE" in citation_type or citation_type in ["PARALLEL_CITATION", "SHORT_FORM_CITATION"]:
        return "Case Citations"
    elif "STATUTE" in citation_type or "USC" in citation_type or "LAW" in citation_type:
        return "Statutory Citations"
    elif "REGULATION" in citation_type or "CFR" in citation_type or "ADMINISTRATIVE" in citation_type:
        return "Regulatory Citations"
    elif "CONSTITUTION" in citation_type or "AMENDMENT" in citation_type:
        return "Constitutional Citations"
    elif "RULE" in citation_type or citation_type.startswith("FR"):
        return "Court Rules"
    elif any(x in citation_type for x in ["REVIEW", "JOURNAL", "TREATISE", "HORNBOOK", 
                                           "ENCYCLOPEDIA", "ALR", "RESTATEMENT", "UNIFORM"]):
        return "Secondary Sources"
    elif any(x in citation_type for x in ["NEWS", "MAGAZINE", "PRESS"]):
        return "News and Media"
    elif any(x in citation_type for x in ["WEB", "BLOG", "SOCIAL", "DATABASE", "WESTLAW", "LEXIS"]):
        return "Electronic Sources"
    elif any(x in citation_type for x in ["INTERNATIONAL", "TREATY", "CONVENTION", "FOREIGN"]):
        return "International Sources"
    elif any(x in citation_type for x in ["HEARING", "TESTIMONY", "REPORT", "CONGRESSIONAL"]):
        return "Legislative Materials"
    elif any(x in citation_type for x in ["BRIEF", "RECORD", "PLEADING", "MOTION"]):
        return "Court Documents"
    else:
        return "Other Citations"


def get_entity_description(entity_type: str, pattern_loader=None) -> str:
    """Get a description for an entity type from PatternLoader or fallback."""
    # Try to get from PatternLoader first
    if pattern_loader:
        try:
            entity_info = pattern_loader.get_entity_type_info(entity_type)
            if entity_info and entity_info.get("description"):
                return entity_info["description"]
        except Exception:
            pass
    
    # Fallback descriptions for common types
    descriptions = {
        "COURT": "Court names and identifiers",
        "JUDGE": "Judicial officers including judges and justices",
        "ATTORNEY": "Legal representatives and counsel",
        "PARTY": "Parties involved in legal proceedings",
        "STATUTE": "Legislative enactments and statutes",
        "CASE_LAW": "Judicial decisions and precedents",
        "DOCUMENT": "Legal documents and filings",
        "JURISDICTION": "Jurisdictional references",
        "DAMAGES": "Monetary damages and compensation",
        "DATE": "Temporal references and deadlines",
        "CORPORATION": "Business entities and organizations",
        # Add more as needed
    }
    return descriptions.get(entity_type, f"Legal entity of type {entity_type.replace('_', ' ').lower()}")


def get_citation_description(citation_type: str, pattern_loader=None) -> str:
    """Get a description for a citation type from PatternLoader or fallback."""
    # Try to get from PatternLoader first
    if pattern_loader:
        try:
            citation_info = pattern_loader.get_entity_type_info(citation_type)
            if citation_info and citation_info.get("description"):
                return citation_info["description"]
        except Exception:
            pass
    
    # Fallback descriptions
    descriptions = {
        "CASE_CITATION": "General case law citations",
        "FEDERAL_CASE_CITATION": "Federal court case citations",
        "STATE_CASE_CITATION": "State court case citations",
        "STATUTE_CITATION": "Legislative statute citations",
        "USC_CITATION": "United States Code citations",
        "CFR_CITATION": "Code of Federal Regulations citations",
        "CONSTITUTIONAL_CITATION": "Constitutional provision citations",
        # Add more as needed
    }
    return descriptions.get(citation_type, f"Citation of type {citation_type.replace('_', ' ').lower()}")


@router.get("/entity-types",
    response_model=EntityTypesResponse,
    deprecated=True,
    summary="[DEPRECATED] Get All Supported Entity and Citation Types",
    description="""
    **⚠️ DEPRECATED**: This endpoint is deprecated and will be removed in version 3.0.0.

    **Migration Guide**:
    - **Old**: `GET /api/v1/entity-types`
    - **New**: `GET /api/v1/patterns?type=entities&include_examples=true`

    **Removal Date**: January 1, 2026

    **Why Deprecated**: This endpoint has been superseded by the unified `/api/v1/patterns`
    endpoint which provides better performance, more flexible filtering, and consistent
    response formats across all pattern types.

    ---

    **Comprehensive Entity Type Discovery**

    This endpoint provides complete information about all legal entity and citation types
    supported by the extraction service, organized by semantic categories.

    ### What's Included
    - **31+ Legal Entity Types**: Courts, judges, attorneys, parties, documents, etc.
    - **25+ Citation Types**: Case law, statutes, regulations, secondary sources, etc.
    - **Categorical Organization**: Entities grouped by legal domain and function
    - **Pattern Coverage**: Which entity types have regex patterns available
    - **AI Enhancement**: Which types support AI-powered extraction

    ### Entity Categories
    - **Courts and Judicial**: Courts, judges, magistrates, arbitrators
    - **Legal Professionals**: Attorneys, law firms, expert witnesses
    - **Parties**: Plaintiffs, defendants, appellants, intervenors
    - **Legal Authority**: Statutes, regulations, case law, constitutional provisions
    - **Documents**: Motions, briefs, orders, contracts, evidence
    - **Procedural Elements**: Rules, standards, tests, burdens of proof

    ### Citation Categories
    - **Case Citations**: Federal and state court decisions
    - **Statutory Citations**: USC, state codes, local ordinances
    - **Regulatory Citations**: CFR, administrative codes
    - **Secondary Sources**: Law reviews, treatises, encyclopedias
    - **Court Documents**: Briefs, records, pleadings

    ### Query Parameters
    - `include_descriptions`: Add human-readable descriptions for each type
    - `include_examples`: Include example patterns and sample citations

    ### Use Cases
    - **Service Integration**: Discover available entity types for GraphRAG and other services
    - **UI Development**: Populate dropdowns and filters with supported types
    - **Documentation**: Generate comprehensive entity type documentation
    - **Quality Assurance**: Verify pattern coverage across all entity types
    """,
    responses={
        200: {
            "description": "Entity types retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "total_entity_types": 31,
                        "total_citation_types": 25,
                        "entity_types": [
                            {
                                "type": "COURT",
                                "name": "Court",
                                "category": "Courts and Judicial",
                                "description": "Court names and identifiers",
                                "regex_supported": True,
                                "ai_enhanced": True,
                                "pattern_count": 12,
                                "pattern_examples": ["U.S. District Court", "Supreme Court of"]
                            }
                        ],
                        "categories": {
                            "Courts and Judicial": ["COURT", "JUDGE", "MAGISTRATE"],
                            "Citation: Case Citations": ["CASE_CITATION", "FEDERAL_CASE_CITATION"]
                        },
                        "metadata": {
                            "service_version": "2.0.0",
                            "total_patterns_in_use": 295,
                            "ai_enhancement_available": True
                        }
                    }
                }
            }
        }
    }
)
async def get_entity_types(
    fastapi_request: Request,
    response: Response,
    include_descriptions: bool = Query(True, description="Include human-readable descriptions for each entity type"),
    include_examples: bool = Query(False, description="Include example patterns and sample texts for each type")
):
    # Add deprecation headers
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Tue, 01 Jan 2026 00:00:00 GMT"
    response.headers["Link"] = '</api/v1/patterns>; rel="successor-version"'

    # Log deprecation warning
    logger.warning(
        "DEPRECATED endpoint /api/v1/entity-types accessed. "
        "Use /api/v1/patterns?type=entities instead. "
        "This endpoint will be removed on 2026-01-01."
    )

    try:
        # Get pattern loader from app state
        pattern_loader = getattr(fastapi_request.app.state, "pattern_loader", None)
        
        # Get pattern statistics if available
        pattern_stats = None
        if pattern_loader:
            try:
                pattern_stats = pattern_loader.get_pattern_statistics()
            except Exception as e:
                logger.warning(f"Could not get pattern statistics: {e}")
        
        # Get all entity types
        entity_types_list = []
        
        # Get entity type info from PatternLoader if available
        entity_info_from_loader = {}
        if pattern_loader:
            try:
                entity_info_from_loader = pattern_loader.get_all_entity_types_info()
                logger.debug(f"Got entity info for {len(entity_info_from_loader)} types from PatternLoader")
                # Log first few types to see what we got
                sample_types = list(entity_info_from_loader.keys())[:10]
                logger.debug(f"Sample types from loader: {sample_types}")
                # Check a specific example
                if 'MAGISTRATE' in entity_info_from_loader:
                    logger.debug(f"MAGISTRATE info: {entity_info_from_loader['MAGISTRATE']}")
                else:
                    logger.debug("MAGISTRATE not found in entity_info_from_loader")
            except Exception as e:
                logger.warning(f"Could not get entity type info from PatternLoader: {e}")
        
        for entity_type in EntityType:
            category = categorize_entity_type(entity_type.value)
            
            # Get info from PatternLoader or use defaults
            loader_info = entity_info_from_loader.get(entity_type.value, {})
            pattern_count = loader_info.get("pattern_count", 0)
            pattern_examples = []
            entity_examples = loader_info.get("examples", [])  # Real-world examples of the entity type
            
            # Get pattern examples if requested
            if include_examples:
                # Get actual pattern regex strings for pattern_examples field
                if pattern_loader:
                    try:
                        # Get pattern strings for showing regex examples
                        patterns = pattern_loader.get_patterns_by_entity_type(entity_type.value)
                        for p in patterns[:3]:
                            pattern_str = p.pattern if len(p.pattern) <= 100 else p.pattern[:97] + "..."
                            pattern_examples.append(pattern_str)
                    except Exception as e:
                        logger.debug(f"Could not get patterns for {entity_type.value}: {e}")
            
            # Get description from PatternLoader or use fallback
            description = ""
            if include_descriptions:
                if loader_info.get("description"):
                    description = loader_info["description"]
                else:
                    description = get_entity_description(entity_type.value, pattern_loader)
            
            entity_types_list.append(EntityTypeInfo(
                type=entity_type.value,
                name=entity_type.value.replace("_", " ").title(),
                category=category,
                description=description,
                regex_supported=pattern_count > 0,  # Based on actual patterns
                ai_enhanced=category not in ["Dates and Deadlines", "Financial and Monetary"],
                pattern_count=pattern_count,
                pattern_examples=pattern_examples if include_examples else [],
                examples=entity_examples[:5] if include_examples else []  # Show up to 5 real-world examples
            ))
        
        # Get all citation types
        citation_types_list = []
        
        # Get citation types from PatternLoader if available
        citation_types_from_loader = []
        if pattern_loader:
            try:
                citation_types_from_loader = pattern_loader.get_citation_types()
            except Exception as e:
                logger.warning(f"Could not get citation types from PatternLoader: {e}")
        
        for citation_type in CitationType:
            category = categorize_citation_type(citation_type.value)
            
            # Get info from PatternLoader
            loader_info = {}
            if pattern_loader and citation_type.value in citation_types_from_loader:
                try:
                    loader_info = pattern_loader.get_entity_type_info(citation_type.value)
                except Exception as e:
                    logger.debug(f"Could not get info for {citation_type.value}: {e}")
            
            pattern_count = loader_info.get("pattern_count", 0)
            pattern_examples = []
            examples = []
            
            # Get examples
            if include_examples:
                # Use actual examples from patterns if available
                if loader_info.get("examples"):
                    examples = loader_info["examples"][:5]
                else:
                    # Fallback to hardcoded examples for common types
                    if citation_type.value == "CASE_CITATION":
                        examples = ["Brown v. Board of Education, 347 U.S. 483 (1954)"]
                    elif citation_type.value == "USC_CITATION":
                        examples = ["42 U.S.C. § 1983", "18 U.S.C. § 1001"]
                    elif citation_type.value == "CFR_CITATION":
                        examples = ["40 C.F.R. § 1500.1", "29 C.F.R. § 1910.1200"]
                
                # Get pattern examples if no real examples available
                if not examples and pattern_loader:
                    try:
                        patterns = pattern_loader.get_patterns_by_entity_type(citation_type.value)
                        for p in patterns[:3]:
                            pattern_str = p.pattern if len(p.pattern) <= 100 else p.pattern[:97] + "..."
                            pattern_examples.append(pattern_str)
                    except Exception as e:
                        logger.debug(f"Could not get patterns for {citation_type.value}: {e}")
            
            # Get description from PatternLoader or use fallback
            description = ""
            if include_descriptions:
                if loader_info.get("description"):
                    description = loader_info["description"]
                else:
                    description = get_citation_description(citation_type.value, pattern_loader)
            
            citation_types_list.append(CitationTypeInfo(
                type=citation_type.value,
                name=citation_type.value.replace("_", " ").title(),
                category=category,
                description=description,
                regex_supported=pattern_count > 0,  # Based on actual patterns
                examples=examples,
                pattern_count=pattern_count,
                pattern_examples=pattern_examples if include_examples else []
            ))
        
        # Group by categories
        categories = {}
        
        # Group entity types by category
        for entity_info in entity_types_list:
            if entity_info.category not in categories:
                categories[entity_info.category] = []
            categories[entity_info.category].append(entity_info.type)
        
        # Group citation types by category (prefix with "Citation: ")
        for citation_info in citation_types_list:
            category_key = f"Citation: {citation_info.category}"
            if category_key not in categories:
                categories[category_key] = []
            categories[category_key].append(citation_info.type)
        
        # Prepare metadata
        metadata = {
            "service_version": "2.0.0",
            "extraction_modes": ["regex", "ai_enhanced", "hybrid"],
            "supported_languages": ["en"],
            "max_document_size_mb": 50,
            "total_entity_citation_types": len(entity_types_list) + len(citation_types_list),
            "ai_enhancement_available": True
        }
        
        # Add PatternLoader statistics if available
        if pattern_stats:
            metadata.update({
                "pattern_loader_stats": {
                    "total_patterns_loaded": pattern_stats.get("total_patterns", 0),
                    "total_pattern_groups": pattern_stats.get("total_groups", 0),
                    "total_entity_types_with_patterns": pattern_stats.get("total_entity_types", 0),
                    "patterns_by_source": pattern_stats.get("patterns_by_source", {}),
                    "top_entity_types": pattern_stats.get("top_entity_types", [])
                }
            })
            
            # Calculate actual patterns in use
            total_patterns_in_use = sum(et.pattern_count for et in entity_types_list) + \
                                   sum(ct.pattern_count for ct in citation_types_list)
            metadata["total_patterns_in_use"] = total_patterns_in_use
        
        # Log the request
        log_client = getattr(fastapi_request.app.state, "log_client", None)
        if log_client:
            await log_client.log(
                level="INFO",
                message="Entity types requested",
                service="entity-extraction-service",
                request_id=getattr(fastapi_request.state, "request_id", ""),
                metadata={
                    "include_descriptions": include_descriptions,
                    "include_examples": include_examples,
                    "total_entity_types": len(entity_types_list),
                    "total_citation_types": len(citation_types_list)
                }
            )
        
        return EntityTypesResponse(
            entity_types=entity_types_list,
            citation_types=citation_types_list,
            total_entity_types=len(entity_types_list),
            total_citation_types=len(citation_types_list),
            categories=categories,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Failed to get entity types: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve entity types: {str(e)}"
        )


@router.get("/entity-types/categories")
async def get_entity_categories(fastapi_request: Request):
    """
    Get a summary of entity type categories.
    
    Returns:
        Dict: Categories with counts and basic information
    """
    try:
        # Count entities by category
        entity_categories = {}
        for entity_type in EntityType:
            category = categorize_entity_type(entity_type.value)
            if category not in entity_categories:
                entity_categories[category] = {
                    "count": 0,
                    "types": [],
                    "has_regex": True,
                    "has_ai_enhancement": category not in ["Dates and Deadlines", "Financial and Monetary"]
                }
            entity_categories[category]["count"] += 1
            entity_categories[category]["types"].append(entity_type.value)
        
        # Count citations by category
        citation_categories = {}
        for citation_type in CitationType:
            category = categorize_citation_type(citation_type.value)
            if category not in citation_categories:
                citation_categories[category] = {
                    "count": 0,
                    "types": [],
                    "has_regex": True,
                    "has_ai_enhancement": True
                }
            citation_categories[category]["count"] += 1
            citation_categories[category]["types"].append(citation_type.value)
        
        return {
            "entity_categories": entity_categories,
            "citation_categories": citation_categories,
            "total_entity_categories": len(entity_categories),
            "total_citation_categories": len(citation_categories),
            "total_types": len(EntityType) + len(CitationType)
        }
        
    except Exception as e:
        logger.error(f"Failed to get entity categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve entity categories: {str(e)}"
        )


@router.get("/entity-types/{entity_type}",
    summary="Get Detailed Entity Type Information",
    description="""
    **Deep Dive into Specific Entity Types**
    
    Get comprehensive details about a specific legal entity or citation type, 
    including pattern information, AI enhancement capabilities, and examples.
    
    ### What You Get
    - **Entity Classification**: Whether it's an entity or citation type
    - **Category Assignment**: Legal domain and functional grouping  
    - **Pattern Details**: Available regex patterns with confidence scores
    - **AI Enhancement**: Whether AI processing is available for this type
    - **Extraction Modes**: Supported extraction methods (regex, AI, hybrid)
    - **Usage Examples**: Sample patterns and matching examples
    
    ### Entity Type Examples
    - `COURT`: Court names, jurisdictions, and legal venues
    - `JUDGE`: Judicial officers, justices, and magistrates  
    - `CASE_CITATION`: Legal case references and parallel citations
    - `STATUTE`: Legislative statutes and regulatory citations
    - `ATTORNEY`: Legal counsel and law firm references
    
    ### Pattern Information
    For each entity type, you'll see:
    - Number of available regex patterns
    - Pattern confidence scores (0.0-1.0)
    - Example pattern strings (truncated for readability)
    - Source files where patterns are defined
    
    ### Response Details
    The response includes categorical information, pattern statistics, 
    and capability flags to help integrate with other services.
    """,
    responses={
        200: {
            "description": "Entity type details retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "type": "COURT",
                        "name": "Court",
                        "category": "Courts and Judicial",
                        "description": "Court names and identifiers",
                        "is_entity": True,
                        "is_citation": False,
                        "regex_supported": True,
                        "ai_enhanced": True,
                        "extraction_modes": ["regex", "ai_enhanced", "hybrid"],
                        "pattern_count": 12,
                        "pattern_details": [
                            {
                                "name": "us_district_court",
                                "pattern": "U\\.S\\. District Court",
                                "confidence": 0.95,
                                "examples": ["U.S. District Court for the Southern District of New York"]
                            }
                        ]
                    }
                }
            }
        },
        404: {
            "description": "Entity type not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Entity type 'UNKNOWN_TYPE' not found"
                    }
                }
            }
        }
    }
)
async def get_entity_type_details(
    fastapi_request: Request,
    entity_type: str = PathParam(..., description="The entity or citation type to get details for (e.g., 'COURT', 'CASE_CITATION')")
):
    # Get pattern loader from app state
    pattern_loader = getattr(fastapi_request.app.state, "pattern_loader", None)
    
    # Check if it's an entity type
    entity_found = False
    entity_info = None
    
    try:
        entity_enum = EntityType(entity_type)
        entity_found = True
        category = categorize_entity_type(entity_type)
        
        # Get comprehensive info from PatternLoader
        loader_info = {}
        if pattern_loader:
            try:
                loader_info = pattern_loader.get_entity_type_info(entity_type)
            except Exception as e:
                logger.debug(f"Could not get entity info from PatternLoader: {e}")
        
        # Get pattern details
        pattern_count = loader_info.get("pattern_count", 0)
        pattern_details = []
        
        if pattern_loader and pattern_count > 0:
            try:
                patterns = pattern_loader.get_patterns_by_entity_type(entity_type)
                
                # Get detailed pattern information
                for p in patterns[:10]:  # Limit to first 10 patterns for detail view
                    pattern_details.append({
                        "name": p.name,
                        "pattern": p.pattern if len(p.pattern) <= 200 else p.pattern[:197] + "...",
                        "confidence": p.confidence,
                        "examples": p.examples[:3] if p.examples else []
                    })
            except Exception as e:
                logger.debug(f"Could not get patterns for {entity_type}: {e}")
        
        # Build response using PatternLoader data
        entity_info = {
            "type": entity_type,
            "name": entity_type.replace("_", " ").title(),
            "category": category,
            "description": loader_info.get("description") or get_entity_description(entity_type, pattern_loader),
            "is_entity": True,
            "is_citation": False,
            "regex_supported": pattern_count > 0,
            "ai_enhanced": category not in ["Dates and Deadlines", "Financial and Monetary"],
            "extraction_modes": ["regex", "ai_enhanced", "hybrid"],
            "pattern_count": pattern_count,
            "pattern_details": pattern_details,
            "examples": loader_info.get("examples", [])[:10],  # Add real examples
            "average_confidence": loader_info.get("average_confidence", 0.0),
            "jurisdictions": loader_info.get("jurisdictions", []),
            "pattern_types": loader_info.get("pattern_types", [])
        }
    except ValueError:
        pass
    
    # Check if it's a citation type
    if not entity_found:
        try:
            citation_enum = CitationType(entity_type)
            category = categorize_citation_type(entity_type)
            
            # Get pattern information
            patterns = []
            pattern_count = 0
            pattern_details = []
            
            if pattern_loader:
                try:
                    # Try various naming conventions for citation patterns
                    patterns = pattern_loader.get_patterns_by_entity_type(entity_type)
                    if not patterns:
                        patterns = pattern_loader.get_patterns_by_entity_type(entity_type.lower())
                    if not patterns:
                        patterns = pattern_loader.get_patterns_by_entity_type(f"{entity_type.lower()}_citations")
                    
                    pattern_count = len(patterns)
                    
                    # Get detailed pattern information
                    for p in patterns[:10]:  # Limit to first 10 patterns for detail view
                        pattern_details.append({
                            "name": p.name,
                            "pattern": p.pattern if len(p.pattern) <= 200 else p.pattern[:197] + "...",
                            "confidence": p.confidence,
                            "examples": p.examples[:3] if p.examples else []
                        })
                except Exception as e:
                    logger.debug(f"Could not get patterns for {entity_type}: {e}")
            
            entity_info = {
                "type": entity_type,
                "name": entity_type.replace("_", " ").title(),
                "category": category,
                "description": get_citation_description(entity_type),
                "is_entity": False,
                "is_citation": True,
                "regex_supported": pattern_count > 0,
                "ai_enhanced": True,
                "extraction_modes": ["regex", "ai_enhanced", "hybrid"],
                "pattern_count": pattern_count,
                "pattern_details": pattern_details
            }
        except ValueError:
            # Neither entity nor citation type found
            logger.info(f"Entity type '{entity_type}' not found")
            raise HTTPException(
                status_code=404,
                detail=f"Entity type '{entity_type}' not found"
            )
    
    return entity_info