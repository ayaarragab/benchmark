import os
import csv
import time
import numpy as np
from falkordb import FalkorDB
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

def run_query(graph, query, params=None):
    start_time = time.perf_counter()
    result = graph.query(query, params)
    # Access result_set to force evaluation
    _ = result.result_set
    end_time = time.perf_counter()
    return (end_time - start_time) * 1000

def execute_benchmark(graph, db_name, metric_name, query, params_list):
    print(f"  -> Running {metric_name}...")
    try:
        for i in range(WARMUP_ITERATIONS):
            run_query(graph, query, params_list[i % len(params_list)])
            
        latencies = []
        for i in range(ITERATIONS):
            latency = run_query(graph, query, params_list[i % len(params_list)])
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

def run_falkor_workloads():
    print(f"\n{'='*40}")
    print(f"🚀 Starting Workloads for FalkorDB")
    print(f"{'='*40}")
    
    url = os.environ.get("FALKOR_URL")
    user = os.environ.get("FALKOR_USERNAME")
    password = os.environ.get("FALKOR_PASSWORD")

    if not url:
        print("FalkorDB credentials missing.")
        return

    client = FalkorDB.from_url(url, username=user, password=password)
    graph = client.select_graph("benchmark")

    # Fetch random nodes
    print("Fetching random start nodes for parameterization...")
    res = graph.query(f"MATCH (p:Person) WITH p ORDER BY rand() LIMIT {ITERATIONS} RETURN p.id AS id, p.name AS name")
    nodes = [{"id": row[0], "name": row[1]} for row in res.result_set]

    # --- 1. Lookups (Safe) ---
    execute_benchmark(graph, "FalkorDB", "Point Lookup (ID)", "MATCH (p:Person {id: $id}) RETURN p.id", nodes)
    execute_benchmark(graph, "FalkorDB", "Indexed Lookup (Name)", "MATCH (p:Person {name: $name}) RETURN p.name, p.age", nodes)
    
    # --- 2. Aggregations (Safe) ---
    execute_benchmark(graph, "FalkorDB", "Aggregation (Count by Age)", "MATCH (p:Person) WITH p.age AS age, count(p) AS count RETURN age, count", [{}] * ITERATIONS)

    # --- 3. Traversals (Increasing Danger) ---
    execute_benchmark(graph, "FalkorDB", "1-Hop Traversal", "MATCH (p:Person {id: $id})-[:FOLLOWS]->(f) RETURN count(f)", nodes)
    execute_benchmark(graph, "FalkorDB", "2-Hop Traversal", "MATCH (p:Person {id: $id})-[:FOLLOWS*2]->(f) RETURN count(f)", nodes)
    execute_benchmark(graph, "FalkorDB", "3-Hop Traversal", "MATCH (p:Person {id: $id})-[:FOLLOWS*3]->(f) RETURN count(f)", nodes)

if __name__ == "__main__":
    run_falkor_workloads()