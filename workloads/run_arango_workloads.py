import os
import csv
import time
import base64
import numpy as np
from arango import ArangoClient
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
WORKLOAD_METRICS_FILE = os.path.join(RESULTS_DIR, "workload_metrics.csv")
RAW_LATENCIES_FILE = os.path.join(RESULTS_DIR, "workload_raw_latencies.csv")

ITERATIONS = 100
WARMUP_ITERATIONS = 10

def save_workload_metrics(db_name, metric_name, p50, p95):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    file_exists = os.path.isfile(WORKLOAD_METRICS_FILE)
    
    with open(WORKLOAD_METRICS_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Database", "Metric", "p50 Latency (ms)", "p95 Latency (ms)"])
        p50_val = round(p50, 2) if isinstance(p50, (int, float)) else p50
        p95_val = round(p95, 2) if isinstance(p95, (int, float)) else p95
        writer.writerow([db_name, metric_name, p50_val, p95_val])

def save_raw_latencies(db_name, metric_name, latencies):
    if not latencies: return
    os.makedirs(RESULTS_DIR, exist_ok=True)
    file_exists = os.path.isfile(RAW_LATENCIES_FILE)
    
    with open(RAW_LATENCIES_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Database", "Metric", "Iteration", "Latency (ms)"])
        rows = [[db_name, metric_name, i + 1, round(lat, 4)] for i, lat in enumerate(latencies)]
        writer.writerows(rows)

def run_query(db, query, params=None):
    start_time = time.perf_counter()
    cursor = db.aql.execute(query, bind_vars=params)
    # Force consumption of the cursor
    _ = [doc for doc in cursor]
    end_time = time.perf_counter()
    return (end_time - start_time) * 1000

def execute_benchmark(db, db_name, metric_name, query, params_list):
    print(f"  -> Running {metric_name}...")
    try:
        for i in range(WARMUP_ITERATIONS):
            run_query(db, query, params_list[i % len(params_list)])
            
        latencies = []
        for i in range(ITERATIONS):
            latency = run_query(db, query, params_list[i % len(params_list)])
            latencies.append(latency)
            
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        
        save_workload_metrics(db_name, metric_name, p50, p95)
        save_raw_latencies(db_name, metric_name, latencies)
        print(f"     p50: {p50:.2f} ms | p95: {p95:.2f} ms")
        
    except Exception as e:
        error_name = e.__class__.__name__
        print(f"     ❌ Failed: {error_name} (Connection Dropped or OOM)")
        save_workload_metrics(db_name, metric_name, "Timeout/OOM", "Timeout/OOM")

def run_arango_workloads():
    print(f"\n{'='*40}")
    print(f"🚀 Starting Workloads for ArangoDB")
    print(f"{'='*40}")
    
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

    # Fetch random start nodes
    print("Fetching random start nodes for parameterization...")
    rand_query = f"FOR p IN Person SORT RAND() LIMIT {ITERATIONS} RETURN {{id: p._key, _key: p._key, name: p.name}}"
    cursor = sys_db.aql.execute(rand_query)
    nodes = [doc for doc in cursor]
#   --- 1. Lookups ---
    execute_benchmark(sys_db, "ArangoDB", "Point Lookup (ID)", 
                      "FOR p IN Person FILTER p._key == @id RETURN p", nodes)
    
    execute_benchmark(sys_db, "ArangoDB", "Indexed Lookup (Name)", 
                      "FOR p IN Person FILTER p.name == @name RETURN p", nodes)
    
    # --- 2. Aggregations ---
    execute_benchmark(sys_db, "ArangoDB", "Aggregation (Count by Age)", 
                      "FOR p IN Person COLLECT age = p.age WITH COUNT INTO count RETURN {age, count}", [{}] * ITERATIONS)

    # --- 3. Traversals (Correct ArangoDB AQL syntax specifying the 'FOLLOWS' edge collection) ---
    execute_benchmark(sys_db, "ArangoDB", "1-Hop Traversal", 
                      "FOR v IN 1..1 OUTBOUND CONCAT('Person/', @id) FOLLOWS RETURN v", nodes)
    
    execute_benchmark(sys_db, "ArangoDB", "2-Hop Traversal", 
                      "FOR v IN 2..2 OUTBOUND CONCAT('Person/', @id) FOLLOWS RETURN v", nodes)
    
    execute_benchmark(sys_db, "ArangoDB", "3-Hop Traversal", 
                      "FOR v IN 3..3 OUTBOUND CONCAT('Person/', @id) FOLLOWS RETURN v", nodes)

if __name__ == "__main__":
    run_arango_workloads()