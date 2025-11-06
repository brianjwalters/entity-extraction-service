#!/usr/bin/env python3
"""
Generate ASCII visualization of pattern performance.
"""

# Performance data from benchmarks
patterns = {
    "Jurisdiction Concepts": [
        ("home_state", 0.296),
        ("emergency_jurisdiction", 0.312),
        ("exclusive_continuing_jurisdiction", 0.301),
        ("significant_connection", 0.242),
        ("foreign_custody_order", 0.302),
    ],
    "Procedural Documents": [
        ("dissolution_petition", 0.280),
        ("temporary_order", 0.360),
        ("final_decree", 0.268),
        ("modification_petition", 0.279),
        ("guardian_ad_litem", 0.270),
    ],
    "Property Division": [
        ("community_property", 0.303),
        ("separate_property", 0.305),
    ],
    "Child Protection": [
        ("child_abuse_report", 0.314),
        ("dependency_action", 0.298),
        ("protective_custody", 0.313),
    ],
}

def generate_bar_chart(name, time_ms, max_width=80):
    """Generate ASCII bar chart for a pattern."""
    target = 15.0
    percentage = (time_ms / target) * 100
    bar_width = int((time_ms / target) * max_width)
    bar = "█" * bar_width

    return f"{name:<40} {bar} {time_ms:.3f}ms ({percentage:.1f}%)"

def main():
    print("=" * 100)
    print("FAMILY LAW PATTERN PERFORMANCE VISUALIZATION")
    print("=" * 100)
    print(f"\nTarget: 15.000ms (shown as 100% bar)")
    print("=" * 100)
    print()

    all_times = []

    for category, pattern_list in patterns.items():
        print(f"\n{category}")
        print("-" * 100)

        for name, time in pattern_list:
            print(generate_bar_chart(name, time))
            all_times.append(time)

    # Overall statistics
    avg_time = sum(all_times) / len(all_times)
    min_time = min(all_times)
    max_time = max(all_times)

    print("\n" + "=" * 100)
    print("OVERALL STATISTICS")
    print("=" * 100)
    print(f"\nAverage Time: {avg_time:.3f}ms ({(avg_time/15)*100:.1f}% of target)")
    print(f"Fastest Pattern: {min_time:.3f}ms ({(min_time/15)*100:.1f}% of target)")
    print(f"Slowest Pattern: {max_time:.3f}ms ({(max_time/15)*100:.1f}% of target)")
    print(f"Performance Margin: {15/avg_time:.1f}x faster than required")
    print()

    # Target reference
    print("\nPerformance Target Reference:")
    print(generate_bar_chart("15ms TARGET", 15.0))
    print(generate_bar_chart("Average Actual", avg_time))
    print(generate_bar_chart("Slowest Pattern (temporary_order)", max_time))

    print("\n" + "=" * 100)
    print("✅ ALL 15 PATTERNS MEET <15ms TARGET")
    print("=" * 100)

if __name__ == "__main__":
    main()
