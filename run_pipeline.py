"""
Run the full pipeline: ingest → detect → dashboard.

Usage:
    python run_pipeline.py          # ingest + launch dashboard
    python run_pipeline.py --ingest # ingest only
    python run_pipeline.py --dash   # dashboard only (skip ingest)
"""

import argparse
import subprocess
import sys
import os

ROOT = os.path.dirname(__file__)


def run_ingest():
    print("=" * 60)
    print("STEP 1: Ingesting market data...")
    print("=" * 60)
    subprocess.run([sys.executable, "-m", "data.ingest_market"], cwd=ROOT, check=True)

    print("\n" + "=" * 60)
    print("STEP 2: Ingesting news data...")
    print("=" * 60)
    subprocess.run([sys.executable, "-m", "data.ingest_news"], cwd=ROOT, check=True)


def run_dashboard():
    print("\n" + "=" * 60)
    print("STEP 3: Launching dashboard...")
    print("=" * 60)
    subprocess.run(["streamlit", "run", "dashboard/app.py"], cwd=ROOT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingest", action="store_true", help="Run ingest only")
    parser.add_argument("--dash", action="store_true", help="Run dashboard only")
    args = parser.parse_args()

    if args.ingest:
        run_ingest()
    elif args.dash:
        run_dashboard()
    else:
        run_ingest()
        run_dashboard()
