#!/usr/bin/env python3
"""
Family Law Pattern Optimization Script V2
True optimization focusing on real performance improvements.
"""

import re
import time
from typing import Dict, List

# TRULY OPTIMIZED patterns based on performance best practices
FINAL_OPTIMIZED_PATTERNS = {
    # jurisdiction_concepts (5 patterns)
    # Optimization: Remove unnecessary non-capturing groups, order alternations by frequency
    "home_state": r"\bhome\s+state(?:\s+jurisdiction)?|child'?s?\s+home\s+state\b",

    # Optimization: Nested alternation for common prefix "emergency"
    "emergency_jurisdiction": r"\bemergency\s+(?:jurisdiction|protective\s+custody)|imminent\s+harm\b",

    # Optimization: Optional patterns to handle variations, one alternation
    "exclusive_continuing_jurisdiction": r"\b(?:exclusive\s+)?continuing\s+(?:exclusive\s+)?jurisdiction|retains\s+jurisdiction\b",

    # Optimization: Remove unnecessary group, simple alternation
    "significant_connection": r"\bsignificant\s+connection|substantial\s+evidence\b",

    # Optimization: Factor out common "order" suffix
    "foreign_custody_order": r"\b(?:foreign\s+custody|out-of-state|registered)\s+order\b",

    # procedural_documents (5 patterns)
    # Optimization: Order most common first, remove unnecessary grouping
    "dissolution_petition": r"\bdissolution\s+petition|petition\s+for\s+dissolution\b",

    # Optimization: Order by frequency (temporary most common)
    "temporary_order": r"\btemporary\s+order|interim\s+order|pendente\s+lite\b",

    # Optimization: Simple alternation, no grouping needed
    "final_decree": r"\bfinal\s+decree|decree\s+of\s+dissolution\b",

    # Optimization: Keep original - already optimal
    "modification_petition": r"\bpetition\s+to\s+modify|modification\s+petition\b",

    # Optimization: Case-insensitive inline flag for GAL, order abbreviation first
    "guardian_ad_litem": r"\b(?i:GAL)(?:\s+appointed)?|guardian\s+ad\s+litem\b",

    # property_division (2 patterns)
    # Optimization: Factor common "community" prefix
    "community_property": r"\bcommunity\s+(?:property|estate)|marital\s+property\b",

    # Optimization: Remove unnecessary group
    "separate_property": r"\bseparate\s+property|property\s+acquired\s+before\s+marriage\b",

    # child_protection (3 patterns)
    # Optimization: Order by frequency (CPS abbreviation first)
    "child_abuse_report": r"\bCPS\s+report|abuse\s+report|child\s+protective\s+services\s+report\b",

    # Optimization: Factor common "dependency" prefix
    "dependency_action": r"\bdependency\s+(?:action|petition)|juvenile\s+court\s+dependency\b",

    # Optimization: Factor common "custody" suffix, optional "emergency" prefix
    "protective_custody": r"\b(?:emergency\s+)?protective\s+custody|child\s+taken\s+into\s+custody\b",
}

# Original patterns for comparison
ORIGINAL_PATTERNS = {
    "home_state": r"\b(?:home\s+state|child(?:'s|'s)?\s+home\s+state|home\s+state\s+jurisdiction)",
    "emergency_jurisdiction": r"\b(?:emergency\s+jurisdiction|imminent\s+harm|emergency\s+protective\s+custody)",
    "exclusive_continuing_jurisdiction": r"\b(?:exclusive\s+continuing\s+jurisdiction|retains\s+jurisdiction|continuing\s+exclusive\s+jurisdiction)",
    "significant_connection": r"\b(?:significant\s+connection|substantial\s+evidence)",
    "foreign_custody_order": r"\b(?:foreign\s+custody\s+order|out-of-state\s+order|registered\s+order)",
    "dissolution_petition": r"\b(?:petition\s+for\s+dissolution|dissolution\s+petition)",
    "temporary_order": r"\b(?:temporary\s+order|interim\s+order|pendente\s+lite)",
    "final_decree": r"\b(?:final\s+decree|decree\s+of\s+dissolution)",
    "modification_petition": r"\b(?:petition\s+to\s+modify|modification\s+petition)",
    "guardian_ad_litem": r"\b(?:guardian\s+ad\s+litem|GAL\s+appointed)",
    "community_property": r"\b(?:community\s+property|community\s+estate|marital\s+property)",
    "separate_property": r"\b(?:separate\s+property|property\s+acquired\s+before\s+marriage)",
    "child_abuse_report": r"\b(?:CPS\s+report|child\s+protective\s+services\s+report|abuse\s+report)",
    "dependency_action": r"\b(?:dependency\s+action|dependency\s+petition|juvenile\s+court\s+dependency)",
    "protective_custody": r"\b(?:protective\s+custody|emergency\s+protective\s+custody|child\s+taken\s+into\s+custody)",
}

# Extended test cases including edge cases and variations
TEST_CASES = {
    "home_state": [
        "California is the child's home state",
        "home state jurisdiction under the UCCJEA",
        "child's home state is Washington",
        "Washington has home state jurisdiction",
        "home state for custody purposes",
        "children's home state determination",
    ],
    "emergency_jurisdiction": [
        "emergency jurisdiction exercised due to imminent harm",
        "emergency protective custody jurisdiction",
        "imminent harm to child requires emergency jurisdiction",
        "court exercised emergency jurisdiction",
        "emergency protective custody was necessary",
    ],
    "exclusive_continuing_jurisdiction": [
        "Washington retains exclusive continuing jurisdiction",
        "exclusive continuing jurisdiction over custody matters",
        "continuing exclusive jurisdiction established",
        "court retains jurisdiction",
        "state has exclusive continuing jurisdiction",
    ],
    "significant_connection": [
        "child has significant connections to Washington",
        "substantial evidence of connection to state",
        "substantial evidence supports jurisdiction",
        "significant connection jurisdiction basis",
    ],
    "foreign_custody_order": [
        "Nevada custody order registered in Washington",
        "foreign custody order from California",
        "out-of-state order recognition requested",
        "registered order from Oregon",
        "enforcement of foreign custody order",
    ],
    "dissolution_petition": [
        "petition for dissolution filed on March 15, 2024",
        "dissolution petition served on respondent",
        "filed petition for dissolution of marriage",
        "dissolution petition initiates proceedings",
    ],
    "temporary_order": [
        "temporary orders regarding custody and support",
        "interim order entered by court",
        "pendente lite order for child support",
        "court issued temporary orders",
        "temporary order pending final decree",
    ],
    "final_decree": [
        "final decree of dissolution entered",
        "decree of dissolution became final",
        "final decree entered on June 30, 2024",
        "final decree terminates marriage",
    ],
    "modification_petition": [
        "petition to modify parenting plan",
        "modification petition for child support",
        "filed petition to modify custody",
        "petition to modify spousal maintenance",
    ],
    "guardian_ad_litem": [
        "GAL appointed to represent children's interests",
        "guardian ad litem will investigate custody",
        "court appointed guardian ad litem",
        "GAL report submitted",
        "gal recommendation supports mother",
        "Guardian Ad Litem appointed by judge",
    ],
    "community_property": [
        "earnings during marriage are community property",
        "community estate to be divided",
        "marital property distribution",
        "all community property divided equally",
    ],
    "separate_property": [
        "property acquired before marriage is separate",
        "separate property shall remain with spouse",
        "inheritance is separate property",
        "property acquired by gift remains separate",
    ],
    "child_abuse_report": [
        "CPS report filed regarding physical abuse",
        "child protective services report of neglect",
        "abuse report submitted to authorities",
        "CPS investigated allegations",
    ],
    "dependency_action": [
        "dependency action filed in juvenile court",
        "dependency petition alleges abuse or neglect",
        "juvenile court dependency proceeding initiated",
        "court found dependency",
    ],
    "protective_custody": [
        "child taken into protective custody",
        "emergency protective custody authorized",
        "CPS placed child in protective custody",
        "protective custody pending investigation",
    ],
}

def benchmark_with_large_text(pattern_name: str, pattern: str, iterations: int = 100) -> Dict:
    """Benchmark pattern with realistic large legal document text."""
    # Simulate a large family law document (5000 words)
    large_text = """
    In the Matter of the Marriage of Smith and Jones

    DECLARATION OF PETITIONER

    I, Jane Smith, declare under penalty of perjury that the following is true and correct:

    1. JURISDICTION: California is the child's home state pursuant to the UCCJEA. The minor children, Emma Smith and Noah Smith,
    have resided in California for more than six months prior to the commencement of this action. Washington has home state
    jurisdiction over custody matters. The court has exclusive continuing jurisdiction over this case.

    2. CUSTODY: I request joint legal custody of the minor children with sole physical custody awarded to me. The children
    have resided primarily with me since our separation. I am a fit parent capable of providing a stable home environment.

    3. VISITATION: Father shall have visitation every other weekend from Friday at 6:00 PM to Sunday at 6:00 PM.
    Holiday visitation shall alternate annually. Supervised visitation may be necessary initially due to domestic violence
    concerns. Overnight visitation can be phased in gradually.

    4. CHILD SUPPORT: Based on Father's gross income of $85,000 per year and my income of $45,000 per year, child support
    should be $1,500 per month. Child care costs of $800 per month should be shared proportionally. Medical expenses total
    approximately $200 per month for health insurance premiums.

    5. SPOUSAL SUPPORT: I request spousal support of $1,200 per month for a period of five years to allow me to complete
    my education and become self-supporting.

    6. PARENTING PLAN: The parties should have joint decision-making authority regarding education and medical care.
    Communication between parents shall be through email or the OurFamilyWizard app. Any relocation shall require
    60 days written notice and court approval. Dispute resolution through mediation shall be required before filing
    any modification petition.

    7. BEST INTERESTS FACTORS: The children have expressed a preference to remain in their current school and live
    primarily with me. I have maintained a stable home environment throughout our marriage and separation. Father has
    a history of substance abuse and has attended rehabilitation programs. A custody evaluation was completed by
    Dr. Johnson in March 2024.

    8. DOMESTIC VIOLENCE: There is a history of domestic violence in our relationship. A restraining order was issued
    in January 2024. These protective orders remain in effect. A guardian ad litem was appointed to represent the
    children's interests in this matter.

    9. PROPERTY DIVISION: All community property acquired during our marriage should be divided equally, including
    our family home, retirement accounts, and vehicles. My separate property includes an inheritance received from
    my grandmother in 2020. Property acquired before marriage should remain separate property.

    10. PROCEDURAL HISTORY: A petition for dissolution of marriage was filed on January 15, 2024. Temporary orders
    regarding custody and support were entered on February 20, 2024. A modification petition was filed in May 2024
    seeking increased child support. The final decree of dissolution is pending.

    11. CHILD PROTECTION CONCERNS: A CPS report was filed in December 2023 regarding allegations of neglect.
    Child protective services investigated but did not substantiate the abuse report. No dependency action was
    filed. The children were never placed in protective custody or emergency protective custody.

    12. EMPLOYMENT: I am employed as a Registered Nurse at ABC Hospital. My work schedule is typically 7:00 AM to
    3:30 PM, three days per week. Father works as a Sales Manager at XYZ Corporation with an annual income of $85,000.

    13. CHILDREN: The minor children are Emma Smith, age 8, born March 15, 2015, and Noah Smith, age 5, DOB: June 22, 2018.

    14. UCCJEA COMPLIANCE: This court has jurisdiction under the UCCJEA as California is the home state. No foreign custody
    orders exist. No other state has continuing jurisdiction. There is substantial evidence of significant connections to
    California. Emergency jurisdiction is not applicable in this case.

    15. REQUESTED RELIEF: I request the court enter a final decree of dissolution dissolving our marriage. I request
    the court approve the parenting plan as proposed. A guardian ad litem report supports these requests. The income and
    expense declaration FL-150 has been filed. All community property should be divided equally, and separate property
    confirmed as such.

    """ * 3  # Repeat 3 times to create ~5000 word document

    compiled = re.compile(pattern, re.IGNORECASE)

    # Warmup
    for _ in range(10):
        matches = list(compiled.finditer(large_text))

    # Benchmark
    start_time = time.perf_counter()
    for _ in range(iterations):
        matches = list(compiled.finditer(large_text))
    end_time = time.perf_counter()

    total_time = (end_time - start_time) * 1000  # Convert to ms
    avg_time = total_time / iterations

    # Count matches in one pass
    final_matches = list(compiled.finditer(large_text))

    return {
        "total_time_ms": round(total_time, 3),
        "avg_time_ms": round(avg_time, 3),
        "matches_found": len(final_matches),
        "text_length": len(large_text),
    }


def generate_optimization_report():
    """Generate comprehensive optimization report."""
    print("=" * 120)
    print("FAMILY LAW PATTERN OPTIMIZATION - FINAL REPORT")
    print("=" * 120)
    print("\nTarget: <15ms per pattern execution on realistic legal documents")
    print("=" * 120)

    results = []

    for pattern_name in ORIGINAL_PATTERNS.keys():
        original = ORIGINAL_PATTERNS[pattern_name]
        optimized = FINAL_OPTIMIZED_PATTERNS[pattern_name]

        print(f"\n{'='*120}")
        print(f"Pattern: {pattern_name}")
        print(f"{'='*120}")

        print(f"\nOriginal:  {original}")
        print(f"Optimized: {optimized}")

        # Test accuracy with all test cases
        print("\n--- ACCURACY TEST ---")
        orig_compiled = re.compile(original, re.IGNORECASE)
        opt_compiled = re.compile(optimized, re.IGNORECASE)

        test_cases = TEST_CASES[pattern_name]
        orig_matches = sum(1 for t in test_cases if orig_compiled.search(t))
        opt_matches = sum(1 for t in test_cases if opt_compiled.search(t))

        print(f"Original Matches: {orig_matches}/{len(test_cases)}")
        print(f"Optimized Matches: {opt_matches}/{len(test_cases)}")
        print(f"Accuracy: {'✓ PASS' if opt_matches == orig_matches else '✗ FAIL'}")

        # Benchmark on large document
        print("\n--- PERFORMANCE BENCHMARK (Large Document ~5000 words, 100 iterations) ---")
        orig_perf = benchmark_with_large_text(pattern_name, original)
        opt_perf = benchmark_with_large_text(pattern_name, optimized)

        print(f"\nOriginal:")
        print(f"  Average Time: {orig_perf['avg_time_ms']:.3f}ms")
        print(f"  Matches Found: {orig_perf['matches_found']}")

        print(f"\nOptimized:")
        print(f"  Average Time: {opt_perf['avg_time_ms']:.3f}ms")
        print(f"  Matches Found: {opt_perf['matches_found']}")

        improvement = ((orig_perf['avg_time_ms'] - opt_perf['avg_time_ms']) / orig_perf['avg_time_ms']) * 100
        speedup = orig_perf['avg_time_ms'] / opt_perf['avg_time_ms']

        print(f"\n--- RESULTS ---")
        print(f"  Performance: {improvement:+.1f}% ({speedup:.2f}x)")
        print(f"  Meets <15ms Target: {'✓ YES' if opt_perf['avg_time_ms'] < 15 else '✗ NO'}")
        print(f"  Match Count: {'✓ SAME' if opt_perf['matches_found'] == orig_perf['matches_found'] else '✗ DIFFERENT'}")

        results.append({
            "pattern": pattern_name,
            "orig_time": orig_perf['avg_time_ms'],
            "opt_time": opt_perf['avg_time_ms'],
            "improvement_pct": improvement,
            "speedup": speedup,
            "meets_target": opt_perf['avg_time_ms'] < 15,
            "accuracy": opt_matches == orig_matches,
        })

    # Summary table
    print(f"\n\n{'='*120}")
    print("OPTIMIZATION SUMMARY")
    print(f"{'='*120}\n")

    print(f"{'Pattern':<35} {'Original (ms)':<15} {'Optimized (ms)':<15} {'Improvement':<15} {'Target':<10}")
    print(f"{'-'*35} {'-'*15} {'-'*15} {'-'*15} {'-'*10}")

    for r in results:
        target_mark = "✓" if r["meets_target"] else "✗"
        print(f"{r['pattern']:<35} {r['orig_time']:<15.3f} {r['opt_time']:<15.3f} {r['improvement_pct']:>+6.1f}% ({r['speedup']:.2f}x) {target_mark:<10}")

    avg_orig = sum(r['orig_time'] for r in results) / len(results)
    avg_opt = sum(r['opt_time'] for r in results) / len(results)
    avg_improvement = ((avg_orig - avg_opt) / avg_orig) * 100
    avg_speedup = avg_orig / avg_opt
    meets_target_count = sum(1 for r in results if r['meets_target'])
    accuracy_count = sum(1 for r in results if r['accuracy'])

    print(f"{'-'*35} {'-'*15} {'-'*15} {'-'*15} {'-'*10}")
    print(f"{'AVERAGES':<35} {avg_orig:<15.3f} {avg_opt:<15.3f} {avg_improvement:>+6.1f}% ({avg_speedup:.2f}x) {meets_target_count}/15")

    print(f"\n\nKEY METRICS:")
    print(f"  • Average Original Time: {avg_orig:.3f}ms")
    print(f"  • Average Optimized Time: {avg_opt:.3f}ms")
    print(f"  • Average Improvement: {avg_improvement:+.1f}%")
    print(f"  • Average Speedup: {avg_speedup:.2f}x")
    print(f"  • Patterns Meeting <15ms Target: {meets_target_count}/15 ({meets_target_count/15*100:.0f}%)")
    print(f"  • Patterns Maintaining Accuracy: {accuracy_count}/15 ({accuracy_count/15*100:.0f}%)")

    print(f"\n\nOPTIMIZATION TECHNIQUES APPLIED:")
    print(f"  1. Removed unnecessary non-capturing groups where not needed for alternations")
    print(f"  2. Ordered alternations by frequency (most common patterns first)")
    print(f"  3. Factored out common prefixes/suffixes to reduce repetition")
    print(f"  4. Used inline case-insensitive flags for specific terms (GAL)")
    print(f"  5. Simplified patterns while maintaining accuracy")
    print(f"  6. Avoided nested quantifiers and potential backtracking scenarios")


if __name__ == "__main__":
    generate_optimization_report()
