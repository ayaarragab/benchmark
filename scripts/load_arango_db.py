import csv
import time
import os
import base64
from arango import ArangoClient
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

def load_arango_data():
    encodedCA = os.environ.get("ARANGO_ENCODED_CA")
    arango_username = os.environ.get("ARANGO_USERNAME")
    arango_password = os.environ.get("ARANGO_PASSWORD")
    arango_host = os.environ.get("ARANGO_HOST")

    if not encodedCA or not arango_password:
        print("Missing ArangoDB credentials.")
        return

    file_content = base64.b64decode(encodedCA)
    cert_path = os.path.join(BASE_DIR, "cert_file.crt")
    with open(cert_path, "w+") as f:
        f.write(file_content.decode("utf-8"))

    client = ArangoClient(hosts=arango_host, verify_override=cert_path)
    sys_db = client.db("_system", username=arango_username, password=arango_password)
    
    print("\n--- Starting Data Load for ArangoDB ---")

    # 1. Setup Collections
    if sys_db.has_collection("Person"):
        sys_db.collection("Person").truncate()
    else:
        sys_db.create_collection("Person")

    if sys_db.has_collection("FOLLOWS"):
        sys_db.collection("FOLLOWS").truncate()
    else:
        sys_db.create_collection("FOLLOWS", edge=True)

    # 2. Indexes
    person_coll = sys_db.collection("Person")
    person_coll.add_persistent_index(fields=["name"])
    # 3. Load Nodes
    print("Loading nodes...")
    nodes = []
    with open(NODES_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # ArangoDB requires the primary key to be strictly named '_key'
            nodes.append({"_key": str(row["id"]), "name": row["name"], "age": int(row["age"])})

    start_time_nodes = time.time()
    for i in range(0, len(nodes), BATCH_SIZE):
        batch = nodes[i:i + BATCH_SIZE]
        person_coll.insert_many(batch)
    nodes_time = time.time() - start_time_nodes
    nodes_per_sec = len(nodes) / nodes_time

    # 4. Load Relationships
    print("Loading relationships...")
    rels = []
    with open(RELS_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # ArangoDB edge format requires '_from' and '_to' referencing the Collection Name
            rels.append({
                "_from": f"Person/{row['source_id']}",
                "_to": f"Person/{row['target_id']}"
            })

    start_time_rels = time.time()
    follows_coll = sys_db.collection("FOLLOWS")
    for i in range(0, len(rels), BATCH_SIZE):
        batch = rels[i:i + BATCH_SIZE]
        follows_coll.insert_many(batch)
    rels_time = time.time() - start_time_rels
    rels_per_sec = len(rels) / rels_time

    total_time = nodes_time + rels_time
    print(f"\n--- ArangoDB Load Metrics ---")
    print(f"Total time: {total_time:.2f} s | Nodes/s: {nodes_per_sec:.2f} | Rels/s: {rels_per_sec:.2f}")
    
    save_metrics_to_csv("ArangoDB", total_time, nodes_per_sec, rels_per_sec)

if __name__ == "__main__":
    load_arango_data()