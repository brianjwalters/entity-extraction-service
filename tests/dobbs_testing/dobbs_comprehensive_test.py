#!/usr/bin/env python3
"""
Comprehensive test framework for Dobbs.pdf entity extraction.
Tests all extraction modes, strategies, and tracks entity type coverage.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import os
import aiohttp
from aiohttp import ClientTimeout
import traceback
from collections import defaultdict, Counter

# Add parent directory to path for imports

# Note: These clients don't exist in this service - commenting out broken imports
# from src.clients.document_upload_client import DocumentUploadClient
from src.client.entity_extraction_client import EntityExtractionClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'/srv/luris/be/entity-extraction-service/tests/dobbs_testing/test_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# All 272 entity types from the system
ALL_ENTITY_TYPES = [
    # Courts and Judicial
    'COURT', 'JUDGE', 'MAGISTRATE', 'ARBITRATOR', 'TRIBUNAL', 'JUDICIAL_OFFICER',
    'SPECIAL_MASTER', 'BANKRUPTCY_JUDGE', 'ADMINISTRATIVE_LAW_JUDGE',
    
    # Legal Professionals
    'ATTORNEY', 'LAW_FIRM', 'PROSECUTOR', 'PUBLIC_DEFENDER', 'LEGAL_AID',
    'COUNSEL', 'SOLICITOR', 'BARRISTER', 'ADVOCATE', 'LEGAL_REPRESENTATIVE',
    'PARALEGAL', 'LEGAL_ASSISTANT', 'LAW_CLERK', 'COURT_REPORTER',
    
    # Parties
    'PARTY', 'PLAINTIFF', 'DEFENDANT', 'APPELLANT', 'APPELLEE', 'RESPONDENT',
    'PETITIONER', 'CLAIMANT', 'COUNTERCLAIMANT', 'THIRD_PARTY', 'INTERVENOR',
    'AMICUS_CURIAE', 'CLASS_REPRESENTATIVE', 'EXPERT_WITNESS', 'WITNESS',
    
    # Legal Concepts
    'LEGAL_DOCTRINE', 'PROCEDURAL_TERM', 'LEGAL_STANDARD', 'LEGAL_ISSUE',
    'LEGAL_PRINCIPLE', 'LEGAL_TEST', 'BURDEN_OF_PROOF', 'PRECEDENT',
    'HOLDING', 'RULING', 'RATIO_DECIDENDI', 'OBITER_DICTUM', 'DISSENT',
    'CONCURRENCE', 'LEGAL_THEORY', 'CAUSE_OF_ACTION', 'DEFENSE', 'REMEDY',
    
    # Citations
    'CASE_CITATION', 'STATUTE_CITATION', 'REGULATION_CITATION', 
    'CONSTITUTIONAL_CITATION', 'RULE_CITATION', 'TREATISE_CITATION',
    'LAW_REVIEW_CITATION', 'RESTATEMENT_CITATION', 'UNIFORM_CODE_CITATION',
    'FEDERAL_REGISTER_CITATION', 'CODE_OF_FEDERAL_REGULATIONS_CITATION',
    'EXECUTIVE_ORDER_CITATION', 'ADMINISTRATIVE_DECISION_CITATION',
    
    # Documents
    'CONTRACT', 'MOTION', 'BRIEF', 'OPINION', 'ORDER', 'JUDGMENT',
    'COMPLAINT', 'ANSWER', 'PETITION', 'MEMORANDUM', 'AFFIDAVIT',
    'DECLARATION', 'DEPOSITION', 'INTERROGATORY', 'REQUEST_FOR_ADMISSION',
    'REQUEST_FOR_PRODUCTION', 'SUBPOENA', 'SUMMONS', 'WARRANT', 'WRIT',
    'PLEADING', 'FILING', 'TRANSCRIPT', 'EXHIBIT', 'EVIDENCE',
    
    # Financial
    'MONETARY_AMOUNT', 'DAMAGES', 'SETTLEMENT', 'LEGAL_FEES', 'COSTS',
    'FINE', 'PENALTY', 'RESTITUTION', 'COMPENSATION', 'AWARD',
    'BAIL', 'BOND', 'RETAINER', 'CONTINGENCY_FEE', 'HOURLY_RATE',
    
    # Temporal
    'DATE', 'DEADLINE', 'FILING_DATE', 'HEARING_DATE', 'TRIAL_DATE',
    'STATUTE_OF_LIMITATIONS', 'TIME_PERIOD', 'TERM', 'EFFECTIVE_DATE',
    'EXPIRATION_DATE', 'SERVICE_DATE', 'NOTICE_PERIOD',
    
    # Jurisdictional
    'JURISDICTION', 'VENUE', 'FORUM', 'DISTRICT', 'CIRCUIT', 'DIVISION',
    'FEDERAL_JURISDICTION', 'STATE_JURISDICTION', 'SUBJECT_MATTER_JURISDICTION',
    'PERSONAL_JURISDICTION', 'TERRITORIAL_JURISDICTION', 'APPELLATE_JURISDICTION',
    
    # Procedural
    'DOCKET_NUMBER', 'CASE_NUMBER', 'CIVIL_ACTION_NUMBER', 'CRIMINAL_NUMBER',
    'BANKRUPTCY_NUMBER', 'ADMINISTRATIVE_NUMBER', 'APPEAL_NUMBER',
    'MOTION_TYPE', 'HEARING_TYPE', 'PROCEEDING_TYPE', 'TRIAL_TYPE',
    'DISCOVERY_METHOD', 'SERVICE_METHOD', 'NOTICE_TYPE',
    
    # Evidence
    'EVIDENCE_TYPE', 'PHYSICAL_EVIDENCE', 'DOCUMENTARY_EVIDENCE',
    'TESTIMONIAL_EVIDENCE', 'DEMONSTRATIVE_EVIDENCE', 'DIGITAL_EVIDENCE',
    'FORENSIC_EVIDENCE', 'CIRCUMSTANTIAL_EVIDENCE', 'DIRECT_EVIDENCE',
    'HEARSAY', 'ADMISSION', 'CONFESSION', 'STATEMENT',
    
    # Criminal Law
    'CRIME', 'FELONY', 'MISDEMEANOR', 'INFRACTION', 'CHARGE', 'COUNT',
    'INDICTMENT', 'ARRAIGNMENT', 'PLEA', 'PLEA_BARGAIN', 'VERDICT',
    'SENTENCE', 'PROBATION', 'PAROLE', 'CONVICTION', 'ACQUITTAL',
    
    # Civil Law
    'TORT', 'NEGLIGENCE', 'LIABILITY', 'BREACH', 'BREACH_OF_CONTRACT',
    'BREACH_OF_DUTY', 'BREACH_OF_WARRANTY', 'FRAUD', 'MISREPRESENTATION',
    'DEFAMATION', 'LIBEL', 'SLANDER', 'TRESPASS', 'NUISANCE',
    'CONVERSION', 'BATTERY', 'ASSAULT', 'FALSE_IMPRISONMENT',
    
    # Corporate/Business
    'CORPORATION', 'LLC', 'PARTNERSHIP', 'SOLE_PROPRIETORSHIP',
    'BUSINESS_ENTITY', 'SHAREHOLDER', 'DIRECTOR', 'OFFICER',
    'MERGER', 'ACQUISITION', 'JOINT_VENTURE', 'FRANCHISE',
    'TRADEMARK', 'PATENT', 'COPYRIGHT', 'TRADE_SECRET',
    
    # Real Estate
    'PROPERTY', 'REAL_PROPERTY', 'PERSONAL_PROPERTY', 'DEED', 'TITLE',
    'LEASE', 'EASEMENT', 'LIEN', 'MORTGAGE', 'FORECLOSURE',
    'LANDLORD', 'TENANT', 'LESSOR', 'LESSEE', 'ZONING',
    
    # Family Law
    'DIVORCE', 'CUSTODY', 'CHILD_SUPPORT', 'ALIMONY', 'SPOUSAL_SUPPORT',
    'VISITATION', 'ADOPTION', 'GUARDIANSHIP', 'CONSERVATORSHIP',
    'PRENUPTIAL_AGREEMENT', 'MARITAL_PROPERTY', 'SEPARATE_PROPERTY',
    
    # Constitutional
    'CONSTITUTIONAL_RIGHT', 'FUNDAMENTAL_RIGHT', 'DUE_PROCESS',
    'EQUAL_PROTECTION', 'FIRST_AMENDMENT', 'FOURTH_AMENDMENT',
    'FIFTH_AMENDMENT', 'SIXTH_AMENDMENT', 'FOURTEENTH_AMENDMENT',
    
    # International
    'TREATY', 'INTERNATIONAL_AGREEMENT', 'CONVENTION', 'PROTOCOL',
    'INTERNATIONAL_COURT', 'INTERNATIONAL_TRIBUNAL', 'EXTRADITION',
    
    # Regulatory
    'REGULATION', 'ADMINISTRATIVE_RULE', 'AGENCY', 'COMMISSION',
    'REGULATORY_BODY', 'ADMINISTRATIVE_AGENCY', 'REGULATORY_VIOLATION',
    'COMPLIANCE', 'ENFORCEMENT_ACTION', 'ADMINISTRATIVE_HEARING',
    
    # Alternative Dispute Resolution
    'ARBITRATION', 'MEDIATION', 'NEGOTIATION', 'SETTLEMENT_CONFERENCE',
    'ALTERNATIVE_DISPUTE_RESOLUTION', 'ARBITRATION_AWARD', 'MEDIATOR',
    
    # Legal Status
    'LEGAL_STATUS', 'STANDING', 'CAPACITY', 'COMPETENCY', 'IMMUNITY',
    'PRIVILEGE', 'RES_JUDICATA', 'COLLATERAL_ESTOPPEL', 'STATUTE_OF_FRAUDS',
    
    # Miscellaneous
    'LEGAL_ENTITY', 'GOVERNMENT_ENTITY', 'AGENCY_ENTITY', 'TRUST',
    'ESTATE', 'BENEFICIARY', 'TRUSTEE', 'EXECUTOR', 'ADMINISTRATOR',
    'POWER_OF_ATTORNEY', 'GUARDIAN_AD_LITEM', 'SPECIAL_APPEARANCE'
]

class DobbsTestFramework:
    """Comprehensive test framework for Dobbs.pdf entity extraction."""
    
    def __init__(self):
        self.upload_client = DocumentUploadClient(base_url="http://localhost:8008")
        self.extraction_client = EntityExtractionClient(base_url="http://localhost:8007")
        self.dobbs_path = "/srv/luris/be/tests/docs/dobbs.pdf"
        self.results_dir = Path("/srv/luris/be/entity-extraction-service/tests/dobbs_testing/results")
        self.results_dir.mkdir(exist_ok=True)
        self.timeout = ClientTimeout(total=300, connect=10, sock_read=300)
        
    async def upload_document(self) -> Tuple[str, str]:
        """Upload Dobbs.pdf and return document_id and markdown_content."""
        logger.info("Uploading Dobbs.pdf...")
        try:
            result = await self.upload_client.upload_document(
                file_path=self.dobbs_path,
                client_id="test_dobbs_extraction",
                case_id=f"dobbs_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            if result and 'document_id' in result and 'markdown_content' in result:
                logger.info(f"Document uploaded successfully. ID: {result['document_id']}")
                logger.info(f"Markdown content length: {len(result['markdown_content'])} characters")
                return result['document_id'], result['markdown_content']
            else:
                logger.error(f"Upload failed or returned incomplete data: {result}")
                raise ValueError("Document upload failed")
                
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            raise
    
    async def test_extraction_mode(
        self,
        document_id: str,
        content: str,
        mode: str,
        strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """Test a specific extraction mode and strategy."""
        logger.info(f"Testing mode: {mode}, strategy: {strategy or 'default'}")
        
        start_time = time.time()
        try:
            # Prepare extraction request
            extract_params = {
                "document_id": document_id,
                "content": content[:50000] if mode == "ai_enhanced" else content,  # Limit for AI
                "extraction_mode": mode,
                "confidence_threshold": 0.6
            }
            
            if strategy and mode in ["ai_enhanced", "hybrid"]:
                extract_params["prompt_strategy"] = strategy
            
            # Perform extraction with timeout
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.extraction_client.base_url}/extract",
                    json=extract_params
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"Extraction failed: {error_text}")
                        result = {"error": error_text, "status": response.status}
            
            elapsed_time = time.time() - start_time
            
            # Analyze results
            if "entities" in result:
                entities = result.get("entities", [])
                citations = result.get("citations", [])
                
                # Count entity types found
                entity_type_counts = Counter(e.get("entity_type") for e in entities)
                citation_type_counts = Counter(c.get("citation_type") for c in citations)
                
                # Calculate coverage
                unique_types_found = set(entity_type_counts.keys())
                coverage_percentage = (len(unique_types_found) / len(ALL_ENTITY_TYPES)) * 100
                
                # Get confidence statistics
                confidences = [e.get("confidence", 0) for e in entities if "confidence" in e]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                analysis = {
                    "mode": mode,
                    "strategy": strategy or "default",
                    "success": True,
                    "elapsed_time": elapsed_time,
                    "total_entities": len(entities),
                    "total_citations": len(citations),
                    "unique_entity_types": len(unique_types_found),
                    "entity_type_coverage": coverage_percentage,
                    "entity_type_counts": dict(entity_type_counts),
                    "citation_type_counts": dict(citation_type_counts),
                    "types_found": sorted(list(unique_types_found)),
                    "types_missing": sorted(list(set(ALL_ENTITY_TYPES) - unique_types_found)),
                    "average_confidence": avg_confidence,
                    "confidence_distribution": {
                        "min": min(confidences) if confidences else 0,
                        "max": max(confidences) if confidences else 0,
                        "count_with_confidence": len(confidences)
                    },
                    "sample_entities": entities[:10] if entities else [],
                    "processing_time_ms": result.get("processing_time_ms", elapsed_time * 1000)
                }
            else:
                analysis = {
                    "mode": mode,
                    "strategy": strategy or "default",
                    "success": False,
                    "elapsed_time": elapsed_time,
                    "error": result.get("error", "Unknown error"),
                    "status": result.get("status", 500)
                }
            
            return analysis
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout for mode: {mode}, strategy: {strategy}")
            return {
                "mode": mode,
                "strategy": strategy or "default",
                "success": False,
                "error": "Timeout",
                "elapsed_time": time.time() - start_time
            }
        except Exception as e:
            logger.error(f"Error testing mode {mode}: {e}")
            logger.error(traceback.format_exc())
            return {
                "mode": mode,
                "strategy": strategy or "default",
                "success": False,
                "error": str(e),
                "elapsed_time": time.time() - start_time
            }
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive tests on all modes and strategies."""
        logger.info("Starting comprehensive Dobbs.pdf extraction test")
        
        test_results = {
            "test_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "document": "dobbs.pdf",
            "started_at": datetime.now().isoformat(),
            "modes_tested": [],
            "aggregate_metrics": {},
            "entity_type_coverage_summary": {}
        }
        
        try:
            # Upload document
            document_id, markdown_content = await self.upload_document()
            test_results["document_id"] = document_id
            test_results["content_length"] = len(markdown_content)
            
            # Define test configurations
            test_configs = [
                ("regex", None),
                ("ai_enhanced", "unified"),
                ("ai_enhanced", "multipass"),
                ("ai_enhanced", "ai_enhanced"),
                ("hybrid", "unified"),
                ("hybrid", "multipass"),
            ]
            
            # Run tests
            all_results = []
            all_entity_types_found = set()
            
            for mode, strategy in test_configs:
                logger.info(f"\n{'='*60}")
                logger.info(f"Testing: {mode} / {strategy or 'default'}")
                logger.info(f"{'='*60}")
                
                result = await self.test_extraction_mode(
                    document_id, markdown_content, mode, strategy
                )
                
                all_results.append(result)
                
                if result.get("success"):
                    all_entity_types_found.update(result.get("types_found", []))
                    
                    # Log summary
                    logger.info(f"✓ Success: {result['total_entities']} entities, "
                              f"{result['unique_entity_types']} types "
                              f"({result['entity_type_coverage']:.1f}% coverage)")
                else:
                    logger.error(f"✗ Failed: {result.get('error')}")
                
                # Small delay between tests
                await asyncio.sleep(2)
            
            # Calculate aggregate metrics
            successful_tests = [r for r in all_results if r.get("success")]
            
            test_results["modes_tested"] = all_results
            test_results["aggregate_metrics"] = {
                "total_tests": len(all_results),
                "successful_tests": len(successful_tests),
                "failed_tests": len(all_results) - len(successful_tests),
                "total_unique_entity_types": len(all_entity_types_found),
                "overall_coverage": (len(all_entity_types_found) / len(ALL_ENTITY_TYPES)) * 100,
                "all_types_found": sorted(list(all_entity_types_found)),
                "all_types_missing": sorted(list(set(ALL_ENTITY_TYPES) - all_entity_types_found)),
                "average_extraction_time": sum(r["elapsed_time"] for r in successful_tests) / len(successful_tests) if successful_tests else 0,
                "best_coverage_mode": max(successful_tests, key=lambda x: x.get("entity_type_coverage", 0)) if successful_tests else None,
                "most_entities_mode": max(successful_tests, key=lambda x: x.get("total_entities", 0)) if successful_tests else None
            }
            
            # Create entity type coverage matrix
            coverage_matrix = {}
            for entity_type in ALL_ENTITY_TYPES:
                coverage_matrix[entity_type] = {
                    "found_by": [],
                    "total_count": 0
                }
                
                for result in successful_tests:
                    if entity_type in result.get("entity_type_counts", {}):
                        mode_strategy = f"{result['mode']}_{result['strategy']}"
                        coverage_matrix[entity_type]["found_by"].append(mode_strategy)
                        coverage_matrix[entity_type]["total_count"] += result["entity_type_counts"][entity_type]
            
            test_results["entity_type_coverage_summary"] = coverage_matrix
            
        except Exception as e:
            logger.error(f"Test framework error: {e}")
            logger.error(traceback.format_exc())
            test_results["error"] = str(e)
        
        test_results["completed_at"] = datetime.now().isoformat()
        
        # Save results
        output_file = self.results_dir / f"dobbs_test_{test_results['test_id']}.json"
        with open(output_file, 'w') as f:
            json.dump(test_results, f, indent=2, default=str)
        
        logger.info(f"\nTest results saved to: {output_file}")
        
        # Print summary
        self.print_summary(test_results)
        
        return test_results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print a summary of test results."""
        print("\n" + "="*80)
        print("DOBBS.PDF EXTRACTION TEST SUMMARY")
        print("="*80)
        
        metrics = results.get("aggregate_metrics", {})
        
        print(f"\nTests Run: {metrics.get('total_tests', 0)}")
        print(f"Successful: {metrics.get('successful_tests', 0)}")
        print(f"Failed: {metrics.get('failed_tests', 0)}")
        
        print(f"\nEntity Type Coverage:")
        print(f"  Total Types Found: {metrics.get('total_unique_entity_types', 0)}/{len(ALL_ENTITY_TYPES)}")
        print(f"  Coverage: {metrics.get('overall_coverage', 0):.1f}%")
        
        if metrics.get("best_coverage_mode"):
            best = metrics["best_coverage_mode"]
            print(f"\nBest Coverage Mode:")
            print(f"  {best['mode']} / {best['strategy']}: {best['entity_type_coverage']:.1f}% coverage")
            print(f"  {best['total_entities']} entities found")
        
        if metrics.get("most_entities_mode"):
            most = metrics["most_entities_mode"]
            if most != metrics.get("best_coverage_mode"):
                print(f"\nMost Entities Found:")
                print(f"  {most['mode']} / {most['strategy']}: {most['total_entities']} entities")
        
        print(f"\nAverage Extraction Time: {metrics.get('average_extraction_time', 0):.2f} seconds")
        
        # Show top missing entity types
        missing = metrics.get("all_types_missing", [])
        if missing:
            print(f"\nTop Missing Entity Types ({len(missing)} total):")
            for entity_type in missing[:10]:
                print(f"  - {entity_type}")
        
        print("\n" + "="*80)

async def main():
    """Main entry point."""
    framework = DobbsTestFramework()
    await framework.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())