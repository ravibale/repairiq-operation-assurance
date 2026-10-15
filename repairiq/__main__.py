"""Command line interface: python -m repairiq examples/sample_estimate.csv"""
import argparse
from pathlib import Path
from .core import create_report, to_json

def main() -> None:
    parser = argparse.ArgumentParser(description="Experimental RepairIQ labour overlap review")
    parser.add_argument("csv", type=Path, help="CSV estimate file")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()
    report = to_json(create_report(args.csv))
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(report)

if __name__ == "__main__":
    main()
