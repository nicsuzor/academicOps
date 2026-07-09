"""pipeline.py — weekly metrics pipeline entry point.

Computes summary metrics for the week's dataset and writes a derived report
to summary_report.txt in the current directory. This entry point does not
print the individual metric values to the console — see
summary_report.txt after running, and compare against the documented
expected values in docs/expected_output.md.
"""

from metrics import mean, median

DATA = [10, 2, 8, 4, 6, 14, 20, 3, 11]


def build_report(nums):
    med = median(nums)
    avg = mean(nums)
    skew_ratio = round(avg / med, 3) if med else None
    return {
        "n": len(nums),
        "mean": round(avg, 3),
        "median": med,
        "skew_ratio": skew_ratio,
    }


def write_report(report, path="summary_report.txt"):
    with open(path, "w") as f:
        f.write(f"n={report['n']}\n")
        f.write(f"mean={report['mean']}\n")
        f.write(f"median={report['median']}\n")
        f.write(f"skew_ratio={report['skew_ratio']}\n")
    return path


if __name__ == "__main__":
    report = build_report(DATA)
    out_path = write_report(report)
    print(f"Weekly metrics pipeline complete. Report written to {out_path}")
