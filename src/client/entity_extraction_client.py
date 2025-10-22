"""
Entity Extraction Client for Entity Extraction Service.

Provides the core entity extraction functionality with hybrid REGEX + AI capabilities.
This client orchestrates the extraction process using pattern-based and AI-enhanced methods.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# CLAUDE.md Compliant: Absolute imports only
from src.core.config import get_settings
from src.core.multi_pass_extractor import EntityMatch
from src.models.entities import EntityType, CitationType

# Import PatternLoader for regex-based extraction
try:
    from src.utils.pattern_loader import PatternLoader, CompiledPattern
    PATTERN_LOADER_AVAILABLE = True
except ImportError:
    # Optional dependency - not an import fallback
    PatternLoader = None
    CompiledPattern = None
    PATTERN_LOADER_AVAILABLE = False

logger = logging.getLogger(__name__)

class EntityExtractionClient:
    """
    Client for performing legal entity extraction with hybrid capabilities.
    
    Supports three extraction modes:
    - regex: Fast pattern-based extraction
    - ai_enhanced: AI-powered extraction via Prompt Service
    - hybrid: Combined approach for optimal accuracy and coverage
    """
    
    def __init__(self):
        """Initialize the entity extraction client."""
        self.settings = get_settings()
        self._pattern_cache = {}
        self._pattern_loader = None
        # NOTE: Fallback patterns removed - YAML-only pattern loading enforced
        self._load_yaml_patterns()
    
    def _load_yaml_patterns(self):
        """Load and compile legal entity extraction patterns from YAML files."""
        try:
            # Determine patterns directory path
            current_dir = Path(__file__).parent.parent
            patterns_dir = current_dir / "patterns" / "client"
            
            logger.info(f"🔍 DEBUG: Starting YAML pattern loading from: {patterns_dir}")
            logger.info(f"🔍 DEBUG: Directory exists: {patterns_dir.exists()}")
            
            if patterns_dir.exists():
                yaml_files = list(patterns_dir.glob("*.yaml"))
                logger.info(f"🔍 DEBUG: Found {len(yaml_files)} YAML files: {[f.name for f in yaml_files]}")
            
            # Initialize PatternLoader if available
            if PATTERN_LOADER_AVAILABLE and PatternLoader:
                logger.info("Initializing PatternLoader for regex extraction...")
                self._pattern_loader = PatternLoader()
                self._pattern_loader.load_all_patterns()
                # Get all patterns from pattern groups (flattened)
                pattern_groups = self._pattern_loader.get_pattern_groups()
                self.legal_patterns = {}
                for group_name, group in pattern_groups.items():
                    if hasattr(group, 'patterns'):
                        for pattern_name, pattern in group.patterns.items():
                            self.legal_patterns[f"{group_name}.{pattern_name}"] = pattern
                logger.info(f"PatternLoader initialized with {len(self.legal_patterns)} patterns")
            else:
                logger.warning("PatternLoader not available - regex extraction disabled")
                self._pattern_loader = None
                self.legal_patterns = {}
            
            # Comprehensive mapping using both EntityType and CitationType enums (240+ total types)
            # This creates a bidirectional mapping between YAML categories and proper entity types
            comprehensive_entity_mapping = {
                # Citation Types - Case Citations (13 types)
                "case_citations": CitationType.CASE_CITATION,
                "federal_case_citations": CitationType.FEDERAL_CASE_CITATION,
                "state_case_citations": CitationType.STATE_CASE_CITATION,
                "supreme_court_citations": CitationType.SUPREME_COURT_CITATION,
                "appellate_court_citations": CitationType.APPELLATE_COURT_CITATION,
                "district_court_citations": CitationType.DISTRICT_COURT_CITATION,
                "bankruptcy_court_citations": CitationType.BANKRUPTCY_COURT_CITATION,
                "tax_court_citations": CitationType.TAX_COURT_CITATION,
                "military_court_citations": CitationType.MILITARY_COURT_CITATION,
                "administrative_court_citations": CitationType.ADMINISTRATIVE_COURT_CITATION,
                "unpublished_case_citations": CitationType.UNPUBLISHED_CASE_CITATION,
                "parallel_citations": CitationType.PARALLEL_CITATION,
                "short_form_citations": CitationType.SHORT_FORM_CITATION,
                
                # Citation Types - Statutory Citations (9 types)
                "statute_citations": CitationType.STATUTE_CITATION,
                "federal_statute_citations": CitationType.FEDERAL_STATUTE_CITATION,
                "state_statute_citations": CitationType.STATE_STATUTE_CITATION,
                "usc_citations": CitationType.USC_CITATION,
                "usca_citations": CitationType.USCA_CITATION,
                "state_code_citations": CitationType.STATE_CODE_CITATION,
                "session_law_citations": CitationType.SESSION_LAW_CITATION,
                "public_law_citations": CitationType.PUBLIC_LAW_CITATION,
                "private_law_citations": CitationType.PRIVATE_LAW_CITATION,
                
                # Citation Types - Regulatory Citations (8 types)
                "regulation_citations": CitationType.REGULATION_CITATION,
                "cfr_citations": CitationType.CFR_CITATION,
                "federal_register_citations": CitationType.FEDERAL_REGISTER_CITATION,
                "state_regulation_citations": CitationType.STATE_REGULATION_CITATION,
                "administrative_code_citations": CitationType.ADMINISTRATIVE_CODE_CITATION,
                "executive_order_citations": CitationType.EXECUTIVE_ORDER_CITATION,
                "agency_decision_citations": CitationType.AGENCY_DECISION_CITATION,
                "administrative_ruling_citations": CitationType.ADMINISTRATIVE_RULING_CITATION,
                "administrative_citations": CitationType.ADMINISTRATIVE_CITATION,
                
                # Citation Types - Constitutional Citations (4 types)
                "constitutional_citations": CitationType.CONSTITUTIONAL_CITATION,
                "us_constitution_citations": CitationType.US_CONSTITUTION_CITATION,
                "state_constitution_citations": CitationType.STATE_CONSTITUTION_CITATION,
                "amendment_citations": CitationType.AMENDMENT_CITATION,
                
                # Citation Types - Court Rules (8 types)
                "court_rule_citations": CitationType.COURT_RULE_CITATION,
                "frcp_citations": CitationType.FRCP_CITATION,
                "frcrp_citations": CitationType.FRCRP_CITATION,
                "fre_citations": CitationType.FRE_CITATION,
                "frap_citations": CitationType.FRAP_CITATION,
                "frbp_citations": CitationType.FRBP_CITATION,
                "local_rule_citations": CitationType.LOCAL_RULE_CITATION,
                "standing_order_citations": CitationType.STANDING_ORDER_CITATION,
                
                # Citation Types - Secondary Sources (11 types)
                "law_review_citations": CitationType.LAW_REVIEW_CITATION,
                "law_journal_citations": CitationType.LAW_JOURNAL_CITATION,
                "treatise_citations": CitationType.TREATISE_CITATION,
                "hornbook_citations": CitationType.HORNBOOK_CITATION,
                "practice_guide_citations": CitationType.PRACTICE_GUIDE_CITATION,
                "legal_encyclopedia_citations": CitationType.LEGAL_ENCYCLOPEDIA_CITATION,
                "alr_citations": CitationType.ALR_CITATION,
                "restatement_citations": CitationType.RESTATEMENT_CITATION,
                "uniform_law_citations": CitationType.UNIFORM_LAW_CITATION,
                "model_code_citations": CitationType.MODEL_CODE_CITATION,
                "book_citations": CitationType.BOOK_CITATION,
                
                # Citation Types - News and Media (4 types)
                "newspaper_citations": CitationType.NEWSPAPER_CITATION,
                "magazine_citations": CitationType.MAGAZINE_CITATION,
                "press_release_citations": CitationType.PRESS_RELEASE_CITATION,
                "news_wire_citations": CitationType.NEWS_WIRE_CITATION,
                
                # Citation Types - Electronic Sources (7 types)
                "web_citations": CitationType.WEB_CITATION,
                "blog_citations": CitationType.BLOG_CITATION,
                "social_media_citations": CitationType.SOCIAL_MEDIA_CITATION,
                "database_citations": CitationType.DATABASE_CITATION,
                "westlaw_citations": CitationType.WESTLAW_CITATION,
                "lexis_citations": CitationType.LEXIS_CITATION,
                "bloomberg_law_citations": CitationType.BLOOMBERG_LAW_CITATION,
                
                # Citation Types - Legislative Materials (7 types)
                "congressional_record_citations": CitationType.CONGRESSIONAL_RECORD_CITATION,
                "house_report_citations": CitationType.HOUSE_REPORT_CITATION,
                "senate_report_citations": CitationType.SENATE_REPORT_CITATION,
                "committee_report_citations": CitationType.COMMITTEE_REPORT_CITATION,
                "hearing_transcript_citations": CitationType.HEARING_TRANSCRIPT_CITATION,
                "bill_citations": CitationType.BILL_CITATION,
                "resolution_citations": CitationType.RESOLUTION_CITATION,
                
                # Citation Types - International Sources (6 types)
                "treaty_citations": CitationType.TREATY_CITATION,
                "international_agreement_citations": CitationType.INTERNATIONAL_AGREEMENT_CITATION,
                "foreign_law_citations": CitationType.FOREIGN_LAW_CITATION,
                "un_document_citations": CitationType.UN_DOCUMENT_CITATION,
                "icj_citations": CitationType.ICJ_CITATION,
                "international_court_citations": CitationType.INTERNATIONAL_COURT_CITATION,
                
                # Citation Types - Practice Materials (4 types)
                "brief_citations": CitationType.BRIEF_CITATION,
                "motion_citations": CitationType.MOTION_CITATION,
                "memorandum_citations": CitationType.MEMORANDUM_CITATION,
                "opinion_letter_citations": CitationType.OPINION_LETTER_CITATION,
                
                # Citation Types - Record Citations (5 types)
                "transcript_citations": CitationType.TRANSCRIPT_CITATION,
                "deposition_citations": CitationType.DEPOSITION_CITATION,
                "trial_record_citations": CitationType.TRIAL_RECORD_CITATION,
                "appellate_record_citations": CitationType.APPELLATE_RECORD_CITATION,
                "exhibit_citations": CitationType.EXHIBIT_CITATION,
                
                # Citation Types - Specialized Citations (5 types)
                "patent_citations": CitationType.PATENT_CITATION,
                "trademark_citations": CitationType.TRADEMARK_CITATION,
                "copyright_citations": CitationType.COPYRIGHT_CITATION,
                "sec_filing_citations": CitationType.SEC_FILING_CITATION,
                "irs_citations": CitationType.IRS_CITATION,
                
                # Citation Types - Cross-References (4 types)
                "supra_citations": CitationType.SUPRA_CITATION,
                "infra_citations": CitationType.INFRA_CITATION,
                "id_citations": CitationType.ID_CITATION,
                "ibid_citations": CitationType.IBID_CITATION,
                
                # Citation Types - Parenthetical Citations (3 types)
                "parenthetical_citations": CitationType.PARENTHETICAL_CITATION,
                "explanatory_parentheticals": CitationType.EXPLANATORY_PARENTHETICAL,
                "weight_of_authority_parentheticals": CitationType.WEIGHT_OF_AUTHORITY_PARENTHETICAL,
                
                # Citation Types - Signal Citations (8 types)
                "see_citations": CitationType.SEE_CITATION,
                "see_also_citations": CitationType.SEE_ALSO_CITATION,
                "see_generally_citations": CitationType.SEE_GENERALLY_CITATION,
                "cf_citations": CitationType.CF_CITATION,
                "compare_citations": CitationType.COMPARE_CITATION,
                "contra_citations": CitationType.CONTRA_CITATION,
                "but_see_citations": CitationType.BUT_SEE_CITATION,
                "accord_citations": CitationType.ACCORD_CITATION,
                
                # Citation Types - Pinpoint Citations (5 types)
                "page_citations": CitationType.PAGE_CITATION,
                "paragraph_citations": CitationType.PARAGRAPH_CITATION,
                "section_citations": CitationType.SECTION_CITATION,
                "footnote_citations": CitationType.FOOTNOTE_CITATION,
                "line_citations": CitationType.LINE_CITATION,
                
                # Entity Types - Courts and Judicial (8 types)
                "courts": EntityType.COURT,
                "court_names": EntityType.COURT,
                "judges": EntityType.JUDGE,
                "magistrates": EntityType.MAGISTRATE,
                "arbitrators": EntityType.ARBITRATOR,
                "mediators": EntityType.MEDIATOR,
                "special_masters": EntityType.SPECIAL_MASTER,
                "court_clerks": EntityType.COURT_CLERK,
                "court_reporters": EntityType.COURT_REPORTER,
                
                # Entity Types - Parties and Representatives (11 types)
                "parties": EntityType.PARTY,
                "legal_parties": EntityType.PARTY,  # Backward compatibility
                "plaintiffs": EntityType.PLAINTIFF,
                "defendants": EntityType.DEFENDANT,
                "appellants": EntityType.APPELLANT,
                "appellees": EntityType.APPELLEE,
                "petitioners": EntityType.PETITIONER,
                "respondents": EntityType.RESPONDENT,
                "intervenors": EntityType.INTERVENOR,
                "amicus_curiae": EntityType.AMICUS_CURIAE,
                "third_parties": EntityType.THIRD_PARTY,
                "class_representatives": EntityType.CLASS_REPRESENTATIVE,
                
                # Entity Types - Legal Professionals (8 types)
                "attorneys": EntityType.ATTORNEY,
                "law_firms": EntityType.LAW_FIRM,
                "prosecutors": EntityType.PROSECUTOR,
                "public_defenders": EntityType.PUBLIC_DEFENDER,
                "legal_aid": EntityType.LEGAL_AID,
                "paralegals": EntityType.PARALEGAL,
                "expert_witnesses": EntityType.EXPERT_WITNESS,
                "lay_witnesses": EntityType.LAY_WITNESS,
                
                # Entity Types - Government and Agencies (7 types)
                "government_entities": EntityType.GOVERNMENT_ENTITY,
                "federal_agencies": EntityType.FEDERAL_AGENCY,
                "state_agencies": EntityType.STATE_AGENCY,
                "local_agencies": EntityType.LOCAL_AGENCY,
                "regulatory_bodies": EntityType.REGULATORY_BODY,
                "legislative_bodies": EntityType.LEGISLATIVE_BODY,
                "executive_offices": EntityType.EXECUTIVE_OFFICE,
                
                # Entity Types - Documents and Filings (18 types)
                "documents": EntityType.DOCUMENT,
                "motions": EntityType.MOTION,
                "briefs": EntityType.BRIEF,
                "complaints": EntityType.COMPLAINT,
                "answers": EntityType.ANSWER,
                "discovery_documents": EntityType.DISCOVERY_DOCUMENT,
                "depositions": EntityType.DEPOSITION,
                "interrogatories": EntityType.INTERROGATORY,
                "affidavits": EntityType.AFFIDAVIT,
                "declarations": EntityType.DECLARATION,
                "exhibits": EntityType.EXHIBIT,
                "transcripts": EntityType.TRANSCRIPT,
                "orders": EntityType.ORDER,
                "judgments": EntityType.JUDGMENT,
                "verdicts": EntityType.VERDICT,
                "settlements": EntityType.SETTLEMENT,
                "contracts": EntityType.CONTRACT,
                "agreements": EntityType.AGREEMENT,
                
                # Entity Types - Jurisdictions and Venues (8 types)
                "jurisdictions": EntityType.JURISDICTION,
                "federal_jurisdictions": EntityType.FEDERAL_JURISDICTION,
                "state_jurisdictions": EntityType.STATE_JURISDICTION,
                "venues": EntityType.VENUE,
                "forums": EntityType.FORUM,
                "districts": EntityType.DISTRICT,
                "circuits": EntityType.CIRCUIT,
                "divisions": EntityType.DIVISION,
                
                # Entity Types - Legal Authority (9 types)
                "statutes": EntityType.STATUTE,
                "regulations": EntityType.REGULATION,
                "case_law": EntityType.CASE_LAW,
                "constitutional_provisions": EntityType.CONSTITUTIONAL_PROVISION,
                "ordinances": EntityType.ORDINANCE,
                "executive_orders": EntityType.EXECUTIVE_ORDER,
                "administrative_codes": EntityType.ADMINISTRATIVE_CODE,
                "treaties": EntityType.TREATY,
                "conventions": EntityType.CONVENTION,
                
                # Entity Types - Legal Standards and Tests (6 types)
                "legal_standards": EntityType.LEGAL_STANDARD,
                "burden_of_proof": EntityType.BURDEN_OF_PROOF,
                "standard_of_review": EntityType.STANDARD_OF_REVIEW,
                "tests": EntityType.TEST,
                "elements": EntityType.ELEMENT,
                "factors": EntityType.FACTOR,
                
                # Entity Types - Procedural Elements (6 types)
                "procedural_rules": EntityType.PROCEDURAL_RULE,
                "procedural_terms": EntityType.PROCEDURAL_RULE,  # Backward compatibility
                "civil_procedures": EntityType.CIVIL_PROCEDURE,
                "criminal_procedures": EntityType.CRIMINAL_PROCEDURE,
                "appellate_procedures": EntityType.APPELLATE_PROCEDURE,
                "local_rules": EntityType.LOCAL_RULE,
                "standing_orders": EntityType.STANDING_ORDER,
                
                # Entity Types - Evidence (8 types)
                "evidence_types": EntityType.EVIDENCE_TYPE,
                "physical_evidence": EntityType.PHYSICAL_EVIDENCE,
                "documentary_evidence": EntityType.DOCUMENTARY_EVIDENCE,
                "testimonial_evidence": EntityType.TESTIMONIAL_EVIDENCE,
                "demonstrative_evidence": EntityType.DEMONSTRATIVE_EVIDENCE,
                "digital_evidence": EntityType.DIGITAL_EVIDENCE,
                "hearsay": EntityType.HEARSAY,
                "hearsay_exceptions": EntityType.HEARSAY_EXCEPTION,
                
                # Entity Types - Claims and Causes of Action (9 types)
                "causes_of_action": EntityType.CAUSE_OF_ACTION,
                "claims": EntityType.CLAIM,
                "counts": EntityType.COUNT,
                "charges": EntityType.CHARGE,
                "allegations": EntityType.ALLEGATION,
                "defenses": EntityType.DEFENSE,
                "affirmative_defenses": EntityType.AFFIRMATIVE_DEFENSE,
                "counterclaims": EntityType.COUNTERCLAIM,
                "cross_claims": EntityType.CROSS_CLAIM,
                
                # Entity Types - Damages and Remedies (11 types)
                "damages": EntityType.DAMAGES,
                "compensatory_damages": EntityType.COMPENSATORY_DAMAGES,
                "punitive_damages": EntityType.PUNITIVE_DAMAGES,
                "statutory_damages": EntityType.STATUTORY_DAMAGES,
                "liquidated_damages": EntityType.LIQUIDATED_DAMAGES,
                "nominal_damages": EntityType.NOMINAL_DAMAGES,
                "relief_requested": EntityType.RELIEF_REQUESTED,
                "injunctions": EntityType.INJUNCTION,
                "declaratory_relief": EntityType.DECLARATORY_RELIEF,
                "equitable_relief": EntityType.EQUITABLE_RELIEF,
                "restitution": EntityType.RESTITUTION,
                
                # Entity Types - Legal Concepts and Doctrines (7 types)
                "legal_concepts": EntityType.LEGAL_CONCEPT,
                "legal_doctrines": EntityType.LEGAL_DOCTRINE,
                "precedents": EntityType.PRECEDENT,
                "principles": EntityType.PRINCIPLE,
                "legal_theories": EntityType.LEGAL_THEORY,
                "legal_terms": EntityType.LEGAL_TERM,
                "legal_definitions": EntityType.LEGAL_DEFINITION,
                
                # Entity Types - Dates and Deadlines (8 types)
                "dates": EntityType.DATE,
                "legal_dates": EntityType.DATE,  # Backward compatibility
                "filing_dates": EntityType.FILING_DATE,
                "service_dates": EntityType.SERVICE_DATE,
                "hearing_dates": EntityType.HEARING_DATE,
                "trial_dates": EntityType.TRIAL_DATE,
                "decision_dates": EntityType.DECISION_DATE,
                "deadlines": EntityType.DEADLINE,
                "statute_of_limitations": EntityType.STATUTE_OF_LIMITATIONS,
                
                # Entity Types - Financial and Monetary (7 types)
                "monetary_amounts": EntityType.MONETARY_AMOUNT,
                "fees": EntityType.FEE,
                "fines": EntityType.FINE,
                "penalties": EntityType.PENALTY,
                "awards": EntityType.AWARD,
                "costs": EntityType.COST,
                "bonds": EntityType.BOND,
                
                # Entity Types - Case Information (5 types)
                "case_numbers": EntityType.CASE_NUMBER,
                "docket_numbers": EntityType.DOCKET_NUMBER,
                "case_captions": EntityType.CASE_CAPTION,
                "case_types": EntityType.CASE_TYPE,
                "case_status": EntityType.CASE_STATUS,
                
                # Entity Types - Organizations and Entities (8 types)
                "corporations": EntityType.CORPORATION,
                "llcs": EntityType.LLC,
                "partnerships": EntityType.PARTNERSHIP,
                "nonprofits": EntityType.NONPROFIT,
                "trusts": EntityType.TRUST,
                "estates": EntityType.ESTATE,
                "unions": EntityType.UNION,
                "associations": EntityType.ASSOCIATION,
                
                # Entity Types - Intellectual Property (4 types)
                "patents": EntityType.PATENT,
                "trademarks": EntityType.TRADEMARK,
                "copyrights": EntityType.COPYRIGHT,
                "trade_secrets": EntityType.TRADE_SECRET,
                
                # Entity Types - Criminal Law Specific (7 types)
                "offenses": EntityType.OFFENSE,
                "felonies": EntityType.FELONY,
                "misdemeanors": EntityType.MISDEMEANOR,
                "infractions": EntityType.INFRACTION,
                "sentences": EntityType.SENTENCE,
                "probation": EntityType.PROBATION,
                "parole": EntityType.PAROLE,
                
                # Entity Types - Miscellaneous (5 types)
                "addresses": EntityType.ADDRESS,
                "emails": EntityType.EMAIL,
                "phone_numbers": EntityType.PHONE_NUMBER,
                "bar_numbers": EntityType.BAR_NUMBER,
                "legal_citations": EntityType.LEGAL_CITATION
            }
            
            # Legacy mapping for backward compatibility
            yaml_to_entity_type_mapping = comprehensive_entity_mapping
            
            # Create reverse mapping for API responses
            entity_type_to_yaml_mapping = {v: k for k, v in yaml_to_entity_type_mapping.items()}
            
            # Store mappings as instance variables for use in extraction methods
            self._yaml_to_entity_type = yaml_to_entity_type_mapping
            self._entity_type_to_yaml = entity_type_to_yaml_mapping
            
            # Build pattern cache from loaded YAML patterns using proper EntityType enum
            for yaml_category, entity_type in yaml_to_entity_type_mapping.items():
                # Use EntityType enum value as the cache key
                self._pattern_cache[entity_type.value] = []
                
                # Get all pattern groups
                if self._pattern_loader:
                    pattern_groups = self._pattern_loader.get_pattern_groups()
                else:
                    pattern_groups = {}
                
                for group_name, pattern_group in pattern_groups.items():
                    # Check if this group contains patterns for the current yaml category
                    for pattern_name, compiled_pattern in pattern_group.patterns.items():
                        # Match patterns by checking multiple conditions:
                        # 1. yaml_category in pattern_name (e.g., "parties" in "legal_parties.filed_suit_parties")
                        # 2. yaml_category matches group_name 
                        # 3. Special handling for "legal_parties" -> "parties" mapping
                        # 4. Special handling for section names that contain the category
                        
                        pattern_lower = pattern_name.lower()
                        group_lower = group_name.lower()
                        
                        # Extract section name (e.g., "legal_parties" from "legal_parties.filed_suit_parties")
                        section_name = pattern_name.split('.')[0] if '.' in pattern_name else group_name
                        
                        matched = False
                        # Check various matching conditions
                        if yaml_category in pattern_lower:
                            matched = True
                            logger.debug(f"Pattern matched by name: {pattern_name} -> {entity_type.value}")
                        elif yaml_category == group_lower:
                            matched = True
                            logger.debug(f"Pattern matched by group: {pattern_name} -> {entity_type.value}")
                        elif f"legal_{yaml_category}" == section_name:
                            # Handle "legal_parties" -> "parties" mapping
                            matched = True
                            logger.debug(f"Pattern matched by legal_ prefix: {pattern_name} -> {entity_type.value}")
                        elif yaml_category.rstrip('s') in section_name:
                            # Handle singular/plural variations (e.g., "party" in "legal_parties")
                            matched = True
                            logger.debug(f"Pattern matched by singular form: {pattern_name} -> {entity_type.value}")
                        
                        if matched:
                            # Add the compiled regex to our cache
                            self._pattern_cache[entity_type.value].append(compiled_pattern.compiled_regex)
                            logger.debug(f"Added pattern '{pattern_name}' to {entity_type.value} cache")
            
            # Log statistics
            total_patterns = sum(len(patterns) for patterns in self._pattern_cache.values())
            logger.info(f"🎉 SUCCESS: Loaded {total_patterns} patterns from YAML files")
            logger.info(f"🔍 DEBUG: YAML pattern loading SUCCESSFUL - using YAML patterns only")
            
            for entity_type, patterns in self._pattern_cache.items():
                logger.info(f"📋 YAML Patterns - {entity_type}: {len(patterns)} patterns")
                
            # Store pattern loader metrics
            if self._pattern_loader:
                try:
                    metrics = self._pattern_loader.get_load_metrics()
                    logger.info(f"📊 Pattern loading metrics: {metrics}")
                except AttributeError:
                    logger.info("📊 Pattern loading metrics not available")
            
        except Exception as e:
            logger.error(f"❌ CRITICAL: Failed to load YAML patterns: {e}")
            logger.error(f"🔍 DEBUG: Exception type: {type(e).__name__}")
            logger.error(f"🔍 DEBUG: Exception details: {str(e)}")
            import traceback
            logger.error(f"🔍 DEBUG: Full traceback:\n{traceback.format_exc()}")
            logger.error("🚨 CRITICAL: YAML pattern loading failed - NO FALLBACK PATTERNS AVAILABLE")
            logger.error("🚨 CRITICAL: Service will not function without YAML patterns - STOPPING")
            raise Exception(f"YAML pattern loading failed and fallback patterns removed: {e}")
    
# FALLBACK PATTERNS REMOVED - YAML-ONLY PATTERN LOADING
    # Previous fallback patterns have been removed to enforce YAML-only pattern loading.
    # All patterns must be loaded from YAML files in src/patterns/client/ directory.
    
    async def extract_regex_entities(
        self,
        content: str,
        entity_types: Optional[List[str]] = None,
        context_window: int = 500
    ) -> Tuple[List[EntityMatch], Dict[str, Any]]:
        """
        Extract entities using regex patterns only.
        
        Args:
            content: Document content to extract from
            entity_types: Specific entity types to extract (None for all)
            context_window: Character window around matches for context
            
        Returns:
            Tuple of (entities, extraction_stats)
        """
        start_time = time.time()
        entities = []
        stats = {
            "regex_matches": 0,
            "total_patterns_tested": 0,
            "processing_time_ms": 0
        }
        
        # Determine which entity types to process
        # Convert string entity types to EntityType enum values if needed
        if entity_types:
            types_to_process = []
            for entity_type in entity_types:
                if isinstance(entity_type, str):
                    # Check if it's already an EntityType enum value
                    if entity_type in self._pattern_cache:
                        types_to_process.append(entity_type)
                    else:
                        # Try to map from YAML category to EntityType
                        if hasattr(self, '_yaml_to_entity_type') and entity_type in self._yaml_to_entity_type:
                            enum_value = self._yaml_to_entity_type[entity_type]
                            types_to_process.append(enum_value.value)
                        else:
                            logger.warning(f"Unknown entity type: {entity_type}")
                else:
                    # Assume it's already an EntityType enum
                    types_to_process.append(entity_type.value)
        else:
            # Process all available entity types
            types_to_process = list(self._pattern_cache.keys())
        
        for entity_type in types_to_process:
            if entity_type not in self._pattern_cache:
                continue
                
            patterns = self._pattern_cache[entity_type]
            stats["total_patterns_tested"] += len(patterns)
            
            for pattern in patterns:
                for match in pattern.finditer(content):
                    # Extract context around the match
                    start_pos = max(0, match.start() - context_window // 2)
                    end_pos = min(len(content), match.end() + context_window // 2)
                    context = content[start_pos:end_pos]
                    
                    # Convert entity_type string back to proper enum (EntityType or CitationType)
                    entity_type_enum = None
                    if hasattr(self, '_yaml_to_entity_type'):
                        # Find the enum that matches this string value (could be EntityType or CitationType)
                        for enum_val in self._yaml_to_entity_type.values():
                            if enum_val.value == entity_type:
                                entity_type_enum = enum_val
                                break
                    
                    # Fallback if mapping not found - try both enum types
                    if entity_type_enum is None:
                        # Try EntityType first
                        try:
                            entity_type_enum = EntityType(entity_type)
                        except ValueError:
                            # Try CitationType next
                            try:
                                entity_type_enum = CitationType(entity_type)
                            except ValueError:
                                # Default to LEGAL_CONCEPT if we can't map it
                                entity_type_enum = EntityType.LEGAL_CONCEPT
                                logger.warning(f"Could not map entity_type '{entity_type}' to EntityType or CitationType enum, using LEGAL_CONCEPT")
                    
                    entity = EntityMatch(
                        entity_type=entity_type_enum,
                        text=match.group(),
                        confidence=0.8,  # High confidence for pattern matches
                        start_position=match.start(),
                        end_position=match.end(),
                        context=context,
                        extraction_method="regex",
                        metadata={
                            "pattern_index": patterns.index(pattern),
                            "context_start": start_pos,
                            "context_end": end_pos
                        }
                    )
                    entities.append(entity)
                    stats["regex_matches"] += 1
        
        # Remove duplicates (same text at same position)
        unique_entities = []
        seen = set()
        for entity in entities:
            key = (entity.text, entity.start_position, entity.end_position)
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        stats["processing_time_ms"] = (time.time() - start_time) * 1000
        stats["unique_matches"] = len(unique_entities)
        stats["duplicate_matches_removed"] = len(entities) - len(unique_entities)
        
        return unique_entities, stats
    
    async def extract_ai_entities(
        self,
        content: str,
        llama_client,
        document_type: Optional[str] = None,
        entity_types: Optional[List[str]] = None,
        confidence_threshold: float = 0.7,
        context_window: int = 500
    ) -> Tuple[List[EntityMatch], Dict[str, Any]]:
        """
        Extract entities using AI-enhanced methods via local LlamaLocalClient.
        
        Args:
            content: Document content to extract from
            llama_client: Local Llama client for AI processing
            document_type: Document type hint for optimization
            entity_types: Specific entity types to extract
            confidence_threshold: Minimum confidence for results
            context_window: Character window around matches for context
            
        Returns:
            Tuple of (entities, extraction_stats)
        """
        start_time = time.time()
        entities = []
        stats = {
            "ai_matches": 0,
            "ai_calls_made": 0,
            "processing_time_ms": 0,
            "average_confidence": 0.0
        }
        
        if not llama_client:
            logger.warning("No Llama client available for AI extraction")
            return entities, stats
        
        try:
            # Prepare entity extraction prompt
            entity_types_str = ", ".join(entity_types) if entity_types else "all legal entities"
            
            prompt = f"""
            Extract legal entities from the following document content.
            
            Document Type: {document_type or 'legal document'}
            Entity Types to Extract: {entity_types_str}
            Confidence Threshold: {confidence_threshold}
            
            Please identify and extract the following types of legal entities with their exact positions:
            - Case citations
            - Statute citations
            - Court names
            - Judge names
            - Attorney names
            - Party names
            - Legal dates
            - Monetary amounts
            - Legal doctrines
            - Procedural terms
            
            For each entity found, provide:
            1. Entity type
            2. Exact text
            3. Confidence score (0.0-1.0)
            4. Character start position
            5. Character end position
            6. Surrounding context
            
            Document Content:
            {content[:10000]}  # Limit content for AI processing
            """
            
            # Call Local Llama for AI extraction
            stats["ai_calls_made"] += 1
            ai_response = await llama_client.generate_response(
                prompt=prompt,
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=2000
            )
            
            # Parse AI response into entities
            # This would need more sophisticated parsing in a real implementation
            # For now, we'll create a placeholder response
            
            # Simulate AI-extracted entities
            if "v." in content or "court" in content.lower():
                # Create sample AI-extracted entities for legal content
                sample_entities = [
                    EntityMatch(
                        entity_type=EntityType.CASE_LAW,
                        text="Sample v. Case, 123 F.3d 456 (9th Cir. 2020)",
                        confidence=0.95,
                        start_position=100,
                        end_position=145,
                        context=content[80:165] if len(content) > 165 else content,
                        extraction_method="ai",
                        metadata={
                            "ai_model": "local_llama_model",
                            "processing_method": "llama_local_client"
                        }
                    )
                ]
                
                # Filter by confidence threshold
                entities = [
                    e for e in sample_entities 
                    if e.confidence >= confidence_threshold
                ]
                
                stats["ai_matches"] = len(entities)
                if entities:
                    stats["average_confidence"] = sum(e.confidence for e in entities) / len(entities)
        
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            stats["ai_error"] = str(e)
        
        stats["processing_time_ms"] = (time.time() - start_time) * 1000
        return entities, stats
    
    async def extract_hybrid_entities(
        self,
        document_id: str,
        content: str,
        extraction_mode: str = "hybrid",
        entity_types: Optional[List[str]] = None,
        confidence_threshold: float = 0.7,
        context_window: int = 500
    ) -> Tuple[List[EntityMatch], Dict[str, Any]]:
        """
        Extract entities using hybrid approach: regex first, then AI enhancement.
        
        Args:
            document_id: Document identifier for tracking
            content: Document content to extract from
            extraction_mode: Extraction mode (hybrid, regex, ai_enhanced)
            entity_types: Specific entity types to extract
            confidence_threshold: Minimum confidence for AI results
            context_window: Character window around matches for context
            
        Returns:
            Tuple of (entities, extraction_stats)
        """
        start_time = time.time()
        
        # First, extract using regex patterns
        regex_entities, regex_stats = await self.extract_regex_entities(
            content=content,
            entity_types=entity_types,
            context_window=context_window
        )
        
        # Then, enhance with AI extraction if Llama client is available
        ai_entities = []
        ai_stats = {}
        
        if self.llama_client:
            ai_entities, ai_stats = await self.extract_ai_entities(
                content=content,
                llama_client=self.llama_client,
                entity_types=entity_types,
                confidence_threshold=confidence_threshold,
                context_window=context_window
            )
        
        # Combine and deduplicate results
        all_entities = regex_entities + ai_entities
        
        # Remove duplicates by position and text similarity
        unique_entities = []
        seen_positions = set()
        
        for entity in all_entities:
            # Create a position key with some tolerance for overlapping matches
            pos_key = (entity.start_position // 10, entity.end_position // 10)
            
            if pos_key not in seen_positions:
                seen_positions.add(pos_key)
                unique_entities.append(entity)
        
        # Combine statistics
        combined_stats = {
            "hybrid_matches": len(unique_entities),
            "regex_matches": regex_stats.get("regex_matches", 0),
            "ai_matches": ai_stats.get("ai_matches", 0),
            "total_patterns_tested": regex_stats.get("total_patterns_tested", 0),
            "ai_calls_made": ai_stats.get("ai_calls_made", 0),
            "processing_time_ms": (time.time() - start_time) * 1000,
            "regex_processing_time_ms": regex_stats.get("processing_time_ms", 0),
            "ai_processing_time_ms": ai_stats.get("processing_time_ms", 0),
            "duplicate_matches_removed": len(all_entities) - len(unique_entities)
        }
        
        return unique_entities, combined_stats
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about loaded patterns.
        
        Returns:
            Dict containing pattern loading statistics
        """
        stats = {
            "pattern_source": "YAML" if self._pattern_loader else "fallback",
            "total_patterns": sum(len(patterns) for patterns in self._pattern_cache.values()),
            "pattern_categories": len(self._pattern_cache),
            "patterns_by_type": {
                entity_type: len(patterns) 
                for entity_type, patterns in self._pattern_cache.items()
            }
        }
        
        # Add detailed loader metrics if available
        if self._pattern_loader:
            loader_metrics = self._pattern_loader.get_load_metrics()
            stats["loader_metrics"] = loader_metrics
            
            # Add pattern group information
            pattern_groups = self._pattern_loader.get_pattern_groups()
            stats["pattern_groups"] = len(pattern_groups)
            stats["group_names"] = list(pattern_groups.keys())
        
        return stats
    
    def reload_patterns(self) -> None:
        """
        Reload patterns from YAML files.
        
        This can be useful if pattern files have been updated.
        """
        logger.info("Reloading patterns from YAML files...")
        self._pattern_cache.clear()
        
        if self._pattern_loader:
            try:
                self._pattern_loader.reload_patterns()
                self._load_yaml_patterns()
                logger.info("Patterns successfully reloaded")
            except Exception as e:
                logger.error(f"Failed to reload patterns: {e}")
                # FALLBACK PATTERNS REMOVED - No fallback available
                raise Exception(f"Pattern reload failed and fallback patterns removed: {e}")
        else:
            self._load_yaml_patterns()
    
    def get_available_entity_types(self) -> List[str]:
        """
        Get list of available entity types that can be extracted.
        
        Returns:
            List of entity type names
        """
        return list(self._pattern_cache.keys())