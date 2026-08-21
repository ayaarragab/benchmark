import csv
import time
import os
from falkordb import FalkorDB
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

NODES_FILE = os.path.join(DATASETS_DIR, "nodes.csv")
RELS_FILE = os.path.join(DATASETS_DIR, "relationships.csv")
LOAD_METRICS_FILE = os.path.join(RESULTS_DIR, "load_metrics.csv")

BATCH_SIZE = 1000

def save_metrics_to_csv(db_name, total_time, nodes_per_sec, rels_per_sec):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    file_exists = os.path.isfile(LOAD_METRICS_FILE)
    
    with open(LOAD_METRICS_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Database", "Total Load Time (s)", "Nodes/sec", "Relationships/sec"])
        writer.writerow([db_name, round(total_time, 2), round(nodes_per_sec, 2), round(rels_per_sec, 2)])
    print(f"Metrics saved to {LOAD_METRICS_FILE}")

def load_falkor_data():
    print("\n--- Starting Data Load for FalkorDB ---")
    url = os.environ.get("FALKOR_URL")
    user = os.environ.get("FALKOR_USERNAME")
    password = os.environ.get("FALKOR_PASSWORD")

    if not url:
        print("FalkorDB credentials missing.")
        return

    # Connect and select graph
    client = FalkorDB.from_url(url, username=user, password=password)
    graph = client.select_graph("benchmark")

    # 1. Clear Data
    print("Clearing existing data...")
    graph.query("MATCH (n) DETACH DELETE n")

    # 2. Create Indexes (Required for Lookup benchmarks)
    print("Creating indexes on name and id...")
    graph.query("CREATE INDEX FOR (p:Person) ON (p.name)")
    graph.query("CREATE INDEX FOR (p:Person) ON (p.id)")

    # 3. Load Nodes
    print("Loading nodes in batches...")
    nodes = []
    with open(NODES_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            nodes.append({"id": row["id"], "name": row["name"], "age": int(row["age"])})

    start_time_nodes = time.time()
    for i in range(0, len(nodes), BATCH_SIZE):
        batch = nodes[i:i + BATCH_SIZE]
        # FalkorDB supports UNWIND, but we pass the batch directly as a parameter
        query = """
        UNWIND $batch AS row
        CREATE (p:Person {id: row.id, name: row.name, age: row.age})
        """
        graph.query(query, {"batch": batch})
    nodes_time = time.time() - start_time_nodes
    nodes_per_sec = len(nodes) / (nodes_time if nodes_time > 0 else 1)

    # 4. Load Relationships
    print("Loading relationships in batches...")
    rels = []
    with open(RELS_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rels.append({"source": row["source_id"], "target": row["target_id"]})

    start_time_rels = time.time()
    for i in range(0, len(rels), BATCH_SIZE):
        batch = rels[i:i + BATCH_SIZE]
        query = """
        UNWIND $batch AS row
        MATCH (s:Person {id: row.source}), (t:Person {id: row.target})
        CREATE (s)-[:FOLLOWS]->(t)
        """
        graph.query(query, {"batch": batch})
    rels_time = time.time() - start_time_rels
    rels_per_sec = len(rels) / (rels_time if rels_time > 0 else 1)

    total_time = nodes_time + rels_time
    print(f"\n--- FalkorDB Load Metrics ---")
    print(f"Total time: {total_time:.2f} s | Nodes/s: {nodes_per_sec:.2f} | Rels/s: {rels_per_sec:.2f}")
    
    save_metrics_to_csv("FalkorDB", total_time, nodes_per_sec, rels_per_sec)

if __name__ == "__main__":
    load_falkor_data()