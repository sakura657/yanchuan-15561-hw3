"""Rebuild the database, analyses, figures and webpage.

Usage: ``python run_all.py``
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = [
    "src/build_db.py",          # data/northwind.db + output/data_summary.json
    "src/q1_markets.py",        # output/q1_*, docs/figures/q1_*
    "src/q2_concentration.py",  # output/q2_*, docs/figures/q2_*
    "src/q3_shipping.py",       # output/q3_*, docs/figures/q3_*
    "src/build_site.py",        # docs/index.html
]


def main():
    """Run each pipeline step in order, stopping at the first failure.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: If a step exits with a non-zero code.
    """
    for step in STEPS:
        print(f"\n=== {step} ===", flush=True)
        result = subprocess.run([sys.executable, str(ROOT / step)], cwd=ROOT)
        if result.returncode != 0:
            sys.exit(f"\nrun_all: {step} failed (exit {result.returncode}); stopping.")
    print("\nrun_all: done. Open docs/index.html to view the page.")


if __name__ == "__main__":
    main()
