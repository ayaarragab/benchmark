"""
Deterministic dataset processor for the SNAP email-Enron network.

Downloads the raw edge list (source_id -> target_id), then builds two
reproducible CSVs used by every loader/workload script in this repo:

  datasets/nodes.csv         id,name,age
  datasets/relationships.csv source_id,target_id

A fixed random seed is used for the synthetic `name`/`age` properties so the
dataset is byte-for-byte reproducible across machines and runs.
"""

import csv
import gzip
import io
import os
import random
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")

NODES_FILE = os.path.join(DATASETS_DIR, "nodes.csv")
RELS_FILE = os.path.join(DATASETS_DIR, "relationships.csv")

DEFAULT_DATASET_URL = "https://snap.stanford.edu/data/email-Enron.txt.gz"
SEED = 42

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Timothy", "Deborah",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts",
]


def download_dataset(url: str) -> bytes:
    print(f"Downloading dataset from {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "benchmark-dataset-processor/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read()
    print(f"Downloaded {len(raw) / (1024 * 1024):.2f} MB")
    return raw


def parse_edges(raw_bytes: bytes, url: str):
    """Parse a SNAP-style edge list, transparently handling .gz or plain text."""
    if url.endswith(".gz"):
        text_stream = io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(raw_bytes)), encoding="utf-8")
    else:
        text_stream = io.StringIO(raw_bytes.decode("utf-8"))

    edges = []
    node_ids = set()
    for line in text_stream:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        source_id, target_id = parts[0], parts[1]
        edges.append((source_id, target_id))
        node_ids.add(source_id)
        node_ids.add(target_id)

    return node_ids, edges


def build_nodes(node_ids):
    rng = random.Random(SEED)
    sorted_ids = sorted(node_ids, key=lambda x: int(x))

    nodes = []
    for node_id in sorted_ids:
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        age = rng.randint(18, 65)
        nodes.append({"id": node_id, "name": f"{first} {last}", "age": age})

    return nodes


def write_csv(path, fieldnames, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows):,} rows -> {path}")


def process_dataset(url: str, force: bool = False):
    if not force and os.path.isfile(NODES_FILE) and os.path.isfile(RELS_FILE):
        print("datasets/nodes.csv and datasets/relationships.csv already exist. "
              "Skipping (pass --force to regenerate).")
        return

    raw_bytes = download_dataset(url)
    node_ids, edges = parse_edges(raw_bytes, url)

    print(f"Parsed {len(node_ids):,} unique nodes and {len(edges):,} relationships.")

    nodes = build_nodes(node_ids)
    write_csv(NODES_FILE, ["id", "name", "age"], nodes)

    rels = [{"source_id": s, "target_id": t} for s, t in edges]
    write_csv(RELS_FILE, ["source_id", "target_id"], rels)

    print("✅ Dataset ready.")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    dataset_url = os.environ.get("DATASET_URL") or DEFAULT_DATASET_URL
    force_flag = "--force" in sys.argv

    process_dataset(dataset_url, force=force_flag)
