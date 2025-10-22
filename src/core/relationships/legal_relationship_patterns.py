"""
Legal Relationship Patterns for CALES Entity Extraction

This module contains comprehensive regex and linguistic patterns for extracting
relationships between legal entities in documents. Patterns are organized by
relationship category and optimized for legal text.
"""

import re
from typing import Dict, List, Tuple, Optional, Pattern
from dataclasses import dataclass
from enum import Enum


@dataclass
class RelationshipPattern:
    """Container for a relationship extraction pattern"""
    pattern: str
    compiled_regex: Pattern
    relationship_type: str
    subject_types: List[str]
    object_types: List[str]
    confidence: float
    bidirectional: bool = False
    requires_context: bool = False
    context_keywords: List[str] = None
    examples: List[str] = None
    
    def __post_init__(self):
        if self.context_keywords is None:
            self.context_keywords = []
        if self.examples is None:
            self.examples = []


class LegalRelationshipPatterns:
    """
    Comprehensive collection of legal relationship patterns.
    Patterns are designed to capture relationships between entities
    in legal documents with high precision.
    """
    
    def __init__(self):
        """Initialize and compile all relationship patterns"""
        self.patterns: Dict[str, List[RelationshipPattern]] = {}
        self._initialize_patterns()
        self._compile_patterns()
    
    def _initialize_patterns(self):
        """Initialize all pattern categories"""
        self.patterns = {
            "law_firm": self._get_law_firm_patterns(),
            "judge": self._get_judge_patterns(),
            "party": self._get_party_patterns(),
            "monetary": self._get_monetary_patterns(),
            "temporal": self._get_temporal_patterns(),
            "court": self._get_court_patterns(),
            "document": self._get_document_patterns(),
            "citation": self._get_citation_patterns(),
            "corporate": self._get_corporate_patterns(),
            "criminal": self._get_criminal_patterns(),
            "property": self._get_property_patterns(),
            "contractual": self._get_contractual_patterns(),
            "procedural": self._get_procedural_patterns(),
            "jurisdictional": self._get_jurisdictional_patterns()
        }
    
    def _compile_patterns(self):
        """Compile all regex patterns for efficiency"""
        for category, pattern_list in self.patterns.items():
            for pattern in pattern_list:
                try:
                    pattern.compiled_regex = re.compile(
                        pattern.pattern,
                        re.IGNORECASE | re.MULTILINE | re.DOTALL
                    )
                except re.error as e:
                    print(f"Error compiling pattern in {category}: {pattern.pattern}")
                    print(f"Error: {e}")
                    # Use a dummy pattern that never matches
                    pattern.compiled_regex = re.compile(r'(?!.*)')
    
    def _get_law_firm_patterns(self) -> List[RelationshipPattern]:
        """Patterns for law firm relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?P<firm>[A-Z][A-Za-z\s&,]+(?:LLP|LLC|PC|PA|PLLC|Law\s+(?:Firm|Group|Office)))\s+(?:represents?|representing|represented\s+by|counsel\s+for|attorneys?\s+for)\s+(?P<client>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="represents",
                subject_types=["LAW_FIRM", "ATTORNEY"],
                object_types=["PLAINTIFF", "DEFENDANT", "PARTY", "CORPORATION", "PERSON"],
                confidence=0.9,
                examples=["Smith & Associates represents John Doe", "Jones Law Firm representing the plaintiff"]
            ),
            RelationshipPattern(
                pattern=r'(?P<firm1>[A-Z][A-Za-z\s&,]+(?:LLP|LLC|PC))\s+(?:and|with|alongside)\s+(?P<firm2>[A-Z][A-Za-z\s&,]+(?:LLP|LLC|PC))\s+(?:as\s+)?co-counsel',
                compiled_regex=None,
                relationship_type="co_counsel",
                subject_types=["LAW_FIRM"],
                object_types=["LAW_FIRM"],
                confidence=0.95,
                bidirectional=True,
                examples=["Smith LLP and Jones LLC as co-counsel"]
            ),
            RelationshipPattern(
                pattern=r'(?P<attorney>[A-Z][a-z]+\s+[A-Z][a-z]+),?\s+(?:Esq\.|Esquire|Attorney),?\s+(?:of|from|with)\s+(?P<firm>[A-Z][A-Za-z\s&,]+(?:LLP|LLC|PC|Law\s+Firm))',
                compiled_regex=None,
                relationship_type="affiliated_with",
                subject_types=["ATTORNEY"],
                object_types=["LAW_FIRM"],
                confidence=0.85,
                examples=["John Smith, Esq. of Smith & Associates LLP"]
            ),
            RelationshipPattern(
                pattern=r'(?P<firm>[A-Z][A-Za-z\s&,]+(?:LLP|LLC|PC))\s+(?:appearing|appeared)\s+(?:for|on\s+behalf\s+of)\s+(?P<party>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="appears_for",
                subject_types=["LAW_FIRM", "ATTORNEY"],
                object_types=["PARTY", "PLAINTIFF", "DEFENDANT"],
                confidence=0.85,
                examples=["ABC Law Firm appearing for the defendant"]
            ),
            RelationshipPattern(
                pattern=r'(?P<party>[\w\s,\.]+)\s+(?:retained|hired|engaged)\s+(?P<firm>[A-Z][A-Za-z\s&,]+(?:LLP|LLC|PC|Law\s+Firm))',
                compiled_regex=None,
                relationship_type="retained_by",
                subject_types=["LAW_FIRM"],
                object_types=["PARTY", "CORPORATION", "PERSON"],
                confidence=0.85,
                examples=["John Doe retained Smith & Associates LLP"]
            )
        ]
    
    def _get_judge_patterns(self) -> List[RelationshipPattern]:
        """Patterns for judge relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?:Judge|Justice|Magistrate|Hon(?:orable)?\.?)\s+(?P<judge>[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)\s+(?:presiding|presides?\s+over|presided\s+over)\s+(?P<case>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="presides_over",
                subject_types=["JUDGE"],
                object_types=["CASE", "PROCEEDING", "HEARING"],
                confidence=0.95,
                examples=["Judge Smith presiding over the case", "Justice Roberts presides over oral arguments"]
            ),
            RelationshipPattern(
                pattern=r'(?:Judge|Justice|Magistrate)\s+(?P<judge>[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)\s+(?:rendered|issued|entered|handed\s+down|delivered)\s+(?:a\s+)?(?P<decision>(?:decision|judgment|ruling|order|verdict|opinion))',
                compiled_regex=None,
                relationship_type="rendered",
                subject_types=["JUDGE"],
                object_types=["JUDGMENT", "ORDER", "DECISION"],
                confidence=0.9,
                examples=["Judge Johnson rendered a decision", "Justice Lee issued an order"]
            ),
            RelationshipPattern(
                pattern=r'(?P<motion>[\w\s]+(?:motion|petition|request))\s+(?:was\s+)?(?:granted|denied|sustained|overruled)\s+by\s+(?:Judge|Justice)\s+(?P<judge>[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)',
                compiled_regex=None,
                relationship_type="ruled_on",
                subject_types=["JUDGE"],
                object_types=["MOTION", "PETITION", "REQUEST"],
                confidence=0.85,
                examples=["Motion to dismiss was granted by Judge Smith"]
            ),
            RelationshipPattern(
                pattern=r'(?P<case>[\w\s]+\s+v\.\s+[\w\s]+)\s+(?:assigned\s+to|before|transferred\s+to)\s+(?:Judge|Justice)\s+(?P<judge>[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)',
                compiled_regex=None,
                relationship_type="assigned_to",
                subject_types=["CASE"],
                object_types=["JUDGE"],
                confidence=0.85,
                examples=["Smith v. Jones assigned to Judge Brown"]
            ),
            RelationshipPattern(
                pattern=r'(?:Judge|Justice)\s+(?P<judge>[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)\s+(?:of\s+the\s+)?(?P<court>[\w\s]+Court)',
                compiled_regex=None,
                relationship_type="member_of",
                subject_types=["JUDGE"],
                object_types=["COURT"],
                confidence=0.8,
                examples=["Judge Smith of the District Court"]
            )
        ]
    
    def _get_party_patterns(self) -> List[RelationshipPattern]:
        """Patterns for party relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?P<plaintiff>[\w\s,\.]+)\s+(?:sued|sues|filed\s+suit\s+against|brought\s+action\s+against|commenced\s+proceedings?\s+against)\s+(?P<defendant>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="sues",
                subject_types=["PLAINTIFF", "PARTY", "PERSON", "CORPORATION"],
                object_types=["DEFENDANT", "PARTY", "PERSON", "CORPORATION"],
                confidence=0.9,
                examples=["John Doe sued ABC Corporation", "Plaintiff filed suit against the defendants"]
            ),
            RelationshipPattern(
                pattern=r'(?P<appellant>[\w\s,\.]+)\s+(?:appeals?|appealed|appealing)\s+(?:against|from)?\s+(?P<appellee>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="appeals_against",
                subject_types=["APPELLANT", "PARTY"],
                object_types=["APPELLEE", "PARTY"],
                confidence=0.85,
                examples=["Smith appeals against Jones", "Defendant appealed from the judgment"]
            ),
            RelationshipPattern(
                pattern=r'(?P<party1>[\w\s,\.]+)\s+(?:settled|reached\s+settlement|agreed\s+to\s+settle)\s+with\s+(?P<party2>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="settles_with",
                subject_types=["PARTY", "PLAINTIFF", "DEFENDANT"],
                object_types=["PARTY", "PLAINTIFF", "DEFENDANT"],
                confidence=0.85,
                bidirectional=True,
                examples=["The parties settled with each other", "Plaintiff agreed to settle with defendant"]
            ),
            RelationshipPattern(
                pattern=r'(?P<defendant>[\w\s,\.]+)\s+(?:defends?|defended|defending)\s+against\s+(?:claims?\s+by|allegations?\s+by|charges?\s+by)?\s+(?P<plaintiff>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="defends_against",
                subject_types=["DEFENDANT", "PARTY"],
                object_types=["PLAINTIFF", "PARTY"],
                confidence=0.8,
                examples=["ABC Corp defending against claims by John Doe"]
            ),
            RelationshipPattern(
                pattern=r'(?P<party1>[\w\s,\.]+)\s+(?:and|&)\s+(?P<party2>[\w\s,\.]+)\s+(?:entered\s+into|executed|signed)\s+(?:a\s+)?(?:contract|agreement)',
                compiled_regex=None,
                relationship_type="contracts_with",
                subject_types=["PARTY", "PERSON", "CORPORATION"],
                object_types=["PARTY", "PERSON", "CORPORATION"],
                confidence=0.85,
                bidirectional=True,
                examples=["Smith and Jones entered into a contract"]
            )
        ]
    
    def _get_monetary_patterns(self) -> List[RelationshipPattern]:
        """Patterns for monetary relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?P<amount>\$[\d,]+(?:\.\d{2})?|\d+\s+dollars?)\s+(?:was\s+)?(?:awarded|granted)\s+to\s+(?P<recipient>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="awarded_to",
                subject_types=["MONEY", "DAMAGES", "JUDGMENT"],
                object_types=["PARTY", "PLAINTIFF", "PERSON", "CORPORATION"],
                confidence=0.9,
                examples=["$100,000 was awarded to the plaintiff", "Damages granted to John Doe"]
            ),
            RelationshipPattern(
                pattern=r'(?P<payer>[\w\s,\.]+)\s+(?:ordered|required|directed)\s+to\s+pay\s+(?P<amount>\$[\d,]+(?:\.\d{2})?|\d+\s+dollars?)',
                compiled_regex=None,
                relationship_type="must_pay",
                subject_types=["PARTY", "DEFENDANT", "PERSON", "CORPORATION"],
                object_types=["MONEY", "DAMAGES", "FINE"],
                confidence=0.85,
                examples=["Defendant ordered to pay $50,000", "ABC Corp required to pay damages"]
            ),
            RelationshipPattern(
                pattern=r'(?:fine|penalty|sanction)\s+of\s+(?P<amount>\$[\d,]+(?:\.\d{2})?)\s+(?:imposed|levied|assessed)\s+(?:on|against)\s+(?P<party>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="imposed_on",
                subject_types=["FINE", "PENALTY", "MONEY"],
                object_types=["PARTY", "DEFENDANT", "PERSON", "CORPORATION"],
                confidence=0.85,
                examples=["Fine of $10,000 imposed on the defendant"]
            ),
            RelationshipPattern(
                pattern=r'(?P<debtor>[\w\s,\.]+)\s+owes?\s+(?P<amount>\$[\d,]+(?:\.\d{2})?|\d+\s+dollars?)\s+to\s+(?P<creditor>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="owes_to",
                subject_types=["PARTY", "DEBTOR", "PERSON", "CORPORATION"],
                object_types=["PARTY", "CREDITOR", "PERSON", "CORPORATION"],
                confidence=0.85,
                examples=["Defendant owes $25,000 to plaintiff"]
            ),
            RelationshipPattern(
                pattern=r'(?P<party>[\w\s,\.]+)\s+(?:paid|remitted|transferred)\s+(?P<amount>\$[\d,]+(?:\.\d{2})?)\s+to\s+(?P<recipient>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="paid_to",
                subject_types=["PARTY", "PERSON", "CORPORATION"],
                object_types=["PARTY", "PERSON", "CORPORATION"],
                confidence=0.8,
                examples=["ABC Corp paid $100,000 to John Doe"]
            )
        ]
    
    def _get_temporal_patterns(self) -> List[RelationshipPattern]:
        """Patterns for temporal relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?P<document>[\w\s]+(?:complaint|motion|petition|brief|notice))\s+(?:was\s+)?filed\s+on\s+(?P<date>(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                compiled_regex=None,
                relationship_type="filed_on",
                subject_types=["PLEADING", "MOTION", "DOCUMENT"],
                object_types=["DATE"],
                confidence=0.95,
                examples=["Complaint filed on January 1, 2023", "Motion was filed on 01/01/2023"]
            ),
            RelationshipPattern(
                pattern=r'(?P<event>[\w\s]+(?:hearing|trial|conference|deposition))\s+(?:is\s+)?scheduled\s+(?:for|on)\s+(?P<date>(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                compiled_regex=None,
                relationship_type="scheduled_for",
                subject_types=["HEARING", "TRIAL", "PROCEEDING"],
                object_types=["DATE"],
                confidence=0.9,
                examples=["Trial scheduled for March 15, 2023", "Hearing is scheduled on 03/15/2023"]
            ),
            RelationshipPattern(
                pattern=r'(?P<event>[\w\s]+(?:incident|accident|breach|violation))\s+occurred\s+on\s+(?P<date>(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                compiled_regex=None,
                relationship_type="occurred_on",
                subject_types=["EVENT", "INCIDENT", "CRIME"],
                object_types=["DATE"],
                confidence=0.85,
                examples=["Incident occurred on June 1, 2022", "The breach occurred on 06/01/2022"]
            ),
            RelationshipPattern(
                pattern=r'(?P<document>[\w\s]+(?:contract|agreement|lease|license))\s+(?:expires?|expired|expiring)\s+(?:on)?\s+(?P<date>(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                compiled_regex=None,
                relationship_type="expires_on",
                subject_types=["CONTRACT", "AGREEMENT", "LICENSE"],
                object_types=["DATE"],
                confidence=0.85,
                examples=["Contract expires December 31, 2023", "License expiring on 12/31/2023"]
            ),
            RelationshipPattern(
                pattern=r'(?:effective|commencing|beginning)\s+(?:as\s+of|from|on)?\s+(?P<date>(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                compiled_regex=None,
                relationship_type="effective_from",
                subject_types=["CONTRACT", "ORDER", "STATUTE", "REGULATION"],
                object_types=["DATE"],
                confidence=0.8,
                examples=["Effective as of January 1, 2023", "Commencing from 01/01/2023"]
            )
        ]
    
    def _get_court_patterns(self) -> List[RelationshipPattern]:
        """Patterns for court relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?P<case>[\w\s]+\s+v\.\s+[\w\s]+)\s+(?:in|before)\s+(?:the\s+)?(?P<court>[\w\s]+Court)',
                compiled_regex=None,
                relationship_type="venue_for",
                subject_types=["COURT"],
                object_types=["CASE"],
                confidence=0.85,
                examples=["Smith v. Jones in the District Court", "Case before the Supreme Court"]
            ),
            RelationshipPattern(
                pattern=r'(?P<lower_court>[\w\s]+Court)\s+(?:decision|judgment|ruling)\s+(?:reviewed|reversed|affirmed|modified)\s+by\s+(?P<higher_court>[\w\s]+Court)',
                compiled_regex=None,
                relationship_type="reviewing",
                subject_types=["COURT"],
                object_types=["COURT", "DECISION"],
                confidence=0.85,
                examples=["District Court decision reviewed by Appeals Court"]
            ),
            RelationshipPattern(
                pattern=r'(?:case|matter)\s+(?:transferred|removed)\s+from\s+(?P<from_court>[\w\s]+Court)\s+to\s+(?P<to_court>[\w\s]+Court)',
                compiled_regex=None,
                relationship_type="transferred_from",
                subject_types=["CASE"],
                object_types=["COURT"],
                confidence=0.85,
                examples=["Case transferred from State Court to Federal Court"]
            ),
            RelationshipPattern(
                pattern=r'(?:case|matter)\s+remanded\s+to\s+(?P<court>[\w\s]+Court)',
                compiled_regex=None,
                relationship_type="remanded_to",
                subject_types=["CASE", "MATTER"],
                object_types=["COURT"],
                confidence=0.9,
                examples=["Case remanded to District Court", "Matter remanded to lower court"]
            ),
            RelationshipPattern(
                pattern=r'(?P<court>[\w\s]+Court)\s+(?:has\s+)?jurisdiction\s+over\s+(?P<matter>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="has_jurisdiction",
                subject_types=["COURT"],
                object_types=["CASE", "MATTER", "PARTY"],
                confidence=0.8,
                examples=["Federal Court has jurisdiction over the matter"]
            )
        ]
    
    def _get_document_patterns(self) -> List[RelationshipPattern]:
        """Patterns for document relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?P<document>[\w\s]+(?:complaint|motion|brief|petition|notice|affidavit))\s+(?:filed|submitted)\s+by\s+(?P<filer>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="filed_by",
                subject_types=["DOCUMENT", "PLEADING", "MOTION"],
                object_types=["PARTY", "ATTORNEY", "LAW_FIRM"],
                confidence=0.9,
                examples=["Motion filed by the plaintiff", "Brief submitted by defendant's counsel"]
            ),
            RelationshipPattern(
                pattern=r'(?P<document>[\w\s]+(?:order|judgment|opinion|decision))\s+(?:authored|written|issued)\s+by\s+(?:Judge|Justice)?\s+(?P<author>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="authored_by",
                subject_types=["ORDER", "JUDGMENT", "OPINION"],
                object_types=["JUDGE", "COURT"],
                confidence=0.85,
                examples=["Opinion authored by Justice Smith", "Order issued by Judge Brown"]
            ),
            RelationshipPattern(
                pattern=r'(?P<document>[\w\s]+(?:contract|agreement|deed|will))\s+(?:signed|executed)\s+by\s+(?P<signatory>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="signed_by",
                subject_types=["CONTRACT", "AGREEMENT", "DOCUMENT"],
                object_types=["PARTY", "PERSON"],
                confidence=0.85,
                examples=["Contract signed by John Doe", "Agreement executed by both parties"]
            ),
            RelationshipPattern(
                pattern=r'(?P<document1>[\w\s]+)\s+(?:incorporates?|includes?|contains?|references?)\s+(?P<document2>[\w\s]+)',
                compiled_regex=None,
                relationship_type="contains",
                subject_types=["DOCUMENT"],
                object_types=["DOCUMENT", "EXHIBIT", "SCHEDULE"],
                confidence=0.75,
                examples=["Contract incorporates Exhibit A", "Brief references the complaint"]
            ),
            RelationshipPattern(
                pattern=r'(?P<affiant>[\w\s,\.]+)\s+(?:swears?|affirms?|attests?|declares?)\s+in\s+(?:the\s+)?(?P<document>affidavit|declaration|sworn\s+statement)',
                compiled_regex=None,
                relationship_type="swears_in",
                subject_types=["PERSON", "WITNESS"],
                object_types=["AFFIDAVIT", "DECLARATION"],
                confidence=0.85,
                examples=["John Doe swears in the affidavit", "Witness affirms in declaration"]
            )
        ]
    
    def _get_citation_patterns(self) -> List[RelationshipPattern]:
        """Patterns for citation relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?P<citing_case>[\w\s]+\s+v\.\s+[\w\s]+)[,\s]+(?:\d+\s+[\w\.]+\s+\d+)[,\s]+(?:cites?|citing|cited)\s+(?P<cited_case>[\w\s]+\s+v\.\s+[\w\s]+)',
                compiled_regex=None,
                relationship_type="cites",
                subject_types=["CASE", "OPINION"],
                object_types=["CASE", "CITATION"],
                confidence=0.95,
                examples=["Smith v. Jones, 123 F.3d 456, citing Brown v. Board"]
            ),
            RelationshipPattern(
                pattern=r'(?P<case1>[\w\s]+\s+v\.\s+[\w\s]+)\s+(?:distinguishes?|distinguished)\s+(?P<case2>[\w\s]+\s+v\.\s+[\w\s]+)',
                compiled_regex=None,
                relationship_type="distinguishes",
                subject_types=["CASE", "OPINION"],
                object_types=["CASE"],
                confidence=0.85,
                examples=["This case distinguishes Smith v. Jones"]
            ),
            RelationshipPattern(
                pattern=r'(?P<case1>[\w\s]+\s+v\.\s+[\w\s]+)\s+(?:overrules?|overruled|overruling)\s+(?P<case2>[\w\s]+\s+v\.\s+[\w\s]+)',
                compiled_regex=None,
                relationship_type="overrules",
                subject_types=["CASE", "OPINION"],
                object_types=["CASE"],
                confidence=0.9,
                examples=["Brown v. Board overruled Plessy v. Ferguson"]
            ),
            RelationshipPattern(
                pattern=r'(?P<case1>[\w\s]+\s+v\.\s+[\w\s]+)\s+(?:follows?|following|followed)\s+(?P<case2>[\w\s]+\s+v\.\s+[\w\s]+)',
                compiled_regex=None,
                relationship_type="follows",
                subject_types=["CASE", "OPINION"],
                object_types=["CASE", "PRECEDENT"],
                confidence=0.85,
                examples=["This court follows Smith v. Jones"]
            ),
            RelationshipPattern(
                pattern=r'(?P<principle>[\w\s]+(?:rule|doctrine|principle|test|standard))\s+(?:established|set\s+forth)\s+in\s+(?P<case>[\w\s]+\s+v\.\s+[\w\s]+)',
                compiled_regex=None,
                relationship_type="establishes",
                subject_types=["CASE"],
                object_types=["LEGAL_DOCTRINE", "LEGAL_STANDARD"],
                confidence=0.8,
                examples=["The Miranda rule established in Miranda v. Arizona"]
            ),
            RelationshipPattern(
                pattern=r'(?:pursuant\s+to|under|according\s+to)\s+(?P<statute>[\d]+\s+U\.S\.C\.\s+§\s+[\d]+|[\d]+\s+C\.F\.R\.\s+§\s+[\d\.]+)',
                compiled_regex=None,
                relationship_type="pursuant_to",
                subject_types=["ACTION", "CLAIM", "CHARGE"],
                object_types=["STATUTE", "REGULATION"],
                confidence=0.85,
                examples=["Pursuant to 42 U.S.C. § 1983", "Under 28 C.F.R. § 2.1"]
            )
        ]
    
    def _get_corporate_patterns(self) -> List[RelationshipPattern]:
        """Patterns for corporate relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?P<parent>[\w\s]+(?:Inc\.|Corp\.|Corporation|LLC|Ltd\.))\s+(?:owns?|acquired|controls?)\s+(?P<subsidiary>[\w\s]+(?:Inc\.|Corp\.|Corporation|LLC|Ltd\.))',
                compiled_regex=None,
                relationship_type="owns",
                subject_types=["CORPORATION"],
                object_types=["CORPORATION", "SUBSIDIARY"],
                confidence=0.85,
                examples=["ABC Corp. owns XYZ Inc.", "Parent Company acquired Subsidiary LLC"]
            ),
            RelationshipPattern(
                pattern=r'(?P<subsidiary>[\w\s]+(?:Inc\.|Corp\.|LLC))\s+(?:is\s+)?(?:a\s+)?(?:subsidiary|division|unit)\s+of\s+(?P<parent>[\w\s]+(?:Inc\.|Corp\.|LLC))',
                compiled_regex=None,
                relationship_type="subsidiary_of",
                subject_types=["CORPORATION", "SUBSIDIARY"],
                object_types=["CORPORATION"],
                confidence=0.85,
                examples=["XYZ Inc. is a subsidiary of ABC Corp."]
            ),
            RelationshipPattern(
                pattern=r'(?P<company1>[\w\s]+(?:Inc\.|Corp\.|LLC))\s+(?:merged?|merging|consolidat(?:ed|ing))\s+with\s+(?P<company2>[\w\s]+(?:Inc\.|Corp\.|LLC))',
                compiled_regex=None,
                relationship_type="merged_with",
                subject_types=["CORPORATION"],
                object_types=["CORPORATION"],
                confidence=0.85,
                bidirectional=True,
                examples=["ABC Corp. merged with XYZ Inc."]
            ),
            RelationshipPattern(
                pattern=r'(?P<employer>[\w\s]+(?:Inc\.|Corp\.|Corporation|LLC|Company))\s+(?:employs?|employed|hired)\s+(?P<employee>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="employs",
                subject_types=["CORPORATION", "EMPLOYER"],
                object_types=["EMPLOYEE", "PERSON"],
                confidence=0.8,
                examples=["ABC Corporation employs John Doe"]
            ),
            RelationshipPattern(
                pattern=r'(?P<officer>[\w\s,\.]+)\s+(?:is\s+)?(?:CEO|CFO|President|Vice\s+President|Director|Officer)\s+of\s+(?P<company>[\w\s]+(?:Inc\.|Corp\.|LLC))',
                compiled_regex=None,
                relationship_type="officer_of",
                subject_types=["PERSON", "BOARD_MEMBER"],
                object_types=["CORPORATION"],
                confidence=0.85,
                examples=["John Smith is CEO of ABC Corp."]
            )
        ]
    
    def _get_criminal_patterns(self) -> List[RelationshipPattern]:
        """Patterns for criminal law relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?P<defendant>[\w\s,\.]+)\s+(?:is\s+)?charged\s+with\s+(?P<crime>[\w\s]+(?:murder|assault|theft|fraud|robbery|burglary|conspiracy))',
                compiled_regex=None,
                relationship_type="charged_with",
                subject_types=["DEFENDANT", "PERSON"],
                object_types=["CRIME", "CHARGE"],
                confidence=0.9,
                examples=["John Doe charged with first-degree murder"]
            ),
            RelationshipPattern(
                pattern=r'(?P<defendant>[\w\s,\.]+)\s+(?:was\s+)?convicted\s+of\s+(?P<crime>[\w\s]+)',
                compiled_regex=None,
                relationship_type="convicted_of",
                subject_types=["DEFENDANT", "PERSON"],
                object_types=["CRIME"],
                confidence=0.95,
                examples=["Defendant was convicted of fraud"]
            ),
            RelationshipPattern(
                pattern=r'(?P<defendant>[\w\s,\.]+)\s+sentenced\s+to\s+(?P<sentence>[\w\s]+(?:years?|months?|days?|life|probation|community\s+service))',
                compiled_regex=None,
                relationship_type="sentenced_to",
                subject_types=["DEFENDANT", "PERSON"],
                object_types=["SENTENCE"],
                confidence=0.9,
                examples=["John Doe sentenced to 10 years", "Defendant sentenced to life imprisonment"]
            ),
            RelationshipPattern(
                pattern=r'(?P<case>[\w\s]+)\s+prosecuted\s+by\s+(?P<prosecutor>[\w\s,\.]+(?:District\s+Attorney|D\.A\.|ADA|U\.S\.\s+Attorney|Prosecutor))',
                compiled_regex=None,
                relationship_type="prosecuted_by",
                subject_types=["CASE", "DEFENDANT"],
                object_types=["PROSECUTOR", "ATTORNEY"],
                confidence=0.85,
                examples=["Case prosecuted by District Attorney Smith"]
            ),
            RelationshipPattern(
                pattern=r'(?P<defendant>[\w\s,\.]+)\s+(?:plead(?:ed|s)?|pled)\s+(?P<plea>guilty|not\s+guilty|no\s+contest|nolo\s+contendere)',
                compiled_regex=None,
                relationship_type="entered_plea",
                subject_types=["DEFENDANT", "PERSON"],
                object_types=["PLEA"],
                confidence=0.9,
                examples=["Defendant pleaded guilty", "John Doe pled not guilty"]
            )
        ]
    
    def _get_property_patterns(self) -> List[RelationshipPattern]:
        """Patterns for property relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?P<owner>[\w\s,\.]+)\s+(?:owns?|owned|is\s+the\s+owner\s+of)\s+(?P<property>[\w\s]+(?:property|premises|parcel|lot|real\s+estate))',
                compiled_regex=None,
                relationship_type="owner_of",
                subject_types=["PERSON", "CORPORATION", "PROPERTY_OWNER"],
                object_types=["PROPERTY"],
                confidence=0.85,
                examples=["John Doe owns the property", "ABC Corp. is the owner of the premises"]
            ),
            RelationshipPattern(
                pattern=r'(?P<tenant>[\w\s,\.]+)\s+(?:leases?|rents?|is\s+tenant\s+of)\s+(?P<property>[\w\s]+)\s+from\s+(?P<landlord>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="tenant_of",
                subject_types=["PERSON", "CORPORATION"],
                object_types=["PROPERTY", "PROPERTY_OWNER"],
                confidence=0.8,
                examples=["John Doe leases the property from ABC Corp."]
            ),
            RelationshipPattern(
                pattern=r'(?P<lienholder>[\w\s,\.]+)\s+(?:holds?\s+a?\s+lien|has\s+a?\s+lien)\s+(?:on|against)\s+(?P<property>[\w\s]+(?:property|premises|asset))',
                compiled_regex=None,
                relationship_type="lienholder_of",
                subject_types=["CREDITOR", "BANK", "PERSON", "CORPORATION"],
                object_types=["PROPERTY"],
                confidence=0.85,
                examples=["Bank holds a lien on the property"]
            ),
            RelationshipPattern(
                pattern=r'(?P<holder>[\w\s,\.]+)\s+(?:has|holds?|granted)\s+(?:an?\s+)?easement\s+(?:on|over|across)\s+(?P<property>[\w\s]+)',
                compiled_regex=None,
                relationship_type="easement_on",
                subject_types=["PERSON", "CORPORATION", "UTILITY"],
                object_types=["PROPERTY"],
                confidence=0.8,
                examples=["Utility company has easement on the property"]
            ),
            RelationshipPattern(
                pattern=r'(?P<property>[\w\s]+(?:property|land|parcel))\s+(?:conveyed|transferred|deeded)\s+(?:to|from)\s+(?P<party>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="conveyed_to",
                subject_types=["PROPERTY"],
                object_types=["PERSON", "CORPORATION"],
                confidence=0.85,
                examples=["Property conveyed to John Doe", "Land transferred from ABC Corp."]
            )
        ]
    
    def _get_contractual_patterns(self) -> List[RelationshipPattern]:
        """Patterns for contractual relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?P<party1>[\w\s,\.]+)\s+(?:is\s+)?(?:party|signatory)\s+to\s+(?P<contract>[\w\s]+(?:agreement|contract|covenant|compact))',
                compiled_regex=None,
                relationship_type="party_to",
                subject_types=["PERSON", "CORPORATION", "PARTY"],
                object_types=["CONTRACT", "AGREEMENT"],
                confidence=0.85,
                examples=["John Doe is party to the agreement", "ABC Corp. signatory to contract"]
            ),
            RelationshipPattern(
                pattern=r'(?P<contract>[\w\s]+(?:agreement|contract))\s+between\s+(?P<party1>[\w\s,\.]+)\s+and\s+(?P<party2>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="between_parties",
                subject_types=["CONTRACT", "AGREEMENT"],
                object_types=["PARTY", "PERSON", "CORPORATION"],
                confidence=0.9,
                examples=["Agreement between John Doe and Jane Smith"]
            ),
            RelationshipPattern(
                pattern=r'(?P<party>[\w\s,\.]+)\s+(?:breached|violated|defaulted\s+on)\s+(?P<contract>[\w\s]+(?:agreement|contract|covenant))',
                compiled_regex=None,
                relationship_type="breached",
                subject_types=["PARTY", "PERSON", "CORPORATION"],
                object_types=["CONTRACT", "AGREEMENT"],
                confidence=0.85,
                examples=["Defendant breached the contract", "ABC Corp. violated the agreement"]
            ),
            RelationshipPattern(
                pattern=r'(?P<contract>[\w\s]+(?:agreement|contract))\s+(?:governs?|regulates?|controls?)\s+(?P<matter>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="governs",
                subject_types=["CONTRACT", "AGREEMENT"],
                object_types=["TRANSACTION", "RELATIONSHIP", "MATTER"],
                confidence=0.75,
                examples=["The agreement governs the relationship", "Contract controls the transaction"]
            ),
            RelationshipPattern(
                pattern=r'(?P<party>[\w\s,\.]+)\s+(?:warrants?|guarantees?|represents?)\s+(?:that\s+)?(?P<warranty>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="warrants",
                subject_types=["PARTY", "PERSON", "CORPORATION"],
                object_types=["WARRANTY", "REPRESENTATION"],
                confidence=0.75,
                examples=["Seller warrants the goods are merchantable", "ABC Corp. represents that"]
            )
        ]
    
    def _get_procedural_patterns(self) -> List[RelationshipPattern]:
        """Patterns for procedural relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?P<party>[\w\s,\.]+)\s+(?:filed|submitted|served)\s+(?P<motion>[\w\s]+motion)\s+(?:to|for)\s+(?P<relief>[\w\s]+)',
                compiled_regex=None,
                relationship_type="filed_motion",
                subject_types=["PARTY", "ATTORNEY"],
                object_types=["MOTION"],
                confidence=0.85,
                examples=["Plaintiff filed motion to dismiss", "Defendant submitted motion for summary judgment"]
            ),
            RelationshipPattern(
                pattern=r'(?P<party>[\w\s,\.]+)\s+(?:objects?|objected)\s+to\s+(?P<matter>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="objects_to",
                subject_types=["PARTY", "ATTORNEY"],
                object_types=["EVIDENCE", "MOTION", "TESTIMONY"],
                confidence=0.8,
                examples=["Defendant objects to the evidence", "Plaintiff objected to testimony"]
            ),
            RelationshipPattern(
                pattern=r'(?P<witness>[\w\s,\.]+)\s+(?:testified|testifying|gave\s+testimony)\s+(?:for|on\s+behalf\s+of)\s+(?P<party>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="testified_for",
                subject_types=["WITNESS", "EXPERT", "PERSON"],
                object_types=["PARTY", "PLAINTIFF", "DEFENDANT"],
                confidence=0.85,
                examples=["Dr. Smith testified for the plaintiff", "Witness gave testimony on behalf of defendant"]
            ),
            RelationshipPattern(
                pattern=r'(?P<party>[\w\s,\.]+)\s+(?:seeks?|seeking|sought)\s+(?P<relief>[\w\s]+(?:damages|injunction|relief|remedy))',
                compiled_regex=None,
                relationship_type="seeks",
                subject_types=["PARTY", "PLAINTIFF"],
                object_types=["DAMAGES", "REMEDY", "RELIEF"],
                confidence=0.8,
                examples=["Plaintiff seeks damages", "Defendant seeking injunctive relief"]
            ),
            RelationshipPattern(
                pattern=r'(?P<court>[\w\s]+Court)\s+(?:granted|denied|sustained|overruled)\s+(?P<motion>[\w\s]+motion)',
                compiled_regex=None,
                relationship_type="ruled_on_motion",
                subject_types=["COURT", "JUDGE"],
                object_types=["MOTION"],
                confidence=0.9,
                examples=["Court granted motion to dismiss", "Judge denied motion for summary judgment"]
            )
        ]
    
    def _get_jurisdictional_patterns(self) -> List[RelationshipPattern]:
        """Patterns for jurisdictional relationships"""
        return [
            RelationshipPattern(
                pattern=r'(?P<court>[\w\s]+Court)\s+(?:has|lacks?|exercises?)\s+(?P<jurisdiction>[\w\s]*jurisdiction)\s+over\s+(?P<matter>[\w\s,\.]+)',
                compiled_regex=None,
                relationship_type="has_jurisdiction_over",
                subject_types=["COURT"],
                object_types=["CASE", "PARTY", "MATTER"],
                confidence=0.85,
                examples=["Federal Court has jurisdiction over the matter", "State Court lacks jurisdiction over defendant"]
            ),
            RelationshipPattern(
                pattern=r'(?P<law>[\w\s]+(?:law|statute|code))\s+(?:of|from)\s+(?P<jurisdiction>[\w\s]+(?:State|Commonwealth|District))',
                compiled_regex=None,
                relationship_type="law_of",
                subject_types=["STATUTE", "LAW"],
                object_types=["JURISDICTION", "STATE"],
                confidence=0.8,
                examples=["Laws of the State of New York", "California Penal Code"]
            ),
            RelationshipPattern(
                pattern=r'(?:venue\s+)?(?:proper|improper|lies?)\s+in\s+(?P<court>[\w\s]+(?:County|District|Division))',
                compiled_regex=None,
                relationship_type="venue_in",
                subject_types=["CASE", "MATTER"],
                object_types=["COURT", "JURISDICTION"],
                confidence=0.8,
                examples=["Venue proper in Southern District", "Venue lies in Kings County"]
            ),
            RelationshipPattern(
                pattern=r'(?P<case>[\w\s]+)\s+(?:removed|transferred)\s+to\s+(?P<court>[\w\s]+Court)\s+(?:pursuant\s+to|under)\s+(?P<statute>[\d]+\s+U\.S\.C\.\s+§\s+[\d]+)',
                compiled_regex=None,
                relationship_type="removed_pursuant_to",
                subject_types=["CASE"],
                object_types=["COURT", "STATUTE"],
                confidence=0.85,
                examples=["Case removed to Federal Court pursuant to 28 U.S.C. § 1441"]
            ),
            RelationshipPattern(
                pattern=r'(?P<party>[\w\s,\.]+)\s+(?:is\s+)?(?:domiciled|resides?|resident)\s+in\s+(?P<jurisdiction>[\w\s]+(?:State|County|District))',
                compiled_regex=None,
                relationship_type="domiciled_in",
                subject_types=["PARTY", "PERSON", "CORPORATION"],
                object_types=["JURISDICTION", "STATE"],
                confidence=0.8,
                examples=["Defendant is domiciled in New York State", "Plaintiff resides in Los Angeles County"]
            )
        ]
    
    def get_all_patterns(self) -> List[RelationshipPattern]:
        """Get all relationship patterns as a flat list"""
        all_patterns = []
        for category_patterns in self.patterns.values():
            all_patterns.extend(category_patterns)
        return all_patterns
    
    def get_patterns_by_category(self, category: str) -> List[RelationshipPattern]:
        """Get patterns for a specific category"""
        return self.patterns.get(category, [])
    
    def get_patterns_for_entity_types(self, 
                                     subject_type: str, 
                                     object_type: str) -> List[RelationshipPattern]:
        """Get patterns that match specific entity types"""
        matching_patterns = []
        for pattern in self.get_all_patterns():
            if (subject_type in pattern.subject_types and 
                object_type in pattern.object_types):
                matching_patterns.append(pattern)
        return matching_patterns
    
    def get_bidirectional_patterns(self) -> List[RelationshipPattern]:
        """Get all bidirectional relationship patterns"""
        return [p for p in self.get_all_patterns() if p.bidirectional]
    
    def get_high_confidence_patterns(self, threshold: float = 0.85) -> List[RelationshipPattern]:
        """Get patterns with confidence above threshold"""
        return [p for p in self.get_all_patterns() if p.confidence >= threshold]