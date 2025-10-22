#!/usr/bin/env python3
"""
Entity Extraction Test Result Generator
Generates standardized test results following AGENT_DEFINITIONS.md structure
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import argparse


class EntityExtractionTestResult:
    """Generates standardized entity extraction test results"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.iso_timestamp = datetime.now().isoformat()
        self.results_dir = Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize standard structure
        self.structure = {
            "test_metadata": {
                "pipeline_id": f"test_{self.timestamp}",
                "test_document": "/srv/luris/be/tests/docs/Rahimi.pdf",
                "test_timestamp": self.iso_timestamp,
                "test_status": "in_progress",
                "extraction_mode": "regex",  # regex|spacy|ai_enhanced
                "service_version": "1.0.0"
            },
            "service_health": {
                "document_upload": False,
                "entity_extraction": False,
                "graphrag": False,
                "vllm": False,
                "prompt_service": False
            },
            "entity_mappings": [],
            "citation_mappings": [],
            "performance_metrics": {
                "upload_time_ms": 0.0,
                "extraction_time_ms": 0.0,
                "graph_creation_time_ms": 0.0,
                "total_pipeline_time_ms": 0.0,
                "entities_per_second": 0.0,
                "memory_usage_mb": 0.0
            },
            "quality_analysis": {
                "entity_type_statistics": {},
                "extraction_summary": {
                    "total_entities": 0,
                    "unique_entities": 0,
                    "total_citations": 0,
                    "unique_citations": 0,
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1_score": 0.0
                },
                "inspection_examples": {}
            }
        }
    
    def set_metadata(self, **kwargs):
        """Update test metadata"""
        self.structure["test_metadata"].update(kwargs)
        return self
    
    def set_service_health(self, **kwargs):
        """Update service health status"""
        self.structure["service_health"].update(kwargs)
        return self
    
    def add_entity_mapping(self, entity: Dict[str, Any]):
        """Add an entity mapping result"""
        required_fields = {
            "entity_type": entity.get("entity_type", "UNKNOWN"),
            "extracted_text": entity.get("extracted_text", ""),
            "normalized_text": entity.get("normalized_text", ""),
            "confidence_score": entity.get("confidence_score", 0.0),
            "position": entity.get("position", {"start": 0, "end": 0}),
            "context_snippet": entity.get("context_snippet", ""),
            "original_text_at_position": entity.get("original_text_at_position", ""),
            "discovery_method": entity.get("discovery_method", "regex"),
            "agent_name": entity.get("agent_name", "PatternMatcher"),
            "attributes": entity.get("attributes", {})
        }
        self.structure["entity_mappings"].append(required_fields)
        return self
    
    def add_citation_mapping(self, citation: Dict[str, Any]):
        """Add a citation mapping result"""
        required_fields = {
            "citation_type": citation.get("citation_type", "CASE_CITATION"),
            "original_text": citation.get("original_text", ""),
            "normalized_citation": citation.get("normalized_citation", ""),
            "bluebook_format": citation.get("bluebook_format", ""),
            "confidence_score": citation.get("confidence_score", 0.0),
            "components": citation.get("components", {
                "reporter": "",
                "volume": "",
                "page": "",
                "court": "",
                "year": ""
            }),
            "position": citation.get("position", {"start": 0, "end": 0})
        }
        self.structure["citation_mappings"].append(required_fields)
        return self
    
    def set_performance_metrics(self, **kwargs):
        """Update performance metrics"""
        self.structure["performance_metrics"].update(kwargs)
        
        # Calculate derived metrics
        if self.structure["entity_mappings"]:
            total_time = self.structure["performance_metrics"]["extraction_time_ms"]
            if total_time > 0:
                entities_count = len(self.structure["entity_mappings"])
                self.structure["performance_metrics"]["entities_per_second"] = (
                    entities_count / (total_time / 1000.0)
                )
        return self
    
    def calculate_quality_metrics(self):
        """Calculate quality analysis metrics"""
        # Calculate entity type statistics
        entity_stats = {}
        for entity in self.structure["entity_mappings"]:
            entity_type = entity["entity_type"]
            if entity_type not in entity_stats:
                entity_stats[entity_type] = {
                    "count": 0,
                    "confidences": [],
                    "examples": []
                }
            
            entity_stats[entity_type]["count"] += 1
            entity_stats[entity_type]["confidences"].append(entity["confidence_score"])
            
            if len(entity_stats[entity_type]["examples"]) < 3:
                entity_stats[entity_type]["examples"].append(entity["extracted_text"])
        
        # Calculate statistics
        for entity_type, stats in entity_stats.items():
            confidences = stats["confidences"]
            self.structure["quality_analysis"]["entity_type_statistics"][entity_type] = {
                "count": stats["count"],
                "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
                "min_confidence": min(confidences) if confidences else 0,
                "max_confidence": max(confidences) if confidences else 0,
                "examples": stats["examples"]
            }
        
        # Calculate extraction summary
        unique_entities = set(e["normalized_text"] for e in self.structure["entity_mappings"])
        unique_citations = set(c["normalized_citation"] for c in self.structure["citation_mappings"])
        
        self.structure["quality_analysis"]["extraction_summary"].update({
            "total_entities": len(self.structure["entity_mappings"]),
            "unique_entities": len(unique_entities),
            "total_citations": len(self.structure["citation_mappings"]),
            "unique_citations": len(unique_citations)
        })
        
        # Add inspection examples
        for entity_type in list(entity_stats.keys())[:3]:  # Top 3 types
            examples = []
            for entity in self.structure["entity_mappings"]:
                if entity["entity_type"] == entity_type and len(examples) < 2:
                    examples.append({
                        "original": entity["extracted_text"],
                        "normalized": entity["normalized_text"],
                        "confidence": entity["confidence_score"],
                        "context": entity["context_snippet"][:100]
                    })
            self.structure["quality_analysis"]["inspection_examples"][entity_type] = examples
        
        return self
    
    def finalize(self):
        """Mark test as completed and calculate final metrics"""
        self.structure["test_metadata"]["test_status"] = "completed"
        
        # Calculate total pipeline time
        metrics = self.structure["performance_metrics"]
        metrics["total_pipeline_time_ms"] = (
            metrics["upload_time_ms"] + 
            metrics["extraction_time_ms"] + 
            metrics["graph_creation_time_ms"]
        )
        
        # Calculate quality metrics
        self.calculate_quality_metrics()
        
        return self
    
    def save_json(self, filename: Optional[str] = None) -> str:
        """Save results to JSON file"""
        if filename is None:
            filename = f"extraction_{self.timestamp}.json"
        
        filepath = self.results_dir / filename
        with open(filepath, 'w') as f:
            json.dump(self.structure, f, indent=2, default=str)
        
        print(f"Results saved to: {filepath}")
        return str(filepath)
    
    def save_markdown(self, filename: Optional[str] = None) -> str:
        """Generate and save markdown report"""
        if filename is None:
            filename = f"extraction_{self.timestamp}.md"
        
        filepath = self.results_dir / filename
        
        md_content = self._generate_markdown_report()
        with open(filepath, 'w') as f:
            f.write(md_content)
        
        print(f"Markdown report saved to: {filepath}")
        return str(filepath)
    
    def _generate_markdown_report(self) -> str:
        """Generate comprehensive markdown report"""
        s = self.structure
        
        report = f"""# Entity Extraction Test Report

## Test Information
- **Pipeline ID**: {s['test_metadata']['pipeline_id']}
- **Timestamp**: {s['test_metadata']['test_timestamp']}
- **Document**: {s['test_metadata']['test_document']}
- **Extraction Mode**: {s['test_metadata']['extraction_mode']}
- **Status**: {s['test_metadata']['test_status']}

## Service Health
| Service | Status |
|---------|--------|
| Document Upload | {'✅' if s['service_health']['document_upload'] else '❌'} |
| Entity Extraction | {'✅' if s['service_health']['entity_extraction'] else '❌'} |
| GraphRAG | {'✅' if s['service_health']['graphrag'] else '❌'} |
| vLLM | {'✅' if s['service_health']['vllm'] else '❌'} |
| Prompt Service | {'✅' if s['service_health']['prompt_service'] else '❌'} |

## Performance Metrics
| Metric | Value |
|--------|-------|
| Upload Time | {s['performance_metrics']['upload_time_ms']:.2f} ms |
| Extraction Time | {s['performance_metrics']['extraction_time_ms']:.2f} ms |
| Graph Creation Time | {s['performance_metrics']['graph_creation_time_ms']:.2f} ms |
| Total Pipeline Time | {s['performance_metrics']['total_pipeline_time_ms']:.2f} ms |
| Entities/Second | {s['performance_metrics']['entities_per_second']:.2f} |
| Memory Usage | {s['performance_metrics']['memory_usage_mb']:.2f} MB |

## Extraction Summary
- **Total Entities**: {s['quality_analysis']['extraction_summary']['total_entities']}
- **Unique Entities**: {s['quality_analysis']['extraction_summary']['unique_entities']}
- **Total Citations**: {s['quality_analysis']['extraction_summary']['total_citations']}
- **Unique Citations**: {s['quality_analysis']['extraction_summary']['unique_citations']}
- **Precision**: {s['quality_analysis']['extraction_summary']['precision']:.2%}
- **Recall**: {s['quality_analysis']['extraction_summary']['recall']:.2%}
- **F1 Score**: {s['quality_analysis']['extraction_summary']['f1_score']:.2%}

## Entity Type Statistics
| Entity Type | Count | Avg Confidence | Examples |
|-------------|-------|----------------|----------|
"""
        
        for entity_type, stats in s['quality_analysis']['entity_type_statistics'].items():
            examples = ', '.join(f'"{ex}"' for ex in stats['examples'][:2])
            report += f"| {entity_type} | {stats['count']} | {stats['avg_confidence']:.2f} | {examples} |\n"
        
        report += "\n## Sample Entity Mappings\n"
        for entity in s['entity_mappings'][:5]:
            report += f"""
### {entity['entity_type']}
- **Extracted**: "{entity['extracted_text']}"
- **Normalized**: "{entity['normalized_text']}"
- **Confidence**: {entity['confidence_score']:.2f}
- **Method**: {entity['discovery_method']}
"""
        
        report += "\n## Sample Citation Mappings\n"
        for citation in s['citation_mappings'][:5]:
            report += f"""
### {citation['citation_type']}
- **Original**: "{citation['original_text']}"
- **Bluebook**: "{citation['bluebook_format']}"
- **Confidence**: {citation['confidence_score']:.2f}
"""
        
        return report
    
    def get_results(self) -> Dict[str, Any]:
        """Get the complete results structure"""
        return self.structure


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Generate entity extraction test results")
    parser.add_argument("--mode", choices=["regex", "spacy", "ai_enhanced"], 
                       default="regex", help="Extraction mode")
    parser.add_argument("--save", action="store_true", 
                       help="Save results to files")
    parser.add_argument("--example", action="store_true",
                       help="Generate example data")
    
    args = parser.parse_args()
    
    # Create test result generator
    generator = EntityExtractionTestResult()
    
    # Set metadata
    generator.set_metadata(extraction_mode=args.mode)
    
    # Set service health (example)
    generator.set_service_health(
        document_upload=True,
        entity_extraction=True,
        graphrag=True,
        vllm=False,
        prompt_service=True
    )
    
    if args.example:
        # Add example entities
        generator.add_entity_mapping({
            "entity_type": "JUDGE",
            "extracted_text": "Chief Justice Roberts",
            "normalized_text": "John G. Roberts Jr.",
            "confidence_score": 0.95,
            "position": {"start": 1234, "end": 1255},
            "context_snippet": "...delivered the opinion of the Court. Chief Justice Roberts stated that...",
            "discovery_method": "regex",
            "agent_name": "PatternMatcher"
        })
        
        generator.add_entity_mapping({
            "entity_type": "CASE_CITATION",
            "extracted_text": "District of Columbia v. Heller",
            "normalized_text": "District of Columbia v. Heller",
            "confidence_score": 0.98,
            "position": {"start": 2345, "end": 2375},
            "context_snippet": "...as established in District of Columbia v. Heller...",
            "discovery_method": "regex",
            "agent_name": "CitationExtractor"
        })
        
        # Add example citation
        generator.add_citation_mapping({
            "citation_type": "CASE_CITATION",
            "original_text": "District of Columbia v. Heller, 554 U.S. 570",
            "normalized_citation": "District of Columbia v. Heller, 554 U.S. 570 (2008)",
            "bluebook_format": "District of Columbia v. Heller, 554 U.S. 570 (2008)",
            "confidence_score": 0.98,
            "components": {
                "reporter": "U.S.",
                "volume": "554",
                "page": "570",
                "court": "Supreme Court",
                "year": "2008"
            }
        })
        
        # Set performance metrics
        generator.set_performance_metrics(
            upload_time_ms=1523.45,
            extraction_time_ms=487.23,
            graph_creation_time_ms=2341.67,
            memory_usage_mb=256.8
        )
    
    # Finalize results
    generator.finalize()
    
    if args.save:
        json_path = generator.save_json()
        md_path = generator.save_markdown()
        print(f"\nTest results saved:")
        print(f"  JSON: {json_path}")
        print(f"  Markdown: {md_path}")
    else:
        # Print results to console
        print(json.dumps(generator.get_results(), indent=2, default=str))


if __name__ == "__main__":
    main()