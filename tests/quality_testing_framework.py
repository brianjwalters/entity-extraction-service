#!/usr/bin/env python3
"""
Quality Testing Framework for SaulLM Fine-Tuning

This framework provides automated quality testing and validation for SaulLM fine-tuning,
including pre/post training comparisons, entity recognition validation, and relationship
detection quality assessment.
"""

import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import statistics
from collections import defaultdict, Counter
import subprocess

# Import our baseline framework
from baseline_framework import BaselineFramework, DocumentMetrics, BaselineComparison

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QualityTestResult:
    """Results of a quality test run."""
    test_name: str
    model_type: str  # "baseline" or "fine-tuned"
    document_name: str
    test_timestamp: str
    
    # Entity extraction metrics
    total_entities: int
    unique_entity_types: int
    avg_confidence: float
    processing_time: float
    
    # Quality metrics
    precision: float
    recall: float
    f1_score: float
    
    # Detailed results
    entity_type_distribution: Dict[str, int]
    confidence_distribution: Dict[str, float]
    sample_entities: List[Dict[str, Any]]
    
    # Performance metrics
    throughput_entities_per_second: float
    memory_usage_gb: float

@dataclass
class QualityComparisonResult:
    """Comparison results between baseline and fine-tuned models."""
    baseline_result: QualityTestResult
    fine_tuned_result: QualityTestResult
    
    # Improvement metrics
    entity_count_improvement_pct: float
    type_diversity_improvement_pct: float
    confidence_improvement_pct: float
    speed_improvement_pct: float
    
    # Quality improvements
    precision_improvement: float
    recall_improvement: float
    f1_improvement: float
    
    # New capabilities
    new_entity_types: List[str]
    improved_entity_types: List[str]
    degraded_entity_types: List[str]
    
    # Overall assessment
    overall_improvement_score: float
    passes_quality_threshold: bool

class QualityTestingFramework:
    """Comprehensive quality testing framework for SaulLM fine-tuning."""
    
    def __init__(self, results_dir: str = "tests/results"):
        """Initialize the quality testing framework.
        
        Args:
            results_dir: Directory to store test results and reports
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.results_dir / "quality_tests").mkdir(exist_ok=True)
        (self.results_dir / "quality_reports").mkdir(exist_ok=True)
        (self.results_dir / "quality_comparisons").mkdir(exist_ok=True)
        
        # Initialize baseline framework
        self.baseline_framework = BaselineFramework(results_dir)
        
        # Quality thresholds
        self.quality_thresholds = {
            "min_entity_count_improvement": 10.0,  # 10% minimum improvement
            "min_confidence_improvement": 5.0,     # 5% minimum improvement
            "min_type_diversity_improvement": 15.0, # 15% minimum improvement
            "max_speed_degradation": -10.0,        # Maximum 10% speed loss
            "min_f1_score": 0.8,                   # Minimum F1 score
            "min_overall_improvement": 0.15        # 15% overall improvement
        }
    
    async def run_saullm_test(self, document_name: str, model_type: str = "baseline") -> QualityTestResult:
        """Run SaulLM test on a document and collect quality metrics.
        
        Args:
            document_name: Name of the document to test (rahimi, dobbs)
            model_type: Type of model (baseline, fine-tuned)
            
        Returns:
            QualityTestResult with comprehensive metrics
        """
        logger.info(f"🧪 Running SaulLM quality test: {document_name} ({model_type})")
        
        # Determine test script based on document
        if document_name.lower() == "rahimi":
            test_script = "tests/test_saullm_rahimi_comparison.py"
        elif document_name.lower() == "dobbs":
            test_script = "tests/test_saullm_dobbs_comparison.py"
        else:
            raise ValueError(f"Unsupported document: {document_name}")
        
        # Run the test
        start_time = time.time()
        
        try:
            # Activate venv and run test
            cmd = f"source venv/bin/activate && CUDA_VISIBLE_DEVICES=1 timeout 3600 python {test_script}"
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path.cwd()
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Test failed with return code {process.returncode}")
                logger.error(f"stderr: {stderr.decode()}")
                raise RuntimeError(f"SaulLM test failed for {document_name}")
            
            processing_time = time.time() - start_time
            
            # Find the most recent result file
            pattern = f"saullm_{document_name.lower()}_results_*.json"
            result_files = list(self.results_dir.glob(pattern))
            
            if not result_files:
                raise FileNotFoundError(f"No result files found for pattern: {pattern}")
            
            latest_result = max(result_files, key=lambda p: p.stat().st_mtime)
            
            # Load and analyze results
            with open(latest_result, 'r') as f:
                data = json.load(f)
            
            metrics = data.get("metrics", {})
            entities = data.get("entities", [])
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(entities, metrics)
            
            # Create quality test result
            result = QualityTestResult(
                test_name=f"{document_name}_{model_type}",
                model_type=model_type,
                document_name=document_name,
                test_timestamp=datetime.now().isoformat(),
                total_entities=metrics.get("entities_found", len(entities)),
                unique_entity_types=metrics.get("unique_entities", len(set(e.get("type") for e in entities))),
                avg_confidence=metrics.get("confidence_avg", 0.0),
                processing_time=processing_time,
                precision=quality_metrics["precision"],
                recall=quality_metrics["recall"],
                f1_score=quality_metrics["f1_score"],
                entity_type_distribution=metrics.get("entity_types", {}),
                confidence_distribution=quality_metrics["confidence_distribution"],
                sample_entities=entities[:10],
                throughput_entities_per_second=metrics.get("entities_found", len(entities)) / processing_time,
                memory_usage_gb=0.0  # Will be updated separately
            )
            
            # Save result
            self._save_quality_result(result)
            
            logger.info(f"✅ Quality test completed: {result.total_entities} entities, F1: {result.f1_score:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"Error running SaulLM test: {e}")
            raise
    
    def _calculate_quality_metrics(self, entities: List[Dict], metrics: Dict) -> Dict[str, Any]:
        """Calculate quality metrics from extraction results.
        
        Args:
            entities: List of extracted entities
            metrics: Test metrics
            
        Returns:
            Dictionary with quality metrics
        """
        confidences = [e.get("confidence", 0.0) for e in entities]
        
        # Calculate confidence distribution
        confidence_bins = {
            "high (>0.9)": len([c for c in confidences if c > 0.9]),
            "medium (0.7-0.9)": len([c for c in confidences if 0.7 <= c <= 0.9]),
            "low (<0.7)": len([c for c in confidences if c < 0.7])
        }
        
        # For now, use simplified quality metrics
        # In a real scenario, you'd compare against ground truth
        precision = min(1.0, sum(confidences) / len(confidences) if confidences else 0.0)
        recall = min(1.0, len(entities) / max(100, len(entities)))  # Simplified
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "confidence_distribution": confidence_bins
        }
    
    def _save_quality_result(self, result: QualityTestResult) -> Path:
        """Save quality test result to file.
        
        Args:
            result: QualityTestResult to save
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quality_{result.test_name}_{timestamp}.json"
        filepath = self.results_dir / "quality_tests" / filename
        
        with open(filepath, 'w') as f:
            json.dump(asdict(result), f, indent=2, default=str)
        
        logger.info(f"Quality result saved to {filepath}")
        return filepath
    
    def compare_quality_results(self, baseline_result: QualityTestResult, 
                               fine_tuned_result: QualityTestResult) -> QualityComparisonResult:
        """Compare baseline and fine-tuned model results.
        
        Args:
            baseline_result: Baseline model test result
            fine_tuned_result: Fine-tuned model test result
            
        Returns:
            QualityComparisonResult with detailed comparison
        """
        logger.info(f"🔍 Comparing quality results: {baseline_result.test_name} vs {fine_tuned_result.test_name}")
        
        # Calculate improvement percentages
        entity_count_improvement = (
            (fine_tuned_result.total_entities - baseline_result.total_entities) /
            baseline_result.total_entities * 100 if baseline_result.total_entities > 0 else 0.0
        )
        
        type_diversity_improvement = (
            (fine_tuned_result.unique_entity_types - baseline_result.unique_entity_types) /
            baseline_result.unique_entity_types * 100 if baseline_result.unique_entity_types > 0 else 0.0
        )
        
        confidence_improvement = (
            (fine_tuned_result.avg_confidence - baseline_result.avg_confidence) /
            baseline_result.avg_confidence * 100 if baseline_result.avg_confidence > 0 else 0.0
        )
        
        speed_improvement = (
            (baseline_result.processing_time - fine_tuned_result.processing_time) /
            baseline_result.processing_time * 100 if baseline_result.processing_time > 0 else 0.0
        )
        
        # Quality metric improvements
        precision_improvement = fine_tuned_result.precision - baseline_result.precision
        recall_improvement = fine_tuned_result.recall - baseline_result.recall
        f1_improvement = fine_tuned_result.f1_score - baseline_result.f1_score
        
        # Analyze entity type changes
        baseline_types = set(baseline_result.entity_type_distribution.keys())
        fine_tuned_types = set(fine_tuned_result.entity_type_distribution.keys())
        
        new_entity_types = list(fine_tuned_types - baseline_types)
        
        improved_entity_types = []
        degraded_entity_types = []
        
        for entity_type in baseline_types.intersection(fine_tuned_types):
            baseline_count = baseline_result.entity_type_distribution[entity_type]
            fine_tuned_count = fine_tuned_result.entity_type_distribution[entity_type]
            
            if fine_tuned_count > baseline_count:
                improved_entity_types.append(entity_type)
            elif fine_tuned_count < baseline_count:
                degraded_entity_types.append(entity_type)
        
        # Calculate overall improvement score
        improvement_factors = [
            entity_count_improvement / 100,
            type_diversity_improvement / 100,
            confidence_improvement / 100,
            max(-0.1, speed_improvement / 100),  # Cap speed loss
            precision_improvement,
            recall_improvement,
            f1_improvement
        ]
        
        overall_improvement_score = sum(improvement_factors) / len(improvement_factors)
        
        # Check if passes quality threshold
        passes_threshold = (
            entity_count_improvement >= self.quality_thresholds["min_entity_count_improvement"] and
            confidence_improvement >= self.quality_thresholds["min_confidence_improvement"] and
            type_diversity_improvement >= self.quality_thresholds["min_type_diversity_improvement"] and
            speed_improvement >= self.quality_thresholds["max_speed_degradation"] and
            fine_tuned_result.f1_score >= self.quality_thresholds["min_f1_score"] and
            overall_improvement_score >= self.quality_thresholds["min_overall_improvement"]
        )
        
        comparison = QualityComparisonResult(
            baseline_result=baseline_result,
            fine_tuned_result=fine_tuned_result,
            entity_count_improvement_pct=entity_count_improvement,
            type_diversity_improvement_pct=type_diversity_improvement,
            confidence_improvement_pct=confidence_improvement,
            speed_improvement_pct=speed_improvement,
            precision_improvement=precision_improvement,
            recall_improvement=recall_improvement,
            f1_improvement=f1_improvement,
            new_entity_types=new_entity_types,
            improved_entity_types=improved_entity_types,
            degraded_entity_types=degraded_entity_types,
            overall_improvement_score=overall_improvement_score,
            passes_quality_threshold=passes_threshold
        )
        
        # Save comparison
        self._save_quality_comparison(comparison)
        
        return comparison
    
    def _save_quality_comparison(self, comparison: QualityComparisonResult) -> Path:
        """Save quality comparison result to file.
        
        Args:
            comparison: QualityComparisonResult to save
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quality_comparison_{comparison.baseline_result.document_name}_{timestamp}.json"
        filepath = self.results_dir / "quality_comparisons" / filename
        
        with open(filepath, 'w') as f:
            json.dump(asdict(comparison), f, indent=2, default=str)
        
        logger.info(f"Quality comparison saved to {filepath}")
        return filepath
    
    def generate_quality_report(self, comparison: QualityComparisonResult) -> str:
        """Generate a comprehensive quality comparison report.
        
        Args:
            comparison: QualityComparisonResult to report on
            
        Returns:
            Markdown formatted report string
        """
        baseline = comparison.baseline_result
        fine_tuned = comparison.fine_tuned_result
        
        status = "✅ PASSED" if comparison.passes_quality_threshold else "❌ FAILED"
        
        report = f"""# SaulLM Fine-Tuning Quality Assessment Report

## 🎯 Overall Assessment: {status}

**Document**: {baseline.document_name.title()}  
**Test Date**: {fine_tuned.test_timestamp}  
**Overall Improvement Score**: {comparison.overall_improvement_score:.3f}

## 📊 Performance Comparison

| Metric | Baseline | Fine-Tuned | Change | Status |
|--------|----------|------------|--------|--------|
| **Total Entities** | {baseline.total_entities} | {fine_tuned.total_entities} | {comparison.entity_count_improvement_pct:+.1f}% | {"✅" if comparison.entity_count_improvement_pct >= 10 else "⚠️"} |
| **Entity Types** | {baseline.unique_entity_types} | {fine_tuned.unique_entity_types} | {comparison.type_diversity_improvement_pct:+.1f}% | {"✅" if comparison.type_diversity_improvement_pct >= 15 else "⚠️"} |
| **Avg Confidence** | {baseline.avg_confidence:.3f} | {fine_tuned.avg_confidence:.3f} | {comparison.confidence_improvement_pct:+.1f}% | {"✅" if comparison.confidence_improvement_pct >= 5 else "⚠️"} |
| **Processing Time** | {baseline.processing_time:.1f}s | {fine_tuned.processing_time:.1f}s | {comparison.speed_improvement_pct:+.1f}% | {"✅" if comparison.speed_improvement_pct >= -10 else "⚠️"} |

## 🎯 Quality Metrics

| Metric | Baseline | Fine-Tuned | Improvement | Target |
|--------|----------|------------|-------------|--------|
| **Precision** | {baseline.precision:.3f} | {fine_tuned.precision:.3f} | {comparison.precision_improvement:+.3f} | {"✅" if fine_tuned.precision >= 0.8 else "❌"} |
| **Recall** | {baseline.recall:.3f} | {fine_tuned.recall:.3f} | {comparison.recall_improvement:+.3f} | {"✅" if fine_tuned.recall >= 0.8 else "❌"} |
| **F1 Score** | {baseline.f1_score:.3f} | {fine_tuned.f1_score:.3f} | {comparison.f1_improvement:+.3f} | {"✅" if fine_tuned.f1_score >= 0.8 else "❌"} |

## 🆕 New Entity Types Discovered

"""
        
        if comparison.new_entity_types:
            for entity_type in comparison.new_entity_types:
                count = fine_tuned.entity_type_distribution.get(entity_type, 0)
                report += f"- **{entity_type}**: {count} entities\n"
        else:
            report += "- No new entity types discovered\n"
        
        report += "\n## 📈 Improved Entity Types\n\n"
        
        if comparison.improved_entity_types:
            for entity_type in comparison.improved_entity_types:
                baseline_count = baseline.entity_type_distribution.get(entity_type, 0)
                fine_tuned_count = fine_tuned.entity_type_distribution.get(entity_type, 0)
                improvement = (fine_tuned_count - baseline_count) / baseline_count * 100 if baseline_count > 0 else 0
                report += f"- **{entity_type}**: {baseline_count} → {fine_tuned_count} ({improvement:+.1f}%)\n"
        else:
            report += "- No entity types showed improvement\n"
        
        report += "\n## 📉 Degraded Entity Types\n\n"
        
        if comparison.degraded_entity_types:
            for entity_type in comparison.degraded_entity_types:
                baseline_count = baseline.entity_type_distribution.get(entity_type, 0)
                fine_tuned_count = fine_tuned.entity_type_distribution.get(entity_type, 0)
                degradation = (fine_tuned_count - baseline_count) / baseline_count * 100 if baseline_count > 0 else 0
                report += f"- **{entity_type}**: {baseline_count} → {fine_tuned_count} ({degradation:+.1f}%)\n"
        else:
            report += "- No entity types showed degradation\n"
        
        report += f"""
## 🔍 Detailed Analysis

### Confidence Distribution

**Baseline:**
- High confidence (>0.9): {baseline.confidence_distribution.get("high (>0.9)", 0)} entities
- Medium confidence (0.7-0.9): {baseline.confidence_distribution.get("medium (0.7-0.9)", 0)} entities
- Low confidence (<0.7): {baseline.confidence_distribution.get("low (<0.7)", 0)} entities

**Fine-Tuned:**
- High confidence (>0.9): {fine_tuned.confidence_distribution.get("high (>0.9)", 0)} entities
- Medium confidence (0.7-0.9): {fine_tuned.confidence_distribution.get("medium (0.7-0.9)", 0)} entities
- Low confidence (<0.7): {fine_tuned.confidence_distribution.get("low (<0.7)", 0)} entities

### Performance Metrics

- **Throughput Improvement**: {fine_tuned.throughput_entities_per_second - baseline.throughput_entities_per_second:+.2f} entities/sec
- **Baseline Throughput**: {baseline.throughput_entities_per_second:.2f} entities/sec
- **Fine-Tuned Throughput**: {fine_tuned.throughput_entities_per_second:.2f} entities/sec

## 🎯 Quality Thresholds Assessment

"""
        
        thresholds = [
            ("Entity Count Improvement", f"{comparison.entity_count_improvement_pct:.1f}%", "≥10%", comparison.entity_count_improvement_pct >= 10),
            ("Confidence Improvement", f"{comparison.confidence_improvement_pct:.1f}%", "≥5%", comparison.confidence_improvement_pct >= 5),
            ("Type Diversity Improvement", f"{comparison.type_diversity_improvement_pct:.1f}%", "≥15%", comparison.type_diversity_improvement_pct >= 15),
            ("Speed Degradation", f"{comparison.speed_improvement_pct:.1f}%", "≥-10%", comparison.speed_improvement_pct >= -10),
            ("F1 Score", f"{fine_tuned.f1_score:.3f}", "≥0.8", fine_tuned.f1_score >= 0.8),
            ("Overall Improvement", f"{comparison.overall_improvement_score:.3f}", "≥0.15", comparison.overall_improvement_score >= 0.15)
        ]
        
        for metric, actual, target, passed in thresholds:
            status_icon = "✅" if passed else "❌"
            report += f"- **{metric}**: {actual} (target: {target}) {status_icon}\n"
        
        report += f"""
## 📋 Recommendations

"""
        
        if comparison.passes_quality_threshold:
            report += """✅ **Fine-tuning successful!** The model shows significant improvements across key metrics.

**Next Steps:**
1. Deploy fine-tuned model to production
2. Monitor performance with real-world data
3. Consider additional fine-tuning with more diverse examples

**Key Achievements:**
- Enhanced entity recognition accuracy
- Improved entity type diversity
- Maintained processing performance
"""
        else:
            report += """❌ **Fine-tuning needs improvement.** Some quality thresholds were not met.

**Recommended Actions:**
1. Review training data quality and diversity
2. Adjust fine-tuning hyperparameters
3. Increase training examples for underperforming entity types
4. Consider longer training duration

**Areas for Improvement:**
"""
            
            if comparison.entity_count_improvement_pct < 10:
                report += "- Increase entity recognition rate\n"
            if comparison.confidence_improvement_pct < 5:
                report += "- Improve confidence calibration\n"
            if comparison.type_diversity_improvement_pct < 15:
                report += "- Enhance entity type diversity\n"
            if fine_tuned.f1_score < 0.8:
                report += "- Improve overall precision and recall\n"
        
        return report
    
    async def run_comprehensive_quality_test(self, document_names: List[str] = ["rahimi", "dobbs"]) -> Dict[str, QualityComparisonResult]:
        """Run comprehensive quality tests on multiple documents.
        
        Args:
            document_names: List of document names to test
            
        Returns:
            Dictionary mapping document names to comparison results
        """
        logger.info(f"🚀 Starting comprehensive quality testing for: {document_names}")
        
        results = {}
        
        for document_name in document_names:
            try:
                logger.info(f"📖 Testing document: {document_name}")
                
                # Run baseline test
                baseline_result = await self.run_saullm_test(document_name, "baseline")
                
                # Note: For now, we'll use the same baseline as "fine-tuned" since we haven't run fine-tuning yet
                # In actual implementation, this would run the fine-tuned model
                fine_tuned_result = await self.run_saullm_test(document_name, "fine-tuned-simulation")
                
                # Compare results
                comparison = self.compare_quality_results(baseline_result, fine_tuned_result)
                
                # Generate report
                report = self.generate_quality_report(comparison)
                
                # Save report
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_file = self.results_dir / "quality_reports" / f"quality_report_{document_name}_{timestamp}.md"
                with open(report_file, 'w') as f:
                    f.write(report)
                
                results[document_name] = comparison
                
                logger.info(f"✅ Quality test completed for {document_name}")
                
            except Exception as e:
                logger.error(f"❌ Quality test failed for {document_name}: {e}")
                continue
        
        return results

def main():
    """Example usage of the quality testing framework."""
    
    # Initialize framework
    framework = QualityTestingFramework()
    
    print("🧪 SaulLM Quality Testing Framework")
    print("=" * 50)
    
    # Run comprehensive quality tests
    try:
        results = asyncio.run(framework.run_comprehensive_quality_test(["rahimi"]))
        
        for document_name, comparison in results.items():
            status = "PASSED" if comparison.passes_quality_threshold else "FAILED"
            improvement = comparison.overall_improvement_score
            
            print(f"\n📊 {document_name.title()} Results:")
            print(f"   Status: {status}")
            print(f"   Overall Improvement: {improvement:.3f}")
            print(f"   Entity Count: {comparison.baseline_result.total_entities} → {comparison.fine_tuned_result.total_entities}")
            print(f"   Confidence: {comparison.baseline_result.avg_confidence:.3f} → {comparison.fine_tuned_result.avg_confidence:.3f}")
        
    except Exception as e:
        logger.error(f"Quality testing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()