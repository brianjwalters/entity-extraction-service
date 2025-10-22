#!/usr/bin/env python3
"""
Test Template Execution Validation

Verifies that all templates execute correctly and return valid JSON
without explanatory text.
"""

import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime


class TemplateExecutionTester:
    """Test template execution and JSON output validation"""
    
    def __init__(self):
        self.base_url = "http://localhost:8007/api/v1"
        self.test_results = []
        self.sample_text = """
        In United States v. Smith, 123 F.3d 456 (9th Cir. 2023), the Ninth Circuit
        Court of Appeals ruled that Judge Sarah Johnson's decision to grant the 
        motion filed by attorney Michael Davis of Davis & Associates on behalf of
        plaintiff John Doe was proper under 28 U.S.C. § 1332. The defendant,
        ABC Corporation, represented by Jones Law Firm, argued that the $5,000,000
        damages award was excessive. The hearing was scheduled for March 15, 2024.
        """
        
    def test_single_template(self, strategy: str, prompt_type: str) -> Tuple[bool, Dict]:
        """Test a single template execution"""
        try:
            payload = {
                "content": self.sample_text,
                "document_id": f"test_template_{strategy}_{prompt_type}_{int(time.time())}",
                "extraction_mode": strategy,
                "confidence_threshold": 0.7,
                "prompt_type": prompt_type
            }
            
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/extract",
                json=payload,
                timeout=30
            )
            response_time = time.time() - start_time
            
            if response.status_code != 200:
                return False, {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text
                }
            
            result = response.json()
            
            # Validation checks
            checks = {
                "valid_json": True,
                "no_explanation": True,
                "has_entities": False,
                "has_citations": False,
                "response_time": response_time
            }
            
            # Check for entities
            if "entities" in result:
                checks["has_entities"] = len(result["entities"]) > 0
                
                # Check for explanatory text in entity values
                for entity in result["entities"]:
                    text = entity.get("entity_text", "")
                    if any(phrase in text.lower() for phrase in [
                        "i will", "i'll", "let me", "here is", "here are",
                        "this is", "the following", "below"
                    ]):
                        checks["no_explanation"] = False
                        break
            
            # Check for citations
            if "citations" in result:
                checks["has_citations"] = len(result["citations"]) > 0
            
            # Check raw response doesn't start with explanation
            if "raw_response" in result:
                raw = result["raw_response"]
                if raw and not raw.strip().startswith("{"):
                    checks["no_explanation"] = False
            
            return all([
                checks["valid_json"],
                checks["no_explanation"],
                checks["has_entities"] or checks["has_citations"]
            ]), checks
            
        except json.JSONDecodeError as e:
            return False, {"error": f"JSON decode error: {e}"}
        except Exception as e:
            return False, {"error": str(e)}
    
    def test_all_templates(self) -> Dict[str, Any]:
        """Test all template combinations"""
        strategies = ["multipass", "ai_enhanced", "unified"]
        
        # Template types for each strategy
        template_types = {
            "multipass": [
                "extraction_pass1", "extraction_pass2", "extraction_pass3",
                "relationship_pass", "validation_pass", "enrichment_pass"
            ],
            "ai_enhanced": [
                "base_extraction", "enhanced_extraction", "structured_extraction",
                "graph_aware_extraction", "legal_specialized_extraction"
            ],
            "unified": [
                "comprehensive", "focused", "detailed", "contextual", "relational"
            ]
        }
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "strategy_results": {}
        }
        
        for strategy in strategies:
            print(f"\nTesting {strategy} strategy templates...")
            strategy_results = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "templates": {}
            }
            
            for template in template_types.get(strategy, []):
                print(f"  Testing {template}...", end=" ")
                passed, details = self.test_single_template(strategy, template)
                
                strategy_results["total"] += 1
                results["total_tests"] += 1
                
                if passed:
                    strategy_results["passed"] += 1
                    results["passed"] += 1
                    print("✓ PASSED")
                else:
                    strategy_results["failed"] += 1
                    results["failed"] += 1
                    print(f"✗ FAILED: {details.get('error', 'Unknown')}")
                
                strategy_results["templates"][template] = {
                    "passed": passed,
                    "details": details
                }
            
            results["strategy_results"][strategy] = strategy_results
        
        return results
    
    def validate_json_structure(self, response: Dict) -> Dict[str, bool]:
        """Validate JSON structure matches expected format"""
        validations = {
            "has_entities_key": "entities" in response,
            "has_citations_key": "citations" in response,
            "entities_is_list": isinstance(response.get("entities"), list),
            "citations_is_list": isinstance(response.get("citations"), list),
            "has_processing_time": "processing_time_ms" in response,
            "has_metadata": "metadata" in response
        }
        
        # Check entity structure
        if validations["entities_is_list"] and response["entities"]:
            entity = response["entities"][0]
            validations["entity_has_text"] = "entity_text" in entity
            validations["entity_has_type"] = "entity_type" in entity
            validations["entity_has_confidence"] = "confidence" in entity
        
        # Check citation structure  
        if validations["citations_is_list"] and response["citations"]:
            citation = response["citations"][0]
            validations["citation_has_text"] = "citation_text" in citation
            validations["citation_has_type"] = "citation_type" in citation
        
        return validations
    
    def run_tests(self) -> None:
        """Run all template execution tests"""
        print("=" * 80)
        print("TEMPLATE EXECUTION VALIDATION TEST SUITE")
        print("=" * 80)
        
        # Test all templates
        results = self.test_all_templates()
        
        # Generate summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed']} ({results['passed']/max(1, results['total_tests'])*100:.1f}%)")
        print(f"Failed: {results['failed']} ({results['failed']/max(1, results['total_tests'])*100:.1f}%)")
        
        # Strategy breakdown
        print("\nStrategy Breakdown:")
        for strategy, data in results["strategy_results"].items():
            print(f"\n  {strategy.upper()}:")
            print(f"    Total: {data['total']}")
            print(f"    Passed: {data['passed']}")
            print(f"    Failed: {data['failed']}")
            
            if data["failed"] > 0:
                print(f"    Failed Templates:")
                for template, details in data["templates"].items():
                    if not details["passed"]:
                        print(f"      - {template}: {details['details'].get('error', 'Unknown')}")
        
        # Save results
        output_file = f"tests/results/template_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nDetailed results saved to: {output_file}")
        
        # Return exit code
        return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    tester = TemplateExecutionTester()
    exit_code = tester.run_tests()
    exit(exit_code)