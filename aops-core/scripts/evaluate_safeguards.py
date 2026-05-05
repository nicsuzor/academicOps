#!/usr/bin/env -S uv run python
"""
Observability Metrics Evaluator

This script parses existing session insights JSON files to calculate metrics like
Guardrail ROI, Intervention Rate, and Friction Tool Heatmaps.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

# Add framework roots to path
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.paths import get_summaries_dir


def load_insights_files():
    summaries_dir = get_summaries_dir()
    insights = []
    if summaries_dir.exists():
        for path in summaries_dir.glob("*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                    insights.append(data)
            except Exception as e:
                print(f"Failed to load {path}: {e}")
    return insights


def generate_report(insights):
    total_sessions = len(insights)
    if total_sessions == 0:
        return "No insights data found to generate report."

    outcomes = defaultdict(int)
    total_tokens = 0
    friction_points = []
    tool_usage = defaultdict(lambda: {"count": 0, "input_tokens": 0, "output_tokens": 0})
    success_tool_usage = defaultdict(lambda: {"count": 0, "input_tokens": 0, "output_tokens": 0})
    failure_tool_usage = defaultdict(lambda: {"count": 0, "input_tokens": 0, "output_tokens": 0})

    for session in insights:
        outcome = session.get("outcome", "unknown")
        outcomes[outcome] += 1

        metrics = session.get("token_metrics") or {}
        totals = metrics.get("totals") or {}
        input_t = totals.get("input_tokens") or 0
        output_t = totals.get("output_tokens") or 0
        total_tokens += input_t + output_t

        by_tool = metrics.get("by_tool") or {}
        for tool, stats in by_tool.items():
            stats = stats or {}
            tool_usage[tool]["count"] += stats.get("count") or 0
            tool_usage[tool]["input_tokens"] += stats.get("input") or 0
            tool_usage[tool]["output_tokens"] += stats.get("output") or 0

            if outcome == "success":
                success_tool_usage[tool]["count"] += stats.get("count") or 0
            elif outcome in ("failure", "partial"):
                failure_tool_usage[tool]["count"] += stats.get("count") or 0

        refs = session.get("framework_reflections") or []
        for ref in refs:
            f_points = (ref or {}).get("friction_points") or []
            friction_points.extend(f_points)

    report = ["# AcademicOps Safeguards Evaluation Report\n"]
    report.append(f"**Total Sessions Evaluated:** {total_sessions}")
    report.append(f"**Total Tokens Processed:** {total_tokens:,}\n")

    report.append("## Outcomes Overview")
    for out, count in outcomes.items():
        report.append(f"- **{out.capitalize()}:** {count} ({(count / total_sessions) * 100:.1f}%)")
    report.append("")

    report.append("## Tool ROI (Tokens per Outcome)")
    report.append("| Tool | Total Calls | Total Input Tokens | Success Rate | Avg Tokens/Success |")
    report.append("|---|---|---|---|---|")

    for tool, usage in sorted(tool_usage.items(), key=lambda x: x[1]["input_tokens"], reverse=True)[
        :15
    ]:
        calls = usage["count"]
        tokens = usage["input_tokens"]
        successes = success_tool_usage[tool]["count"]
        success_rate = (successes / calls * 100) if calls > 0 else 0
        avg_success_tokens = tokens / successes if successes > 0 else float("inf")

        avg_tokens_str = (
            f"{avg_success_tokens:,.0f}" if avg_success_tokens != float("inf") else "N/A"
        )

        report.append(f"| {tool} | {calls} | {tokens:,} | {success_rate:.1f}% | {avg_tokens_str} |")
    report.append("")

    report.append("## Extracted Friction Points")
    if friction_points:
        for fp in friction_points[:20]:  # Top 20 points
            report.append(f"- {fp}")
    else:
        report.append("- No friction points documented.")

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Evaluate AcademicOps safeguards and tool ROI")
    parser.add_argument("-o", "--output", help="Output markdown file path")
    args = parser.parse_args()

    print("Loading insights...")
    insights = load_insights_files()

    print("Generating report...")
    report_md = generate_report(insights)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report_md)
        print(f"Report written to {args.output}")
    else:
        print("\n" + "=" * 50 + "\n")
        print(report_md)
        print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    main()
