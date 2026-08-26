from __future__ import annotations

import argparse
from pathlib import Path

from dusty_dragon.qc.local import run_qc


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Dusty Dragon local QC gates.")
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install the repository with development dependencies before QC.",
    )
    args = parser.parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    return run_qc(repository_root=repository_root, install=args.install)


if __name__ == "__main__":
    raise SystemExit(main())
