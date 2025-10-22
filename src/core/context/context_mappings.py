"""
Context Mappings for CALES Entity Extraction Service

This module provides comprehensive context mappings for all 272 entity types,
organizing them by their typical contextual appearances in legal documents.
"""

from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass


class ContextType(Enum):
    """Legal context types for entity classification"""
    CASE_HEADER = "case_header"
    PARTY_SECTION = "party_section"
    JURISDICTION = "jurisdiction"
    PROCEDURAL = "procedural"
    DATES_DEADLINES = "dates_deadlines"
    MONETARY = "monetary"
    LEGAL_CITATIONS = "legal_citations"
    CONTRACTUAL = "contractual"
    CRIMINAL = "criminal"
    PROPERTY = "property"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    CORPORATE = "corporate"
    FINANCIAL = "financial"
    INSURANCE = "insurance"
    EMPLOYMENT = "employment"
    FAMILY = "family"
    IMMIGRATION = "immigration"
    MEDICAL = "medical"
    ENVIRONMENTAL = "environmental"
    BANKRUPTCY = "bankruptcy"
    ADMINISTRATIVE = "administrative"
    EVIDENCE = "evidence"
    DISCOVERY = "discovery"
    INTERNATIONAL = "international"
    ARBITRATION = "arbitration"
    SECURITIES = "securities"
    MARITIME = "maritime"
    AVIATION = "aviation"
    TELECOMMUNICATIONS = "telecommunications"
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    TECHNOLOGY = "technology"
    ENTERTAINMENT = "entertainment"
    NONPROFIT = "nonprofit"
    ESTATE_PLANNING = "estate_planning"
    MILITARY = "military"
    CONSTRUCTION = "construction"
    AGRICULTURE = "agriculture"
    NATURAL_RESOURCES = "natural_resources"
    TRIBAL = "tribal"
    GENERAL_PARTIES = "general_parties"
    CONTACT_INFO = "contact_info"
    IDENTIFICATION = "identification"
    COURT_PERSONNEL = "court_personnel"
    LEGAL_DOCUMENTS = "legal_documents"
    LEGAL_CONCEPTS = "legal_concepts"
    GOVERNMENT = "government"
    TEMPORAL = "temporal"
    QUANTITATIVE = "quantitative"
    STATUS = "status"
    CRIMINAL_CHARGES = "criminal_charges"
    BENEFICIARIES = "beneficiaries"
    LEGAL_ACTIONS = "legal_actions"
    CONTRACT_TERMS = "contract_terms"
    LEGAL_STANDARDS = "legal_standards"
    SIGNATURE = "signature"
    CROSS_REFERENCES = "cross_references"
    VENUE_FORUM = "venue_forum"
    CONTRACT_CLAUSES = "contract_clauses"


@dataclass
class EntityContextMapping:
    """Mapping of entity type to its contextual indicators"""
    entity_type: str
    primary_context: ContextType
    secondary_contexts: List[ContextType]
    context_indicators: List[str]  # Keywords/phrases indicating this context
    proximity_words: List[str]  # Words often found near this entity type
    section_headers: List[str]  # Common section headers where entity appears
    confidence_boost: float  # Confidence boost when found in expected context


class ContextMappings:
    """
    Comprehensive context mappings for all 272 CALES entity types.
    Provides contextual understanding for entity extraction and validation.
    """
    
    def __init__(self):
        """Initialize context mappings for all entity types"""
        self._initialize_entity_mappings()
        self._initialize_context_groups()
        self._initialize_context_indicators()
    
    def _initialize_entity_mappings(self):
        """Initialize mappings for all 272 entity types"""
        self.entity_mappings: Dict[str, EntityContextMapping] = {
            # Legal Core Entities
            "COURT": EntityContextMapping(
                entity_type="COURT",
                primary_context=ContextType.CASE_HEADER,
                secondary_contexts=[ContextType.JURISDICTION, ContextType.VENUE_FORUM],
                context_indicators=["in the", "before the", "court of", "tribunal"],
                proximity_words=["district", "circuit", "appeals", "supreme", "federal", "state"],
                section_headers=["CAPTION", "CASE INFORMATION", "COURT"],
                confidence_boost=0.15
            ),
            "JUDGE": EntityContextMapping(
                entity_type="JUDGE",
                primary_context=ContextType.CASE_HEADER,
                secondary_contexts=[ContextType.COURT_PERSONNEL, ContextType.PROCEDURAL],
                context_indicators=["honorable", "judge", "justice", "magistrate", "before"],
                proximity_words=["presiding", "assigned", "hearing", "ruling", "order"],
                section_headers=["JUDGE", "JUDICIAL OFFICER", "BEFORE"],
                confidence_boost=0.2
            ),
            "ATTORNEY": EntityContextMapping(
                entity_type="ATTORNEY",
                primary_context=ContextType.PARTY_SECTION,
                secondary_contexts=[ContextType.SIGNATURE, ContextType.COURT_PERSONNEL],
                context_indicators=["attorney for", "counsel for", "represented by", "esq", "esquire"],
                proximity_words=["plaintiff", "defendant", "petitioner", "respondent", "firm"],
                section_headers=["ATTORNEYS", "COUNSEL", "REPRESENTATION"],
                confidence_boost=0.15
            ),
            "LAW_FIRM": EntityContextMapping(
                entity_type="LAW_FIRM",
                primary_context=ContextType.PARTY_SECTION,
                secondary_contexts=[ContextType.SIGNATURE, ContextType.CONTACT_INFO],
                context_indicators=["llp", "pllc", "law office", "legal", "attorneys", "& associates"],
                proximity_words=["counsel", "firm", "partners", "attorneys", "representing"],
                section_headers=["LAW FIRM", "COUNSEL", "ATTORNEYS FOR"],
                confidence_boost=0.15
            ),
            "CASE": EntityContextMapping(
                entity_type="CASE",
                primary_context=ContextType.LEGAL_CITATIONS,
                secondary_contexts=[ContextType.CASE_HEADER, ContextType.LEGAL_CONCEPTS],
                context_indicators=["v.", "versus", "matter of", "in re", "ex rel"],
                proximity_words=["case", "citation", "precedent", "ruling", "decision"],
                section_headers=["CASE CITATIONS", "AUTHORITIES", "PRECEDENTS"],
                confidence_boost=0.2
            ),
            "DOCKET_NUMBER": EntityContextMapping(
                entity_type="DOCKET_NUMBER",
                primary_context=ContextType.CASE_HEADER,
                secondary_contexts=[ContextType.PROCEDURAL],
                context_indicators=["case no", "docket", "no.", "cv", "cr", "case number"],
                proximity_words=["filed", "assigned", "consolidated", "related"],
                section_headers=["CASE NUMBER", "DOCKET", "CASE INFORMATION"],
                confidence_boost=0.25
            ),
            "CITATION": EntityContextMapping(
                entity_type="CITATION",
                primary_context=ContextType.LEGAL_CITATIONS,
                secondary_contexts=[ContextType.LEGAL_CONCEPTS],
                context_indicators=["F.3d", "F.2d", "U.S.", "Cal.App", "F.Supp", "So.2d", "N.E.2d"],
                proximity_words=["citing", "see", "accord", "compare", "but see"],
                section_headers=["CITATIONS", "AUTHORITIES", "CASES CITED"],
                confidence_boost=0.3
            ),
            
            # Party Entities
            "PLAINTIFF": EntityContextMapping(
                entity_type="PLAINTIFF",
                primary_context=ContextType.PARTY_SECTION,
                secondary_contexts=[ContextType.CASE_HEADER, ContextType.GENERAL_PARTIES],
                context_indicators=["plaintiff", "petitioner", "complainant", "claimant", "appellant"],
                proximity_words=["versus", "against", "filed", "alleges", "seeks"],
                section_headers=["PARTIES", "PLAINTIFF", "PETITIONER"],
                confidence_boost=0.2
            ),
            "DEFENDANT": EntityContextMapping(
                entity_type="DEFENDANT",
                primary_context=ContextType.PARTY_SECTION,
                secondary_contexts=[ContextType.CASE_HEADER, ContextType.GENERAL_PARTIES],
                context_indicators=["defendant", "respondent", "accused", "appellee"],
                proximity_words=["versus", "against", "denies", "defends", "liable"],
                section_headers=["PARTIES", "DEFENDANT", "RESPONDENT"],
                confidence_boost=0.2
            ),
            "WITNESS": EntityContextMapping(
                entity_type="WITNESS",
                primary_context=ContextType.EVIDENCE,
                secondary_contexts=[ContextType.DISCOVERY, ContextType.PROCEDURAL],
                context_indicators=["witness", "testified", "testimony", "deponent", "affiant"],
                proximity_words=["sworn", "stated", "observed", "saw", "heard"],
                section_headers=["WITNESSES", "TESTIMONY", "WITNESS LIST"],
                confidence_boost=0.15
            ),
            "EXPERT": EntityContextMapping(
                entity_type="EXPERT",
                primary_context=ContextType.EVIDENCE,
                secondary_contexts=[ContextType.DISCOVERY],
                context_indicators=["expert", "specialist", "consultant", "opinion", "qualified"],
                proximity_words=["report", "analysis", "methodology", "credentials", "field"],
                section_headers=["EXPERT WITNESSES", "EXPERT REPORTS", "EXPERT TESTIMONY"],
                confidence_boost=0.2
            ),
            "JURY": EntityContextMapping(
                entity_type="JURY",
                primary_context=ContextType.PROCEDURAL,
                secondary_contexts=[ContextType.COURT_PERSONNEL],
                context_indicators=["jury", "juror", "panel", "verdict", "deliberation"],
                proximity_words=["trial", "selection", "instructions", "unanimous", "hung"],
                section_headers=["JURY", "JURY DEMAND", "JURY INSTRUCTIONS"],
                confidence_boost=0.15
            ),
            
            # Legal Concepts
            "LEGAL_DOCTRINE": EntityContextMapping(
                entity_type="LEGAL_DOCTRINE",
                primary_context=ContextType.LEGAL_CONCEPTS,
                secondary_contexts=[ContextType.LEGAL_STANDARDS],
                context_indicators=["doctrine", "principle", "rule", "theory", "concept"],
                proximity_words=["applies", "established", "recognized", "under", "pursuant"],
                section_headers=["LEGAL ANALYSIS", "APPLICABLE LAW", "LEGAL STANDARDS"],
                confidence_boost=0.1
            ),
            "LEGAL_STANDARD": EntityContextMapping(
                entity_type="LEGAL_STANDARD",
                primary_context=ContextType.LEGAL_STANDARDS,
                secondary_contexts=[ContextType.LEGAL_CONCEPTS],
                context_indicators=["standard", "test", "burden", "threshold", "requirement"],
                proximity_words=["proof", "evidence", "meets", "satisfies", "fails"],
                section_headers=["LEGAL STANDARD", "STANDARD OF REVIEW", "BURDEN OF PROOF"],
                confidence_boost=0.15
            ),
            "CAUSE_OF_ACTION": EntityContextMapping(
                entity_type="CAUSE_OF_ACTION",
                primary_context=ContextType.LEGAL_CONCEPTS,
                secondary_contexts=[ContextType.PROCEDURAL],
                context_indicators=["claim", "cause of action", "count", "allegation", "violation"],
                proximity_words=["alleges", "asserts", "brings", "states", "pleads"],
                section_headers=["CAUSES OF ACTION", "CLAIMS", "COUNTS"],
                confidence_boost=0.15
            ),
            "LEGAL_REMEDY": EntityContextMapping(
                entity_type="LEGAL_REMEDY",
                primary_context=ContextType.LEGAL_CONCEPTS,
                secondary_contexts=[ContextType.MONETARY],
                context_indicators=["remedy", "relief", "damages", "compensation", "restitution"],
                proximity_words=["seeks", "entitled", "awarded", "grant", "deny"],
                section_headers=["RELIEF SOUGHT", "PRAYER FOR RELIEF", "REMEDIES"],
                confidence_boost=0.15
            ),
            "LEGAL_DEFENSE": EntityContextMapping(
                entity_type="LEGAL_DEFENSE",
                primary_context=ContextType.LEGAL_CONCEPTS,
                secondary_contexts=[ContextType.PROCEDURAL],
                context_indicators=["defense", "immunity", "privilege", "justification", "excuse"],
                proximity_words=["asserts", "raises", "claims", "invokes", "waives"],
                section_headers=["DEFENSES", "AFFIRMATIVE DEFENSES", "IMMUNITIES"],
                confidence_boost=0.15
            ),
            
            # Statutory Entities
            "STATUTE": EntityContextMapping(
                entity_type="STATUTE",
                primary_context=ContextType.LEGAL_CITATIONS,
                secondary_contexts=[ContextType.LEGAL_CONCEPTS],
                context_indicators=["U.S.C.", "USC", "statute", "code", "section", "§"],
                proximity_words=["title", "chapter", "subsection", "paragraph", "violates"],
                section_headers=["APPLICABLE STATUTES", "STATUTORY AUTHORITY", "STATUTES"],
                confidence_boost=0.2
            ),
            "REGULATION": EntityContextMapping(
                entity_type="REGULATION",
                primary_context=ContextType.LEGAL_CITATIONS,
                secondary_contexts=[ContextType.ADMINISTRATIVE],
                context_indicators=["C.F.R.", "CFR", "regulation", "rule", "part", "subpart"],
                proximity_words=["title", "section", "promulgated", "pursuant", "compliance"],
                section_headers=["REGULATIONS", "REGULATORY FRAMEWORK", "APPLICABLE REGULATIONS"],
                confidence_boost=0.2
            ),
            "CONSTITUTIONAL_PROVISION": EntityContextMapping(
                entity_type="CONSTITUTIONAL_PROVISION",
                primary_context=ContextType.LEGAL_CITATIONS,
                secondary_contexts=[ContextType.LEGAL_CONCEPTS],
                context_indicators=["amendment", "article", "clause", "constitution", "constitutional"],
                proximity_words=["first", "fifth", "fourteenth", "due process", "equal protection"],
                section_headers=["CONSTITUTIONAL ISSUES", "CONSTITUTIONAL CLAIMS"],
                confidence_boost=0.2
            ),
            "ORDINANCE": EntityContextMapping(
                entity_type="ORDINANCE",
                primary_context=ContextType.LEGAL_CITATIONS,
                secondary_contexts=[ContextType.ADMINISTRATIVE],
                context_indicators=["ordinance", "municipal code", "city code", "county code", "local"],
                proximity_words=["city", "county", "township", "municipality", "zoning"],
                section_headers=["LOCAL ORDINANCES", "MUNICIPAL LAW", "CITY ORDINANCES"],
                confidence_boost=0.15
            ),
            
            # Procedural Entities
            "MOTION": EntityContextMapping(
                entity_type="MOTION",
                primary_context=ContextType.PROCEDURAL,
                secondary_contexts=[ContextType.LEGAL_DOCUMENTS],
                context_indicators=["motion", "move", "request", "application", "petition"],
                proximity_words=["dismiss", "summary judgment", "compel", "limine", "reconsider"],
                section_headers=["MOTION", "RELIEF REQUESTED", "PROCEDURAL HISTORY"],
                confidence_boost=0.2
            ),
            "ORDER": EntityContextMapping(
                entity_type="ORDER",
                primary_context=ContextType.PROCEDURAL,
                secondary_contexts=[ContextType.LEGAL_DOCUMENTS],
                context_indicators=["order", "ordered", "decree", "ruling", "decision"],
                proximity_words=["court", "judge", "hereby", "granted", "denied"],
                section_headers=["ORDER", "COURT ORDER", "RULING"],
                confidence_boost=0.2
            ),
            "JUDGMENT": EntityContextMapping(
                entity_type="JUDGMENT",
                primary_context=ContextType.PROCEDURAL,
                secondary_contexts=[ContextType.LEGAL_DOCUMENTS],
                context_indicators=["judgment", "verdict", "decision", "finding", "determination"],
                proximity_words=["final", "default", "summary", "entered", "rendered"],
                section_headers=["JUDGMENT", "FINAL JUDGMENT", "VERDICT"],
                confidence_boost=0.2
            ),
            "PLEADING": EntityContextMapping(
                entity_type="PLEADING",
                primary_context=ContextType.LEGAL_DOCUMENTS,
                secondary_contexts=[ContextType.PROCEDURAL],
                context_indicators=["complaint", "answer", "reply", "counterclaim", "cross-claim"],
                proximity_words=["filed", "amended", "supplemental", "responsive", "initial"],
                section_headers=["PLEADINGS", "COMPLAINT", "ANSWER"],
                confidence_boost=0.15
            ),
            "BRIEF": EntityContextMapping(
                entity_type="BRIEF",
                primary_context=ContextType.LEGAL_DOCUMENTS,
                secondary_contexts=[ContextType.PROCEDURAL],
                context_indicators=["brief", "memorandum", "memo", "submission", "argument"],
                proximity_words=["support", "opposition", "reply", "amicus", "appellate"],
                section_headers=["BRIEF", "MEMORANDUM", "LEGAL ARGUMENT"],
                confidence_boost=0.15
            ),
            
            # Contract Entities
            "CONTRACT": EntityContextMapping(
                entity_type="CONTRACT",
                primary_context=ContextType.CONTRACTUAL,
                secondary_contexts=[ContextType.LEGAL_DOCUMENTS],
                context_indicators=["contract", "agreement", "covenant", "compact", "terms"],
                proximity_words=["parties", "executed", "breach", "performance", "consideration"],
                section_headers=["CONTRACT", "AGREEMENT", "TERMS AND CONDITIONS"],
                confidence_boost=0.2
            ),
            "CONTRACT_PARTY": EntityContextMapping(
                entity_type="CONTRACT_PARTY",
                primary_context=ContextType.CONTRACTUAL,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["party", "contractor", "vendor", "supplier", "purchaser"],
                proximity_words=["first party", "second party", "agrees", "shall", "obligations"],
                section_headers=["PARTIES", "CONTRACTING PARTIES", "SIGNATORIES"],
                confidence_boost=0.15
            ),
            "CONTRACT_TERM": EntityContextMapping(
                entity_type="CONTRACT_TERM",
                primary_context=ContextType.CONTRACT_TERMS,
                secondary_contexts=[ContextType.CONTRACTUAL],
                context_indicators=["term", "provision", "clause", "condition", "requirement"],
                proximity_words=["shall", "must", "agrees", "warrants", "represents"],
                section_headers=["TERMS", "PROVISIONS", "CONDITIONS"],
                confidence_boost=0.1
            ),
            "CONTRACT_DATE": EntityContextMapping(
                entity_type="CONTRACT_DATE",
                primary_context=ContextType.CONTRACTUAL,
                secondary_contexts=[ContextType.DATES_DEADLINES],
                context_indicators=["effective date", "execution date", "commencement", "termination"],
                proximity_words=["dated", "as of", "beginning", "ending", "expires"],
                section_headers=["TERM", "EFFECTIVE DATE", "DURATION"],
                confidence_boost=0.15
            ),
            "CONTRACT_AMOUNT": EntityContextMapping(
                entity_type="CONTRACT_AMOUNT",
                primary_context=ContextType.CONTRACTUAL,
                secondary_contexts=[ContextType.MONETARY],
                context_indicators=["consideration", "price", "payment", "amount", "compensation"],
                proximity_words=["dollars", "sum", "total", "payable", "due"],
                section_headers=["CONSIDERATION", "PAYMENT", "COMPENSATION"],
                confidence_boost=0.2
            ),
            
            # Criminal Law Entities
            "CRIME": EntityContextMapping(
                entity_type="CRIME",
                primary_context=ContextType.CRIMINAL,
                secondary_contexts=[ContextType.CRIMINAL_CHARGES],
                context_indicators=["crime", "offense", "violation", "felony", "misdemeanor"],
                proximity_words=["charged", "convicted", "guilty", "alleged", "committed"],
                section_headers=["CHARGES", "CRIMINAL CHARGES", "OFFENSES"],
                confidence_boost=0.2
            ),
            "SENTENCE": EntityContextMapping(
                entity_type="SENTENCE",
                primary_context=ContextType.CRIMINAL,
                secondary_contexts=[ContextType.PROCEDURAL],
                context_indicators=["sentence", "imprisonment", "probation", "parole", "confinement"],
                proximity_words=["years", "months", "imposed", "suspended", "consecutive"],
                section_headers=["SENTENCE", "SENTENCING", "PUNISHMENT"],
                confidence_boost=0.2
            ),
            "PLEA": EntityContextMapping(
                entity_type="PLEA",
                primary_context=ContextType.CRIMINAL,
                secondary_contexts=[ContextType.PROCEDURAL],
                context_indicators=["plea", "plead", "guilty", "not guilty", "nolo contendere"],
                proximity_words=["entered", "agreement", "bargain", "withdraws", "accepts"],
                section_headers=["PLEA", "PLEA AGREEMENT", "ARRAIGNMENT"],
                confidence_boost=0.2
            ),
            "CHARGE": EntityContextMapping(
                entity_type="CHARGE",
                primary_context=ContextType.CRIMINAL_CHARGES,
                secondary_contexts=[ContextType.CRIMINAL],
                context_indicators=["charged", "count", "indictment", "information", "accusation"],
                proximity_words=["felony", "misdemeanor", "degree", "class", "level"],
                section_headers=["CHARGES", "COUNTS", "INDICTMENT"],
                confidence_boost=0.2
            ),
            
            # Property Entities
            "PROPERTY": EntityContextMapping(
                entity_type="PROPERTY",
                primary_context=ContextType.PROPERTY,
                secondary_contexts=[ContextType.CONTRACTUAL],
                context_indicators=["property", "real estate", "land", "premises", "parcel"],
                proximity_words=["located", "described", "bounded", "conveyed", "transferred"],
                section_headers=["PROPERTY DESCRIPTION", "REAL PROPERTY", "PREMISES"],
                confidence_boost=0.15
            ),
            "PROPERTY_OWNER": EntityContextMapping(
                entity_type="PROPERTY_OWNER",
                primary_context=ContextType.PROPERTY,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["owner", "proprietor", "landlord", "lessor", "grantor"],
                proximity_words=["property", "title", "deed", "owns", "possessed"],
                section_headers=["OWNERSHIP", "PROPERTY OWNERS", "TITLE"],
                confidence_boost=0.15
            ),
            "DEED": EntityContextMapping(
                entity_type="DEED",
                primary_context=ContextType.PROPERTY,
                secondary_contexts=[ContextType.LEGAL_DOCUMENTS],
                context_indicators=["deed", "conveyance", "transfer", "grant", "quitclaim"],
                proximity_words=["warranty", "trust", "recorded", "executed", "delivered"],
                section_headers=["DEED", "CONVEYANCE", "TRANSFER"],
                confidence_boost=0.2
            ),
            "EASEMENT": EntityContextMapping(
                entity_type="EASEMENT",
                primary_context=ContextType.PROPERTY,
                secondary_contexts=[ContextType.LEGAL_CONCEPTS],
                context_indicators=["easement", "right of way", "servitude", "access", "use"],
                proximity_words=["granted", "reserved", "appurtenant", "gross", "prescriptive"],
                section_headers=["EASEMENTS", "RIGHTS OF WAY", "SERVITUDES"],
                confidence_boost=0.15
            ),
            
            # Intellectual Property Entities
            "PATENT": EntityContextMapping(
                entity_type="PATENT",
                primary_context=ContextType.INTELLECTUAL_PROPERTY,
                secondary_contexts=[ContextType.PROPERTY],
                context_indicators=["patent", "invention", "claims", "USPTO", "application"],
                proximity_words=["issued", "pending", "infringement", "prior art", "novelty"],
                section_headers=["PATENTS", "INTELLECTUAL PROPERTY", "IP RIGHTS"],
                confidence_boost=0.2
            ),
            "TRADEMARK": EntityContextMapping(
                entity_type="TRADEMARK",
                primary_context=ContextType.INTELLECTUAL_PROPERTY,
                secondary_contexts=[ContextType.PROPERTY],
                context_indicators=["trademark", "service mark", "trade name", "™", "®"],
                proximity_words=["registered", "pending", "infringement", "confusion", "dilution"],
                section_headers=["TRADEMARKS", "MARKS", "BRAND"],
                confidence_boost=0.2
            ),
            "COPYRIGHT": EntityContextMapping(
                entity_type="COPYRIGHT",
                primary_context=ContextType.INTELLECTUAL_PROPERTY,
                secondary_contexts=[ContextType.PROPERTY],
                context_indicators=["copyright", "©", "work", "authorship", "creative"],
                proximity_words=["registered", "infringement", "fair use", "derivative", "original"],
                section_headers=["COPYRIGHT", "COPYRIGHTED WORKS", "AUTHORSHIP"],
                confidence_boost=0.2
            ),
            "TRADE_SECRET": EntityContextMapping(
                entity_type="TRADE_SECRET",
                primary_context=ContextType.INTELLECTUAL_PROPERTY,
                secondary_contexts=[ContextType.PROPERTY],
                context_indicators=["trade secret", "confidential", "proprietary", "formula", "process"],
                proximity_words=["misappropriation", "disclosure", "protection", "competitive", "advantage"],
                section_headers=["TRADE SECRETS", "CONFIDENTIAL INFORMATION", "PROPRIETARY"],
                confidence_boost=0.15
            ),
            
            # Corporate Entities
            "CORPORATION": EntityContextMapping(
                entity_type="CORPORATION",
                primary_context=ContextType.CORPORATE,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["corporation", "inc", "incorporated", "corp", "company"],
                proximity_words=["shareholders", "directors", "officers", "bylaws", "articles"],
                section_headers=["CORPORATE PARTIES", "COMPANIES", "ENTITIES"],
                confidence_boost=0.15
            ),
            "LLC": EntityContextMapping(
                entity_type="LLC",
                primary_context=ContextType.CORPORATE,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["LLC", "L.L.C.", "limited liability company", "limited company"],
                proximity_words=["members", "managers", "operating agreement", "articles", "formation"],
                section_headers=["ENTITIES", "LIMITED LIABILITY COMPANIES", "PARTIES"],
                confidence_boost=0.15
            ),
            "PARTNERSHIP": EntityContextMapping(
                entity_type="PARTNERSHIP",
                primary_context=ContextType.CORPORATE,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["partnership", "LP", "LLP", "general partnership", "limited partnership"],
                proximity_words=["partners", "general partner", "limited partner", "agreement", "interest"],
                section_headers=["PARTNERSHIPS", "ENTITIES", "PARTIES"],
                confidence_boost=0.15
            ),
            "BOARD_MEMBER": EntityContextMapping(
                entity_type="BOARD_MEMBER",
                primary_context=ContextType.CORPORATE,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["director", "board member", "trustee", "board of directors"],
                proximity_words=["chairman", "president", "secretary", "treasurer", "elected"],
                section_headers=["BOARD OF DIRECTORS", "DIRECTORS", "GOVERNANCE"],
                confidence_boost=0.15
            ),
            "SHAREHOLDER": EntityContextMapping(
                entity_type="SHAREHOLDER",
                primary_context=ContextType.CORPORATE,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["shareholder", "stockholder", "equity holder", "investor"],
                proximity_words=["shares", "stock", "voting", "dividend", "proxy"],
                section_headers=["SHAREHOLDERS", "STOCKHOLDERS", "OWNERSHIP"],
                confidence_boost=0.15
            ),
            
            # Financial Entities
            "FINANCIAL_INSTRUMENT": EntityContextMapping(
                entity_type="FINANCIAL_INSTRUMENT",
                primary_context=ContextType.FINANCIAL,
                secondary_contexts=[ContextType.SECURITIES],
                context_indicators=["security", "bond", "note", "debenture", "instrument"],
                proximity_words=["maturity", "interest", "principal", "coupon", "yield"],
                section_headers=["SECURITIES", "FINANCIAL INSTRUMENTS", "INVESTMENTS"],
                confidence_boost=0.15
            ),
            "BANK": EntityContextMapping(
                entity_type="BANK",
                primary_context=ContextType.FINANCIAL,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["bank", "credit union", "savings", "financial institution", "lender"],
                proximity_words=["account", "loan", "deposit", "branch", "routing"],
                section_headers=["FINANCIAL INSTITUTIONS", "BANKS", "LENDERS"],
                confidence_boost=0.15
            ),
            "ACCOUNT": EntityContextMapping(
                entity_type="ACCOUNT",
                primary_context=ContextType.FINANCIAL,
                secondary_contexts=[ContextType.IDENTIFICATION],
                context_indicators=["account", "account number", "account no", "acct"],
                proximity_words=["checking", "savings", "deposit", "balance", "statement"],
                section_headers=["ACCOUNTS", "FINANCIAL ACCOUNTS", "BANK ACCOUNTS"],
                confidence_boost=0.15
            ),
            "TAX": EntityContextMapping(
                entity_type="TAX",
                primary_context=ContextType.FINANCIAL,
                secondary_contexts=[ContextType.MONETARY],
                context_indicators=["tax", "taxation", "IRS", "revenue", "assessment"],
                proximity_words=["income", "property", "sales", "federal", "state"],
                section_headers=["TAXES", "TAX LIABILITY", "TAX ISSUES"],
                confidence_boost=0.15
            ),
            "TAX_ID": EntityContextMapping(
                entity_type="TAX_ID",
                primary_context=ContextType.IDENTIFICATION,
                secondary_contexts=[ContextType.FINANCIAL],
                context_indicators=["EIN", "TIN", "SSN", "tax ID", "employer identification"],
                proximity_words=["federal", "number", "taxpayer", "identification", "IRS"],
                section_headers=["TAX IDENTIFICATION", "TAX NUMBERS", "IDENTIFICATION"],
                confidence_boost=0.2
            ),
            
            # Insurance Entities
            "INSURANCE_COMPANY": EntityContextMapping(
                entity_type="INSURANCE_COMPANY",
                primary_context=ContextType.INSURANCE,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["insurer", "insurance company", "carrier", "underwriter"],
                proximity_words=["policy", "coverage", "premium", "claim", "risk"],
                section_headers=["INSURANCE", "INSURERS", "CARRIERS"],
                confidence_boost=0.15
            ),
            "INSURANCE_POLICY": EntityContextMapping(
                entity_type="INSURANCE_POLICY",
                primary_context=ContextType.INSURANCE,
                secondary_contexts=[ContextType.CONTRACTUAL],
                context_indicators=["policy", "policy number", "coverage", "insurance contract"],
                proximity_words=["premium", "deductible", "limit", "exclusion", "endorsement"],
                section_headers=["INSURANCE POLICY", "COVERAGE", "POLICY TERMS"],
                confidence_boost=0.15
            ),
            "CLAIM": EntityContextMapping(
                entity_type="CLAIM",
                primary_context=ContextType.INSURANCE,
                secondary_contexts=[ContextType.LEGAL_ACTIONS],
                context_indicators=["claim", "claim number", "loss", "demand", "request"],
                proximity_words=["filed", "denied", "approved", "pending", "settlement"],
                section_headers=["CLAIMS", "INSURANCE CLAIMS", "LOSSES"],
                confidence_boost=0.15
            ),
            "COVERAGE": EntityContextMapping(
                entity_type="COVERAGE",
                primary_context=ContextType.INSURANCE,
                secondary_contexts=[ContextType.CONTRACTUAL],
                context_indicators=["coverage", "covered", "protection", "benefit", "limit"],
                proximity_words=["policy", "exclusion", "deductible", "maximum", "sublimit"],
                section_headers=["COVERAGE", "POLICY COVERAGE", "BENEFITS"],
                confidence_boost=0.15
            ),
            
            # Employment Entities
            "EMPLOYER": EntityContextMapping(
                entity_type="EMPLOYER",
                primary_context=ContextType.EMPLOYMENT,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["employer", "company", "business", "organization", "firm"],
                proximity_words=["employee", "hire", "terminate", "benefits", "wages"],
                section_headers=["EMPLOYMENT", "EMPLOYER", "COMPANY"],
                confidence_boost=0.15
            ),
            "EMPLOYEE": EntityContextMapping(
                entity_type="EMPLOYEE",
                primary_context=ContextType.EMPLOYMENT,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["employee", "worker", "staff", "personnel", "associate"],
                proximity_words=["hired", "terminated", "position", "duties", "compensation"],
                section_headers=["EMPLOYMENT", "EMPLOYEES", "PERSONNEL"],
                confidence_boost=0.15
            ),
            "UNION": EntityContextMapping(
                entity_type="UNION",
                primary_context=ContextType.EMPLOYMENT,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["union", "labor organization", "local", "international", "AFL-CIO"],
                proximity_words=["bargaining", "collective", "members", "representation", "strike"],
                section_headers=["UNION", "LABOR ORGANIZATION", "BARGAINING UNIT"],
                confidence_boost=0.15
            ),
            "EMPLOYMENT_AGREEMENT": EntityContextMapping(
                entity_type="EMPLOYMENT_AGREEMENT",
                primary_context=ContextType.EMPLOYMENT,
                secondary_contexts=[ContextType.CONTRACTUAL],
                context_indicators=["employment agreement", "employment contract", "offer letter", "terms of employment"],
                proximity_words=["compensation", "benefits", "duties", "termination", "non-compete"],
                section_headers=["EMPLOYMENT AGREEMENT", "EMPLOYMENT TERMS", "CONTRACT"],
                confidence_boost=0.15
            ),
            
            # Family Law Entities
            "SPOUSE": EntityContextMapping(
                entity_type="SPOUSE",
                primary_context=ContextType.FAMILY,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["spouse", "husband", "wife", "partner", "married"],
                proximity_words=["marriage", "divorce", "separation", "support", "custody"],
                section_headers=["PARTIES", "SPOUSES", "MARRIAGE"],
                confidence_boost=0.15
            ),
            "CHILD": EntityContextMapping(
                entity_type="CHILD",
                primary_context=ContextType.FAMILY,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["child", "children", "minor", "son", "daughter"],
                proximity_words=["custody", "support", "visitation", "parent", "guardian"],
                section_headers=["CHILDREN", "MINORS", "DEPENDENTS"],
                confidence_boost=0.15
            ),
            "CUSTODY": EntityContextMapping(
                entity_type="CUSTODY",
                primary_context=ContextType.FAMILY,
                secondary_contexts=[ContextType.LEGAL_CONCEPTS],
                context_indicators=["custody", "custodial", "physical custody", "legal custody", "joint custody"],
                proximity_words=["child", "parent", "visitation", "primary", "shared"],
                section_headers=["CUSTODY", "CHILD CUSTODY", "PARENTING"],
                confidence_boost=0.2
            ),
            "DIVORCE_DECREE": EntityContextMapping(
                entity_type="DIVORCE_DECREE",
                primary_context=ContextType.FAMILY,
                secondary_contexts=[ContextType.LEGAL_DOCUMENTS],
                context_indicators=["divorce decree", "decree", "dissolution", "divorce judgment", "final decree"],
                proximity_words=["marriage", "dissolved", "granted", "entered", "property division"],
                section_headers=["DECREE", "DIVORCE DECREE", "DISSOLUTION"],
                confidence_boost=0.2
            ),
            
            # Immigration Entities
            "VISA": EntityContextMapping(
                entity_type="VISA",
                primary_context=ContextType.IMMIGRATION,
                secondary_contexts=[ContextType.IDENTIFICATION],
                context_indicators=["visa", "H-1B", "L-1", "F-1", "green card", "immigrant visa"],
                proximity_words=["status", "petition", "approval", "expires", "category"],
                section_headers=["IMMIGRATION STATUS", "VISA", "IMMIGRATION"],
                confidence_boost=0.2
            ),
            "IMMIGRATION_STATUS": EntityContextMapping(
                entity_type="IMMIGRATION_STATUS",
                primary_context=ContextType.IMMIGRATION,
                secondary_contexts=[ContextType.STATUS],
                context_indicators=["status", "lawful permanent resident", "citizen", "nonimmigrant", "asylee"],
                proximity_words=["immigration", "authorized", "admitted", "adjustment", "maintain"],
                section_headers=["STATUS", "IMMIGRATION STATUS", "LEGAL STATUS"],
                confidence_boost=0.15
            ),
            "USCIS_FORM": EntityContextMapping(
                entity_type="USCIS_FORM",
                primary_context=ContextType.IMMIGRATION,
                secondary_contexts=[ContextType.LEGAL_DOCUMENTS],
                context_indicators=["I-130", "I-485", "I-765", "N-400", "Form", "USCIS"],
                proximity_words=["petition", "application", "filed", "approved", "pending"],
                section_headers=["FORMS", "USCIS FORMS", "APPLICATIONS"],
                confidence_boost=0.2
            ),
            
            # Medical Entities
            "MEDICAL_PROVIDER": EntityContextMapping(
                entity_type="MEDICAL_PROVIDER",
                primary_context=ContextType.MEDICAL,
                secondary_contexts=[ContextType.GENERAL_PARTIES],
                context_indicators=["doctor", "physician", "hospital", "clinic", "medical provider"],
                proximity_words=["treatment", "diagnosis", "patient", "care", "medical"],
                section_headers=["MEDICAL PROVIDERS", "HEALTHCARE", "PHYSICIANS"],
                confidence_boost=0.15
            ),
            "MEDICAL_CONDITION": EntityContextMapping(
                entity_type="MEDICAL_CONDITION",
                primary_context=ContextType.MEDICAL,
                secondary_contexts=[ContextType.EVIDENCE],
                context_indicators=["diagnosis", "condition", "disease", "injury", "illness"],
                proximity_words=["suffered", "treated", "chronic", "acute", "symptoms"],
                section_headers=["MEDICAL CONDITIONS", "DIAGNOSES", "INJURIES"],
                confidence_boost=0.15
            ),
            "MEDICAL_TREATMENT": EntityContextMapping(
                entity_type="MEDICAL_TREATMENT",
                primary_context=ContextType.MEDICAL,
                secondary_contexts=[ContextType.EVIDENCE],
                context_indicators=["treatment", "surgery", "procedure", "therapy", "medication"],
                proximity_words=["received", "underwent", "prescribed", "administered", "performed"],
                section_headers=["TREATMENT", "MEDICAL TREATMENT", "PROCEDURES"],
                confidence_boost=0.15
            ),
            "MEDICAL_RECORD": EntityContextMapping(
                entity_type="MEDICAL_RECORD",
                primary_context=ContextType.MEDICAL,
                secondary_contexts=[ContextType.EVIDENCE],
                context_indicators=["medical record", "chart", "history", "report", "documentation"],
                proximity_words=["patient", "examination", "findings", "notes", "discharge"],
                section_headers=["MEDICAL RECORDS", "MEDICAL DOCUMENTATION", "RECORDS"],
                confidence_boost=0.15
            ),
            
            # Additional Entity Types (continuing with remaining 180+ entities)
            # Due to length constraints, I'll provide a template for the remaining entities
            # Each follows the same pattern with appropriate context mappings
            
            # Environmental Law Entities
            "ENVIRONMENTAL_LAW": EntityContextMapping(
                entity_type="ENVIRONMENTAL_LAW",
                primary_context=ContextType.ENVIRONMENTAL,
                secondary_contexts=[ContextType.LEGAL_CONCEPTS],
                context_indicators=["environmental", "EPA", "pollution", "emissions", "contamination"],
                proximity_words=["violation", "compliance", "permit", "regulation", "cleanup"],
                section_headers=["ENVIRONMENTAL LAW", "ENVIRONMENTAL ISSUES", "EPA"],
                confidence_boost=0.15
            ),
            
            # Continue with remaining entities...
            # Each entity type should have its complete mapping
        }
        
        # Add remaining entity mappings programmatically for brevity
        self._add_remaining_entity_mappings()
    
    def _add_remaining_entity_mappings(self):
        """Add mappings for remaining entity types"""
        # This method adds the remaining ~180 entity types
        # Each follows the same EntityContextMapping structure
        
        remaining_entities = {
            "POLLUTANT": ContextType.ENVIRONMENTAL,
            "ENVIRONMENTAL_PERMIT": ContextType.ENVIRONMENTAL,
            "BANKRUPTCY_CHAPTER": ContextType.BANKRUPTCY,
            "CREDITOR": ContextType.BANKRUPTCY,
            "DEBTOR": ContextType.BANKRUPTCY,
            "TRUSTEE": ContextType.BANKRUPTCY,
            "AGENCY": ContextType.ADMINISTRATIVE,
            "ADMINISTRATIVE_ORDER": ContextType.ADMINISTRATIVE,
            "HEARING": ContextType.PROCEDURAL,
            "LICENSE": ContextType.ADMINISTRATIVE,
            "EVIDENCE": ContextType.EVIDENCE,
            "DISCOVERY": ContextType.DISCOVERY,
            "EXHIBIT": ContextType.EVIDENCE,
            "DEPOSITION": ContextType.DISCOVERY,
            "TREATY": ContextType.INTERNATIONAL,
            "INTERNATIONAL_COURT": ContextType.INTERNATIONAL,
            "INTERNATIONAL_LAW": ContextType.INTERNATIONAL,
            "ARBITRATION": ContextType.ARBITRATION,
            "MEDIATION": ContextType.ARBITRATION,
            "ARBITRATOR": ContextType.ARBITRATION,
            "MEDIATOR": ContextType.ARBITRATION,
            "SECURITY": ContextType.SECURITIES,
            "SEC_FILING": ContextType.SECURITIES,
            "STOCK_EXCHANGE": ContextType.SECURITIES,
            "ANTITRUST_LAW": ContextType.LEGAL_CONCEPTS,
            "MARKET": ContextType.FINANCIAL,
            "MERGER": ContextType.CORPORATE,
            "VESSEL": ContextType.MARITIME,
            "MARITIME_LAW": ContextType.MARITIME,
            "PORT": ContextType.MARITIME,
            "AIRCRAFT": ContextType.AVIATION,
            "AIRLINE": ContextType.AVIATION,
            "FAA_REGULATION": ContextType.AVIATION,
            "UTILITY": ContextType.ADMINISTRATIVE,
            "ENERGY_REGULATION": ContextType.ADMINISTRATIVE,
            "PIPELINE": ContextType.NATURAL_RESOURCES,
            "TELECOM_COMPANY": ContextType.TELECOMMUNICATIONS,
            "FCC_REGULATION": ContextType.TELECOMMUNICATIONS,
            "EDUCATIONAL_INSTITUTION": ContextType.EDUCATION,
            "EDUCATION_LAW": ContextType.EDUCATION,
            "STUDENT": ContextType.EDUCATION,
            "HEALTHCARE_PROVIDER": ContextType.HEALTHCARE,
            "HEALTHCARE_LAW": ContextType.HEALTHCARE,
            "INSURANCE_PLAN": ContextType.HEALTHCARE,
            "TECHNOLOGY_COMPANY": ContextType.TECHNOLOGY,
            "SOFTWARE": ContextType.TECHNOLOGY,
            "DOMAIN_NAME": ContextType.TECHNOLOGY,
            "DATA_BREACH": ContextType.TECHNOLOGY,
            "PRIVACY_LAW": ContextType.TECHNOLOGY,
            "PERSONAL_DATA": ContextType.TECHNOLOGY,
            "CONSENT": ContextType.CONTRACT_TERMS,
            "ENTERTAINMENT_ENTITY": ContextType.ENTERTAINMENT,
            "TALENT": ContextType.ENTERTAINMENT,
            "SPORTS_ENTITY": ContextType.ENTERTAINMENT,
            "ATHLETE": ContextType.ENTERTAINMENT,
            "NONPROFIT": ContextType.NONPROFIT,
            "DONOR": ContextType.NONPROFIT,
            "GRANT": ContextType.NONPROFIT,
            "GUARDIAN": ContextType.ESTATE_PLANNING,
            "POWER_OF_ATTORNEY": ContextType.ESTATE_PLANNING,
            "LIVING_WILL": ContextType.ESTATE_PLANNING,
            "MILITARY_RANK": ContextType.MILITARY,
            "MILITARY_UNIT": ContextType.MILITARY,
            "UCMJ": ContextType.MILITARY,
            "CONTRACTOR": ContextType.CONSTRUCTION,
            "CONSTRUCTION_PROJECT": ContextType.CONSTRUCTION,
            "MECHANIC_LIEN": ContextType.CONSTRUCTION,
            "FARM": ContextType.AGRICULTURE,
            "AGRICULTURAL_LAW": ContextType.AGRICULTURE,
            "CROP": ContextType.AGRICULTURE,
            "MINE": ContextType.NATURAL_RESOURCES,
            "MINERAL_RIGHTS": ContextType.NATURAL_RESOURCES,
            "NATURAL_RESOURCE": ContextType.NATURAL_RESOURCES,
            "TRIBE": ContextType.TRIBAL,
            "TRIBAL_COURT": ContextType.TRIBAL,
            "RESERVATION": ContextType.TRIBAL,
            "PARTY": ContextType.GENERAL_PARTIES,
            "AGREEMENT": ContextType.CONTRACTUAL,
            "OBLIGATION": ContextType.CONTRACT_TERMS,
            "RIGHT": ContextType.LEGAL_CONCEPTS,
            "LIABILITY": ContextType.LEGAL_CONCEPTS,
            "DATE": ContextType.DATES_DEADLINES,
            "TIME": ContextType.TEMPORAL,
            "DEADLINE": ContextType.DATES_DEADLINES,
            "TERM": ContextType.TEMPORAL,
            "ADDRESS": ContextType.CONTACT_INFO,
            "CITY": ContextType.JURISDICTION,
            "STATE": ContextType.JURISDICTION,
            "COUNTRY": ContextType.JURISDICTION,
            "JURISDICTION": ContextType.JURISDICTION,
            "MONEY": ContextType.MONETARY,
            "CURRENCY": ContextType.MONETARY,
            "PERCENTAGE": ContextType.QUANTITATIVE,
            "INTEREST_RATE": ContextType.QUANTITATIVE,
            "PHONE": ContextType.CONTACT_INFO,
            "EMAIL": ContextType.CONTACT_INFO,
            "FAX": ContextType.CONTACT_INFO,
            "WEBSITE": ContextType.CONTACT_INFO,
            "SSN": ContextType.IDENTIFICATION,
            "DRIVER_LICENSE": ContextType.IDENTIFICATION,
            "PASSPORT": ContextType.IDENTIFICATION,
            "BAR_NUMBER": ContextType.IDENTIFICATION,
            "BAILIFF": ContextType.COURT_PERSONNEL,
            "CLERK": ContextType.COURT_PERSONNEL,
            "PARALEGAL": ContextType.COURT_PERSONNEL,
            "NOTARY": ContextType.COURT_PERSONNEL,
            "PROSECUTOR": ContextType.COURT_PERSONNEL,
            "PUBLIC_DEFENDER": ContextType.COURT_PERSONNEL,
            "COURT_REPORTER": ContextType.COURT_PERSONNEL,
            "LEGAL_GUARDIAN": ContextType.ESTATE_PLANNING,
            "AFFIDAVIT": ContextType.LEGAL_DOCUMENTS,
            "SUBPOENA": ContextType.LEGAL_DOCUMENTS,
            "WARRANT": ContextType.LEGAL_DOCUMENTS,
            "WILL": ContextType.ESTATE_PLANNING,
            "TRUST": ContextType.ESTATE_PLANNING,
            "SETTLEMENT": ContextType.LEGAL_DOCUMENTS,
            "STIPULATION": ContextType.LEGAL_DOCUMENTS,
            "NOTICE": ContextType.LEGAL_DOCUMENTS,
            "APPEAL": ContextType.PROCEDURAL,
            "ARRAIGNMENT": ContextType.CRIMINAL,
            "BAIL": ContextType.CRIMINAL,
            "DISCOVERY_REQUEST": ContextType.DISCOVERY,
            "VOIR_DIRE": ContextType.PROCEDURAL,
            "CROSS_EXAMINATION": ContextType.PROCEDURAL,
            "CLOSING_ARGUMENT": ContextType.PROCEDURAL,
            "LEGAL_TEST": ContextType.LEGAL_STANDARDS,
            "BURDEN_OF_PROOF": ContextType.LEGAL_STANDARDS,
            "PRECEDENT": ContextType.LEGAL_CONCEPTS,
            "HOLDING": ContextType.LEGAL_CONCEPTS,
            "DICTA": ContextType.LEGAL_CONCEPTS,
            "TORT": ContextType.LEGAL_CONCEPTS,
            "BREACH": ContextType.LEGAL_CONCEPTS,
            "DAMAGES_TYPE": ContextType.MONETARY,
            "EQUITABLE_RELIEF": ContextType.LEGAL_CONCEPTS,
            "CLASS_ACTION": ContextType.PROCEDURAL,
            "GOVERNMENT_ENTITY": ContextType.GOVERNMENT,
            "LEGISLATURE": ContextType.GOVERNMENT,
            "EXECUTIVE": ContextType.GOVERNMENT,
            "MUNICIPALITY": ContextType.GOVERNMENT,
            "COUNTY_ENTITY": ContextType.GOVERNMENT,
            "STATUTE_OF_LIMITATIONS": ContextType.DATES_DEADLINES,
            "FILING_DEADLINE": ContextType.DATES_DEADLINES,
            "EFFECTIVE_DATE": ContextType.DATES_DEADLINES,
            "EXPIRATION_DATE": ContextType.DATES_DEADLINES,
            "QUANTITY": ContextType.QUANTITATIVE,
            "RATIO": ContextType.QUANTITATIVE,
            "FRACTION": ContextType.QUANTITATIVE,
            "LEGAL_STATUS": ContextType.STATUS,
            "CASE_STATUS": ContextType.STATUS,
            "COMPLIANCE_STATUS": ContextType.STATUS,
            "FELONY": ContextType.CRIMINAL_CHARGES,
            "MISDEMEANOR": ContextType.CRIMINAL_CHARGES,
            "INFRACTION": ContextType.CRIMINAL_CHARGES,
            "FIDUCIARY": ContextType.BENEFICIARIES,
            "BENEFICIARY": ContextType.BENEFICIARIES,
            "HEIR": ContextType.BENEFICIARIES,
            "EXECUTOR": ContextType.BENEFICIARIES,
            "LEGAL_ACTION": ContextType.LEGAL_ACTIONS,
            "OBJECTION": ContextType.LEGAL_ACTIONS,
            "WAIVER": ContextType.LEGAL_ACTIONS,
            "RELEASE": ContextType.LEGAL_ACTIONS,
            "CONDITION_PRECEDENT": ContextType.CONTRACT_TERMS,
            "CONDITION_SUBSEQUENT": ContextType.CONTRACT_TERMS,
            "CONTINGENCY": ContextType.CONTRACT_TERMS,
            "INTERPRETATION": ContextType.LEGAL_CONCEPTS,
            "AMBIGUITY": ContextType.LEGAL_CONCEPTS,
            "DEFINITION": ContextType.LEGAL_CONCEPTS,
            "WHEREAS_CLAUSE": ContextType.CONTRACT_TERMS,
            "THEREFORE_CLAUSE": ContextType.CONTRACT_TERMS,
            "HERETOFORE": ContextType.CONTRACT_TERMS,
            "LEGAL_CITATION_SIGNAL": ContextType.LEGAL_CITATIONS,
            "LEGAL_QUALIFIER": ContextType.LEGAL_CONCEPTS,
            "LEGAL_EXCEPTION": ContextType.LEGAL_CONCEPTS,
            "LEGAL_LIMITATION": ContextType.LEGAL_CONCEPTS,
            "SIGNATURE_BLOCK": ContextType.SIGNATURE,
            "SEAL": ContextType.SIGNATURE,
            "ACKNOWLEDGMENT": ContextType.SIGNATURE,
            "CERTIFICATION": ContextType.SIGNATURE,
            "CROSS_REFERENCE": ContextType.CROSS_REFERENCES,
            "INCORPORATION": ContextType.CROSS_REFERENCES,
            "SCHEDULE_REFERENCE": ContextType.CROSS_REFERENCES,
            "STANDARD_OF_CARE": ContextType.LEGAL_STANDARDS,
            "GOOD_FAITH": ContextType.LEGAL_STANDARDS,
            "MATERIALITY": ContextType.LEGAL_STANDARDS,
            "AMENDMENT": ContextType.LEGAL_DOCUMENTS,
            "SUPPLEMENT": ContextType.LEGAL_DOCUMENTS,
            "RESTATEMENT": ContextType.LEGAL_DOCUMENTS,
            "LEGAL_PRESUMPTION": ContextType.LEGAL_CONCEPTS,
            "ESTOPPEL": ContextType.LEGAL_CONCEPTS,
            "LACHES": ContextType.LEGAL_CONCEPTS,
            "VENUE": ContextType.VENUE_FORUM,
            "FORUM": ContextType.VENUE_FORUM,
            "CHOICE_OF_LAW": ContextType.VENUE_FORUM,
            "SEVERABILITY": ContextType.CONTRACT_CLAUSES,
            "FORCE_MAJEURE": ContextType.CONTRACT_CLAUSES,
            "INDEMNIFICATION": ContextType.CONTRACT_CLAUSES,
            "REPRESENTATIONS": ContextType.CONTRACT_CLAUSES,
            "COVENANT": ContextType.CONTRACT_CLAUSES,
            "RECITAL": ContextType.CONTRACT_CLAUSES,
        }
        
        # Add basic mappings for remaining entities
        for entity_type, primary_context in remaining_entities.items():
            if entity_type not in self.entity_mappings:
                self.entity_mappings[entity_type] = EntityContextMapping(
                    entity_type=entity_type,
                    primary_context=primary_context,
                    secondary_contexts=[],
                    context_indicators=[entity_type.lower().replace("_", " ")],
                    proximity_words=[],
                    section_headers=[entity_type.replace("_", " ")],
                    confidence_boost=0.1
                )
    
    def _initialize_context_groups(self):
        """Initialize context type groupings"""
        self.context_groups = {
            ContextType.CASE_HEADER: [
                "COURT", "JUDGE", "DOCKET_NUMBER", "CASE", "PLAINTIFF", "DEFENDANT"
            ],
            ContextType.PARTY_SECTION: [
                "PLAINTIFF", "DEFENDANT", "ATTORNEY", "LAW_FIRM", "CONTRACT_PARTY"
            ],
            ContextType.DATES_DEADLINES: [
                "DATE", "TIME", "DEADLINE", "CONTRACT_DATE", "FILING_DEADLINE",
                "EFFECTIVE_DATE", "EXPIRATION_DATE", "STATUTE_OF_LIMITATIONS"
            ],
            ContextType.MONETARY: [
                "MONEY", "CURRENCY", "CONTRACT_AMOUNT", "DAMAGES_TYPE", "TAX"
            ],
            ContextType.LEGAL_CITATIONS: [
                "CITATION", "CASE", "STATUTE", "REGULATION", "CONSTITUTIONAL_PROVISION"
            ],
            # Add more context groupings as needed
        }
    
    def _initialize_context_indicators(self):
        """Initialize context-level indicators"""
        self.context_indicators = {
            ContextType.CASE_HEADER: {
                "patterns": [
                    r"IN THE.*COURT",
                    r"CASE NO\.",
                    r"DOCKET NO\.",
                    r"BEFORE.*JUDGE"
                ],
                "keywords": ["caption", "style", "court", "judge", "docket"]
            },
            ContextType.PARTY_SECTION: {
                "patterns": [
                    r"PLAINTIFF.*v\.",
                    r"PARTIES:",
                    r"REPRESENTED BY"
                ],
                "keywords": ["plaintiff", "defendant", "parties", "counsel", "attorney"]
            },
            ContextType.DATES_DEADLINES: {
                "patterns": [
                    r"\d{1,2}/\d{1,2}/\d{2,4}",
                    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
                    r"deadline.*\d{1,2}"
                ],
                "keywords": ["date", "deadline", "expires", "effective", "filed"]
            },
            # Add more context indicators
        }
    
    def get_entity_context(self, entity_type: str) -> Optional[EntityContextMapping]:
        """Get context mapping for a specific entity type"""
        return self.entity_mappings.get(entity_type)
    
    def get_entities_by_context(self, context_type: ContextType) -> List[str]:
        """Get all entity types associated with a context type"""
        entities = []
        for entity_type, mapping in self.entity_mappings.items():
            if (mapping.primary_context == context_type or 
                context_type in mapping.secondary_contexts):
                entities.append(entity_type)
        return entities
    
    def get_context_indicators_for_type(self, context_type: ContextType) -> Dict:
        """Get indicators for a specific context type"""
        return self.context_indicators.get(context_type, {})
    
    def suggest_entity_types_for_context(self, text: str, max_suggestions: int = 5) -> List[str]:
        """Suggest likely entity types based on context indicators in text"""
        scores = {}
        
        for entity_type, mapping in self.entity_mappings.items():
            score = 0.0
            
            # Check context indicators
            for indicator in mapping.context_indicators:
                if indicator.lower() in text.lower():
                    score += 1.0
            
            # Check proximity words
            for word in mapping.proximity_words:
                if word.lower() in text.lower():
                    score += 0.5
            
            # Check section headers
            for header in mapping.section_headers:
                if header.lower() in text.lower():
                    score += 2.0
            
            if score > 0:
                scores[entity_type] = score
        
        # Sort by score and return top suggestions
        sorted_entities = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [entity for entity, _ in sorted_entities[:max_suggestions]]
    
    def get_confidence_boost(self, entity_type: str, context_matches: bool) -> float:
        """Get confidence boost for entity when found in expected context"""
        if context_matches and entity_type in self.entity_mappings:
            return self.entity_mappings[entity_type].confidence_boost
        return 0.0