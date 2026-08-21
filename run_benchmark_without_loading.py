#!/usr/bin/env python3
"""
Testing entry point for the benchmark pipeline (LOADING DISABLED):

    python run_test_benchmark.py

Pipeline stages (each can be skipped with a flag):
  1. install   -> pip install -r requirements.txt (Skipped if already installed)
  2. dataset   -> scripts/download_and_process_dataset.py (Skipped if dataset exists)
  3. workloads -> scripts/run_all_workloads.py

Credentials are read from `.env` (copy `.env.example` -> `.env` and fill in
whichever databases you actually have running; scripts skip any DB whose
env vars are missing).

Flags:
  --skip-install      skip `pip install -r requirements.txt`
  --skip-dataset      skip dataset download/processing
  --skip-workloads    skip running the workload/concurrency/footprint suite
  --force-dataset     re-download and rebuild datasets/*.csv even if they exist
  --only STAGE        run a single stage only (install|dataset|workloads)
"""

import argparse
import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def banner(title: str) -> None:
    print(f"\n{'#' * 70}")
    print(f"# {title}")
    print(f"{'#' * 70}\n")


def run(cmd, cwd=BASE_DIR):
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"\n❌ Command failed with exit code {result.returncode}: {' '.join(cmd)}")
        sys.exit(result.returncode)


def stage_install():
    banner("STAGE 1/3 — Installing dependencies")
    # Smart check: Only run pip install if core packages are missing
    try:
        import pandas
        import neo4j
        import arango
        import falkordb
        print("✅ Core dependencies already installed. Skipping pip install.")
        return
    except ImportError:
        print("⏳ Missing dependencies detected. Installing...")

    req_file = os.path.join(BASE_DIR, "requirements.txt")
    run([sys.executable, "-m", "pip", "install", "-r", req_file])


def stage_dataset(force: bool):
    banner("STAGE 2/3 — Downloading & processing dataset")
    nodes_path = os.path.join(BASE_DIR, "datasets", "nodes.csv")
    rels_path = os.path.join(BASE_DIR, "datasets", "relationships.csv")

    if not force and os.path.exists(nodes_path) and os.path.exists(rels_path):
        print("✅ Dataset CSVs already exist. Skipping download.")
        print("   (Use --force-dataset to override)")
        return

    script = os.path.join(BASE_DIR, "scripts", "download_and_process_dataset.py")
    cmd = [sys.executable, script]
    if force:
        cmd.append("--force")
    run(cmd)


def stage_workloads():
    banner("STAGE 3/3 — Running workloads, concurrency & footprint benchmarks")
    # Updated path to match your scripts folder
    script = os.path.join(BASE_DIR, "workloads", "run_all_workloads.py")
    run([sys.executable, script])


def check_env_file():
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.isfile(env_path):
        print("⚠️  No .env file found. Copy .env.example to .env and fill in credentials")
        print("   for whichever databases you want to benchmark (scripts skip any DB")
        print("   whose env vars aren't set).\n")


def main():
    parser = argparse.ArgumentParser(description="Run the testing benchmark pipeline (NO LOAD).")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--skip-dataset", action="store_true")
    parser.add_argument("--skip-workloads", action="store_true")
    parser.add_argument("--force-dataset", action="store_true", help="Re-download/rebuild the dataset CSVs")
    parser.add_argument("--only", choices=["install", "dataset", "workloads"], default=None,
                         help="Run only this single stage")
    args = parser.parse_args()

    check_env_file()
    start = time.time()

    if args.only:
        stage_map = {
            "install": stage_install,
            "dataset": lambda: stage_dataset(args.force_dataset),
            "workloads": stage_workloads,
        }
        stage_map[args.only]()
    else:
        if not args.skip_install:
            stage_install()
        if not args.skip_dataset:
            stage_dataset(args.force_dataset)
        if not args.skip_workloads:
            stage_workloads()

    elapsed = time.time() - start
    banner(f"✅ Testing Pipeline complete in {elapsed:.1f}s")
    print("Results written to:")
    print("  results/workload_metrics.csv")
    print("  results/workload_raw_latencies.csv")
    print("  results/concurrency_metrics.csv")
    print("  results/footprint_metrics.csv")


if __name__ == "__main__":
    main()