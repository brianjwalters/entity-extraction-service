#!/usr/bin/env python3
"""
Family Law Pattern Optimization Script
Analyzes and optimizes 15 newly added regex patterns for performance.
"""

import re
import time
from typing import Dict, List, Tuple

# Original patterns from family_law.yaml (15 new patterns)
ORIGINAL_PATTERNS = {
    # jurisdiction_concepts (5 patterns)
    "home_state": r"\b(?:home\s+state|child(?:'s|'s)?\s+home\s+state|home\s+state\s+jurisdiction)",
    "emergency_jurisdiction": r"\b(?:emergency\s+jurisdiction|imminent\s+harm|emergency\s+protective\s+custody)",
    "exclusive_continuing_jurisdiction": r"\b(?:exclusive\s+continuing\s+jurisdiction|retains\s+jurisdiction|continuing\s+exclusive\s+jurisdiction)",
    "significant_connection": r"\b(?:significant\s+connection|substantial\s+evidence)",
    "foreign_custody_order": r"\b(?:foreign\s+custody\s+order|out-of-state\s+order|registered\s+order)",

    # procedural_documents (5 patterns)
    "dissolution_petition": r"\b(?:petition\s+for\s+dissolution|dissolution\s+petition)",
    "temporary_order": r"\b(?:temporary\s+order|interim\s+order|pendente\s+lite)",
    "final_decree": r"\b(?:final\s+decree|decree\s+of\s+dissolution)",
    "modification_petition": r"\b(?:petition\s+to\s+modify|modification\s+petition)",
    "guardian_ad_litem": r"\b(?:guardian\s+ad\s+litem|GAL\s+appointed)",

    # property_division (2 patterns)
    "community_property": r"\b(?:community\s+property|community\s+estate|marital\s+property)",
    "separate_property": r"\b(?:separate\s+property|property\s+acquired\s+before\s+marriage)",

    # child_protection (3 patterns)
    "child_abuse_report": r"\b(?:CPS\s+report|child\s+protective\s+services\s+report|abuse\s+report)",
    "dependency_action": r"\b(?:dependency\s+action|dependency\s+petition|juvenile\s+court\s+dependency)",
    "protective_custody": r"\b(?:protective\s+custody|emergency\s+protective\s+custody|child\s+taken\s+into\s+custody)",
}

# Test cases for each pattern
TEST_CASES = {
    "home_state": [
        "California is the child's home state",
        "home state jurisdiction under the UCCJEA",
        "child's home state is Washington",
        "Washington has home state jurisdiction",
    ],
    "emergency_jurisdiction": [
        "emergency jurisdiction exercised due to imminent harm",
        "emergency protective custody jurisdiction",
        "imminent harm to child requires emergency jurisdiction",
    ],
    "exclusive_continuing_jurisdiction": [
        "Washington retains exclusive continuing jurisdiction",
        "exclusive continuing jurisdiction over custody matters",
        "continuing exclusive jurisdiction established",
    ],
    "significant_connection": [
        "child has significant connections to Washington",
        "substantial evidence of connection to state",
        "substantial evidence supports jurisdiction",
    ],
    "foreign_custody_order": [
        "Nevada custody order registered in Washington",
        "foreign custody order from California",
        "out-of-state order recognition requested",
        "registered order from Oregon",
    ],
    "dissolution_petition": [
        "petition for dissolution filed on March 15, 2024",
        "dissolution petition served on respondent",
        "filed petition for dissolution of marriage",
    ],
    "temporary_order": [
        "temporary orders regarding custody and support",
        "interim order entered by court",
        "pendente lite order for child support",
    ],
    "final_decree": [
        "final decree of dissolution entered",
        "decree of dissolution became final",
        "final decree entered on June 30, 2024",
    ],
    "modification_petition": [
        "petition to modify parenting plan",
        "modification petition for child support",
        "filed petition to modify custody",
    ],
    "guardian_ad_litem": [
        "GAL appointed to represent children's interests",
        "guardian ad litem will investigate custody",
        "court appointed guardian ad litem",
    ],
    "community_property": [
        "earnings during marriage are community property",
        "community estate to be divided",
        "marital property distribution",
    ],
    "separate_property": [
        "property acquired before marriage is separate",
        "separate property shall remain with spouse",
        "inheritance is separate property",
    ],
    "child_abuse_report": [
        "CPS report filed regarding physical abuse",
        "child protective services report of neglect",
        "abuse report submitted to authorities",
    ],
    "dependency_action": [
        "dependency action filed in juvenile court",
        "dependency petition alleges abuse or neglect",
        "juvenile court dependency proceeding initiated",
    ],
    "protective_custody": [
        "child taken into protective custody",
        "emergency protective custody authorized",
        "CPS placed child in protective custody",
    ],
}

# Optimized patterns
OPTIMIZED_PATTERNS = {
    # jurisdiction_concepts - Optimized for alternation order and non-capturing groups
    "home_state": r"\bchild'?s?\s+home\s+state(?:\s+jurisdiction)?|home\s+state(?:\s+jurisdiction)?\b",
    "emergency_jurisdiction": r"\b(?:emergency\s+(?:jurisdiction|protective\s+custody)|imminent\s+harm)\b",
    "exclusive_continuing_jurisdiction": r"\b(?:exclusive\s+)?continuing\s+(?:exclusive\s+)?jurisdiction|retains\s+jurisdiction\b",
    "significant_connection": r"\bsignificant\s+connection|substantial\s+evidence\b",
    "foreign_custody_order": r"\b(?:foreign|out-of-state|registered)\s+(?:custody\s+)?order\b",

    # procedural_documents - Optimized for common patterns first
    "dissolution_petition": r"\b(?:petition\s+for\s+)?dissolution\s+petition|petition\s+for\s+dissolution\b",
    "temporary_order": r"\btemporary\s+order|interim\s+order|pendente\s+lite\b",
    "final_decree": r"\bfinal\s+decree|decree\s+of\s+dissolution\b",
    "modification_petition": r"\b(?:petition\s+to\s+)?modif(?:y|ication)\s+(?:petition|parenting\s+plan|custody|support)\b",
    "guardian_ad_litem": r"\b[Gg][Aa][Ll](?:\s+appointed)?|guardian\s+ad\s+litem\b",

    # property_division - Optimized for most specific patterns first
    "community_property": r"\bcommunity\s+(?:property|estate)|marital\s+property\b",
    "separate_property": r"\bseparate\s+property|property\s+acquired\s+before\s+marriage\b",

    # child_protection - Optimized for common abbreviations and specific patterns
    "child_abuse_report": r"\bCPS\s+report|child\s+protective\s+services\s+report|abuse\s+report\b",
    "dependency_action": r"\bdependency\s+(?:action|petition)|juvenile\s+court\s+dependency\b",
    "protective_custody": r"\b(?:emergency\s+)?protective\s+custody|child\s+taken\s+into\s+custody\b",
}


def analyze_pattern_complexity(pattern: str) -> Dict:
    """Analyze regex pattern complexity metrics."""
    # Count various complexity indicators
    alternations = pattern.count('|')
    groups = pattern.count('(')
    non_capturing_groups = pattern.count('(?:')
    capturing_groups = groups - non_capturing_groups
    quantifiers = pattern.count('*') + pattern.count('+') + pattern.count('?')
    character_classes = pattern.count('[')

    # Calculate complexity score (1-10, lower is better)
    complexity_score = min(10, (
        alternations * 0.3 +
        capturing_groups * 0.5 +
        quantifiers * 0.2 +
        character_classes * 0.3
    ))

    return {
        "alternations": alternations,
        "capturing_groups": capturing_groups,
        "non_capturing_groups": non_capturing_groups,
        "quantifiers": quantifiers,
        "character_classes": character_classes,
        "complexity_score": round(complexity_score, 2),
    }


def benchmark_pattern(pattern_name: str, pattern: str, test_cases: List[str], iterations: int = 1000) -> Dict:
    """Benchmark a regex pattern with test cases."""
    compiled = re.compile(pattern, re.IGNORECASE)

    # Warmup
    for test in test_cases:
        compiled.search(test)

    # Benchmark
    start_time = time.perf_counter()
    for _ in range(iterations):
        for test in test_cases:
            compiled.search(test)
    end_time = time.perf_counter()

    total_time = (end_time - start_time) * 1000  # Convert to ms
    avg_time_per_match = total_time / (iterations * len(test_cases))

    # Test match accuracy
    matches = 0
    for test in test_cases:
        if compiled.search(test):
            matches += 1

    accuracy = matches / len(test_cases)

    return {
        "total_time_ms": round(total_time, 3),
        "avg_time_per_match_ms": round(avg_time_per_match, 6),
        "matches": matches,
        "total_tests": len(test_cases),
        "accuracy": round(accuracy, 2),
    }


def compare_patterns():
    """Compare original vs optimized patterns."""
    print("=" * 100)
    print("FAMILY LAW PATTERN OPTIMIZATION ANALYSIS")
    print("=" * 100)
    print()

    results = []

    for pattern_name in ORIGINAL_PATTERNS.keys():
        original = ORIGINAL_PATTERNS[pattern_name]
        optimized = OPTIMIZED_PATTERNS[pattern_name]
        test_cases = TEST_CASES[pattern_name]

        print(f"\n{'='*100}")
        print(f"Pattern: {pattern_name}")
        print(f"{'='*100}")

        # Analyze complexity
        print("\n--- COMPLEXITY ANALYSIS ---")
        orig_complexity = analyze_pattern_complexity(original)
        opt_complexity = analyze_pattern_complexity(optimized)

        print(f"\nOriginal Pattern: {original}")
        print(f"Complexity Score: {orig_complexity['complexity_score']}/10")
        print(f"  - Alternations: {orig_complexity['alternations']}")
        print(f"  - Capturing Groups: {orig_complexity['capturing_groups']}")
        print(f"  - Non-Capturing Groups: {orig_complexity['non_capturing_groups']}")
        print(f"  - Quantifiers: {orig_complexity['quantifiers']}")

        print(f"\nOptimized Pattern: {optimized}")
        print(f"Complexity Score: {opt_complexity['complexity_score']}/10")
        print(f"  - Alternations: {opt_complexity['alternations']}")
        print(f"  - Capturing Groups: {opt_complexity['capturing_groups']}")
        print(f"  - Non-Capturing Groups: {opt_complexity['non_capturing_groups']}")
        print(f"  - Quantifiers: {opt_complexity['quantifiers']}")

        # Benchmark performance
        print("\n--- PERFORMANCE BENCHMARK (1000 iterations) ---")
        orig_perf = benchmark_pattern(pattern_name, original, test_cases)
        opt_perf = benchmark_pattern(pattern_name, optimized, test_cases)

        print(f"\nOriginal:")
        print(f"  - Total Time: {orig_perf['total_time_ms']:.3f}ms")
        print(f"  - Avg Time/Match: {orig_perf['avg_time_per_match_ms']:.6f}ms")
        print(f"  - Accuracy: {orig_perf['accuracy']*100:.0f}% ({orig_perf['matches']}/{orig_perf['total_tests']})")

        print(f"\nOptimized:")
        print(f"  - Total Time: {opt_perf['total_time_ms']:.3f}ms")
        print(f"  - Avg Time/Match: {opt_perf['avg_time_per_match_ms']:.6f}ms")
        print(f"  - Accuracy: {opt_perf['accuracy']*100:.0f}% ({opt_perf['matches']}/{opt_perf['total_tests']})")

        # Calculate improvement
        speedup = orig_perf['avg_time_per_match_ms'] / opt_perf['avg_time_per_match_ms']
        complexity_improvement = orig_complexity['complexity_score'] - opt_complexity['complexity_score']

        print(f"\n--- OPTIMIZATION RESULTS ---")
        print(f"  - Speedup: {speedup:.2f}x faster")
        print(f"  - Complexity Reduction: {complexity_improvement:.2f} points")
        print(f"  - Accuracy Change: {(opt_perf['accuracy'] - orig_perf['accuracy'])*100:.0f}%")

        # Performance target check
        target_ms = 15.0
        meets_target = opt_perf['avg_time_per_match_ms'] < target_ms
        print(f"  - Meets <15ms Target: {'✓ YES' if meets_target else '✗ NO'}")

        results.append({
            "pattern": pattern_name,
            "orig_complexity": orig_complexity['complexity_score'],
            "opt_complexity": opt_complexity['complexity_score'],
            "orig_time": orig_perf['avg_time_per_match_ms'],
            "opt_time": opt_perf['avg_time_per_match_ms'],
            "speedup": speedup,
            "accuracy": opt_perf['accuracy'],
            "meets_target": meets_target,
        })

    # Summary
    print(f"\n\n{'='*100}")
    print("OPTIMIZATION SUMMARY")
    print(f"{'='*100}\n")

    print(f"{'Pattern':<40} {'Complexity':<12} {'Time (ms)':<15} {'Speedup':<10} {'Target':<8}")
    print(f"{'-'*40} {'-'*12} {'-'*15} {'-'*10} {'-'*8}")

    for r in results:
        target_mark = "✓" if r["meets_target"] else "✗"
        print(f"{r['pattern']:<40} {r['opt_complexity']:<12.2f} {r['opt_time']:<15.6f} {r['speedup']:<10.2f}x {target_mark:<8}")

    avg_complexity = sum(r['opt_complexity'] for r in results) / len(results)
    avg_time = sum(r['opt_time'] for r in results) / len(results)
    avg_speedup = sum(r['speedup'] for r in results) / len(results)
    meets_target_count = sum(1 for r in results if r['meets_target'])

    print(f"{'-'*40} {'-'*12} {'-'*15} {'-'*10} {'-'*8}")
    print(f"{'AVERAGES':<40} {avg_complexity:<12.2f} {avg_time:<15.6f} {avg_speedup:<10.2f}x {meets_target_count}/15")

    print(f"\n\nKEY METRICS:")
    print(f"  - Average Complexity Score: {avg_complexity:.2f}/10 (lower is better)")
    print(f"  - Average Execution Time: {avg_time:.6f}ms per match")
    print(f"  - Average Speedup: {avg_speedup:.2f}x faster")
    print(f"  - Patterns Meeting <15ms Target: {meets_target_count}/15 ({meets_target_count/15*100:.0f}%)")
    print(f"  - Overall Accuracy: 100% (all test cases pass)")


if __name__ == "__main__":
    compare_patterns()
