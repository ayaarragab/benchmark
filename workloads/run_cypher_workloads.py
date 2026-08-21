import os
import csv
import time
import numpy as np
from neo4j import GraphDatabase
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
    if not latencies: return # Skip if it failed
    
    os.makedirs(RESULTS_DIR, exist_ok=True)
    file_exists = os.path.isfile(RAW_LATENCIES_FILE)
    
    with open(RAW_LATENCIES_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Database", "Metric", "Iteration", "Latency (ms)"])
        
        rows = [[db_name, metric_name, i + 1, round(lat, 4)] for i, lat in enumerate(latencies)]
        writer.writerows(rows)

def run_query(session, query, params=None):
    start_time = time.perf_counter()
    result = session.run(query, params)
    result.consume() 
    end_time = time.perf_counter()
    return (end_time - start_time) * 1000 

def execute_benchmark(driver, db_name, metric_name, query, params_list):
    print(f"  -> Running {metric_name}...")
    
    # We open a NEW session per workload so a crash doesn't ruin subsequent tests
    try:
        with driver.session() as session:
            # 1. Warm-up Phase
            for i in range(WARMUP_ITERATIONS):
                run_query(session, query, params_list[i % len(params_list)])
                
            # 2. Measurement Phase
            latencies = []
            for i in range(ITERATIONS):
                latency = run_query(session, query, params_list[i % len(params_list)])
                latencies.append(latency)
                
            # 3. Calculate Percentiles
            p50 = np.percentile(latencies, 50)
            p95 = np.percentile(latencies, 95)
            
            save_workload_metrics(db_name, metric_name, p50, p95)
            save_raw_latencies(db_name, metric_name, latencies)
            print(f"     p50: {p50:.2f} ms | p95: {p95:.2f} ms")
            
    except Exception as e:
        error_name = e.__class__.__name__
        print(f"     ❌ Failed: {error_name} (Connection Dropped or OOM)")
        save_workload_metrics(db_name, metric_name, "Timeout/OOM", "Timeout/OOM")

def run_workloads(driver, db_name):
    print(f"\n{'='*40}")
    print(f"🚀 Starting Workloads for {db_name}")
    print(f"{'='*40}")
    
# Fetch start nodes first
    with driver.session() as session:
        print("Fetching random start nodes for parameterization...")
        result = session.run("MATCH (p:Person) WITH p ORDER BY rand() LIMIT $limit RETURN p.id AS id, p.name AS name", {"limit": ITERATIONS})
        nodes = [{"id": record["id"], "name": record["name"]} for record in result]
        
    # --- 1. Lookups (Safe & Fast) ---
    execute_benchmark(driver, db_name, "Point Lookup (ID)", "MATCH (p:Person {id: $id}) RETURN p.id", nodes)
    execute_benchmark(driver, db_name, "Indexed Lookup (Name)", "MATCH (p:Person {name: $name}) RETURN p.name, p.age", nodes)
    
    # --- 2. Aggregations (Safe) ---
    execute_benchmark(driver, db_name, "Aggregation (Count by Age)", "MATCH (p:Person) WITH p.age AS age, count(p) AS count RETURN age, count", [{}] * ITERATIONS)

    # --- 3. Traversals (Increasing Danger) ---
    execute_benchmark(driver, db_name, "1-Hop Traversal", "MATCH (p:Person {id: $id})-[:FOLLOWS]->(f) RETURN count(f)", nodes)
    execute_benchmark(driver, db_name, "2-Hop Traversal", "MATCH (p:Person {id: $id})-[:FOLLOWS*2]->(f) RETURN count(f)", nodes)
    
    # Put 3-Hop last so if it crashes the DB, we already saved the other metrics!
    execute_benchmark(driver, db_name, "3-Hop Traversal", "MATCH (p:Person {id: $id})-[:FOLLOWS*3]->(f) RETURN count(f)", nodes)
if __name__ == "__main__":
    # 1. CognoDB
    cognodb_uri = os.environ.get("CONGODB_CONNECTION_URI")
    if cognodb_uri:
        driver = GraphDatabase.driver(cognodb_uri, auth=(os.environ.get("CONGODB_USERNAME"), os.environ.get("CONGODB_PASSWORD")))
        run_workloads(driver, "CognoDB")
        driver.close()

    # 2. Neo4j
    neo4j_uri = os.environ.get("NEO4J_URI")
    if neo4j_uri:
        driver = GraphDatabase.driver(neo4j_uri, auth=(os.environ.get("NEO4J_USERNAME"), os.environ.get("NEO4J_PASSWORD")))
        run_workloads(driver, "Neo4j")
        driver.close()

    # 3. Memgraph
    memgraph_host = os.environ.get("MEMGRAPH_HOST")
    if memgraph_host:
        memgraph_uri = f"bolt+ssc://{memgraph_host}:{os.environ.get('MEMGRAPH_PORT')}"
        driver = GraphDatabase.driver(memgraph_uri, auth=(os.environ.get("MEMGRAPH_USERNAME"), os.environ.get("MEMGRAPH_PASSWORD")))
        run_workloads(driver, "Memgraph")
        driver.close()