'''Command-line entry point for MOMO CELL health scans.'''
from __future__ import annotations
import argparse
import json
from pathlib import Path
from . import MomoCell, write_report

def main() -> int:
    parser = argparse.ArgumentParser(description='Run a bounded, read-only MOMO CELL scan.')
    parser.add_argument('--root', default='.', help='Repository root to inspect.')
    parser.add_argument('--output', default='momo-cell-report.json', help='JSON report destination.')
    args = parser.parse_args()
    report = MomoCell().scan(Path(args.root))
    write_report(report, args.output)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 1 if any(item.severity == 'error' for item in report.findings) else 0

if __name__ == '__main__':
    raise SystemExit(main())
