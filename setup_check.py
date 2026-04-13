"""
setup_check.py — ICAF standalone pre-flight checker
────────────────────────────────────────────────────
Run this before using ICAF on any new machine to verify and optionally
install all required system and Python dependencies.

Usage:
    python setup_check.py          # check only — no changes made
    python setup_check.py --fix    # check and auto-install missing items
"""

import sys
import os

# Allow running from the project root before the package is installed
sys.path.insert(0, os.path.dirname(__file__))

from icaf.cli.preflight import run_preflight, print_report

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="setup_check.py",
        description="ICAF pre-flight dependency checker and auto-installer."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-install missing system packages (apt) and Python packages (pip). "
             "Some steps require sudo."
    )
    args = parser.parse_args()

    report = run_preflight(auto_fix=args.fix)
    print_report(report)
    sys.exit(0 if report.passed else 1)