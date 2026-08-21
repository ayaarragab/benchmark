import os
import csv
import time
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from neo4j import GraphDatabase
from arango import ArangoClient
from falkordb import FalkorDB
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONCURRENCY_METRICS_FILE = os.path.join(RESULTS_DIR, "concurrency_metrics.csv")

CONCURRENCY_LEVELS = [10, 20, 40]  # Client concurrency levels
REQUESTS_PER_CLIENT = 15           # Reduced slightly to respect free-tier rate limits

def save_concurrency_metrics(db_name, concurrency, mix_type, total_requests, duration, qps):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    file_exists = os.path.isfile(CONCURRENCY_METRICS_FILE)
    
    with open(CONCURRENCY_METRICS_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Database", "Concurrency (Clients)", "Workload Mix", "Total Requests", "Duration (s)", "Throughput (QPS)"])
        writer.writerow([db_name, concurrency, mix_type, total_requests, round(duration, 2), round(qps, 2)])
    print(f"     ✅ [{db_name}] Concurrency {concurrency} -> Throughput: {qps:.2f} QPS (Duration: {duration:.2f}s)")

# --- 1. Cypher Worker (CognoDB, Neo4j, Memgraph) ---
def cypher_worker(driver, query):
    try:
        with driver.session() as session:
            start = time.perf_counter()
            result = session.run(query)
            result.consume()
            end = time.perf_counter()
            return True, (end - start) * 1000
    except Exception:
        return False, 0

def benchmark_cypher(db_name, driver, concurrency):
    read_query = "MATCH (p:Person) RETURN p.name LIMIT 1"
    write_query = "CREATE (n:Log {timestamp: timestamp()}) RETURN n"
    
    tasks = [write_query if i % 5 == 0 else read_query for i in range(concurrency * REQUESTS_PER_CLIENT)]
    total_requests = len(tasks)
    
    start_time = time.perf_counter()
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(cypher_worker, driver, q) for q in tasks]
        for future in as_completed(futures):
            success, _ = future.result()
            if success: success_count += 1
            
    duration = time.perf_counter() - start_time
    qps = success_count / duration if duration > 0 else 0
    save_concurrency_metrics(db_name, concurrency, "80% Read / 20% Write", total_requests, duration, qps)


# --- 2. ArangoDB Worker (AQL) ---
def arango_worker(sys_db, read_q, write_q, is_write):
    try:
        start = time.perf_counter()
        if is_write:
            cursor = sys_db.aql.execute(write_q)
        else:
            cursor = sys_db.aql.execute(read_q)
        _ = [doc for doc in cursor]
        end = time.perf_counter()
        return True, (end - start) * 1000
    except Exception:
        return False, 0

def benchmark_arango(concurrency):
    db_name = "ArangoDB"
    encodedCA = os.environ.get("ARANGO_ENCODED_CA")
    if not encodedCA: return
    
    file_content = base64.b64decode(encodedCA)
    cert_path = os.path.join(BASE_DIR, "cert_file.crt")
    with open(cert_path, "w+") as f:
        f.write(file_content.decode("utf-8"))

    client = ArangoClient(hosts=os.environ.get("ARANGO_HOST"), verify_override=cert_path)
    sys_db = client.db("_system", username=os.environ.get("ARANGO_USERNAME"), password=os.environ.get("ARANGO_PASSWORD"))

    read_query = "FOR p IN Person LIMIT 1 RETURN p.name"
    write_query = "INSERT {timestamp: DATE_NOW()} INTO Log"
    
    tasks = []
    for i in range(concurrency * REQUESTS_PER_CLIENT):
        tasks.append((write_query, True) if i % 5 == 0 else (read_query, False))
        
    total_requests = len(tasks)
    start_time = time.perf_counter()
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(arango_worker, sys_db, read_query, write_query, is_w) for _, is_w in tasks]
        for future in as_completed(futures):
            success, _ = future.result()
            if success: success_count += 1
            
    duration = time.perf_counter() - start_time
    qps = success_count / duration if duration > 0 else 0
    save_concurrency_metrics(db_name, concurrency, "80% Read / 20% Write", total_requests, duration, qps)


# --- 3. FalkorDB Worker ---
def falkor_worker(graph, query):
    try:
        start = time.perf_counter()
        res = graph.query(query)
        _ = res.result_set
        end = time.perf_counter()
        return True, (end - start) * 1000
    except Exception:
        return False, 0

def benchmark_falkor(concurrency):
    db_name = "FalkorDB"
    url = os.environ.get("FALKOR_URL")
    if not url: return

    client = FalkorDB.from_url(url, username=os.environ.get("FALKOR_USERNAME"), password=os.environ.get("FALKOR_PASSWORD"))
    graph = client.select_graph("benchmark")

    read_query = "MATCH (p:Person) RETURN p.name LIMIT 1"
    write_query = "CREATE (n:Log {timestamp: timestamp()}) RETURN n"

    tasks = [write_query if i % 5 == 0 else read_query for i in range(concurrency * REQUESTS_PER_CLIENT)]
    total_requests = len(tasks)
    
    start_time = time.perf_counter()
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(falkor_worker, graph, q) for q in tasks]
        for future in as_completed(futures):
            success, _ = future.result()
            if success: success_count += 1
            
    duration = time.perf_counter() - start_time
    qps = success_count / duration if duration > 0 else 0
    save_concurrency_metrics(db_name, concurrency, "80% Read / 20% Write", total_requests, duration, qps)


if __name__ == "__main__":
    print("🚀 Starting Multi-Database Concurrency & Throughput Benchmark...")

    # 1. CognoDB
    if os.environ.get("CONGODB_CONNECTION_URI"):
        d = GraphDatabase.driver(os.environ.get("CONGODB_CONNECTION_URI"), auth=(os.environ.get("CONGODB_USERNAME"), os.environ.get("CONGODB_PASSWORD")))
        for c in CONCURRENCY_LEVELS: benchmark_cypher("CognoDB", d, c)
        d.close()

    # 2. Neo4j
    if os.environ.get("NEO4J_URI"):
        d = GraphDatabase.driver(os.environ.get("NEO4J_URI"), auth=(os.environ.get("NEO4J_USERNAME"), os.environ.get("NEO4J_PASSWORD")))
        for c in CONCURRENCY_LEVELS: benchmark_cypher("Neo4j", d, c)
        d.close()

    # 3. Memgraph
    if os.environ.get("MEMGRAPH_HOST"):
        d = GraphDatabase.driver(f"bolt+ssc://{os.environ.get('MEMGRAPH_HOST')}:{os.environ.get('MEMGRAPH_PORT')}", auth=(os.environ.get("MEMGRAPH_USERNAME"), os.environ.get("MEMGRAPH_PASSWORD")))
        for c in CONCURRENCY_LEVELS: benchmark_cypher("Memgraph", d, c)
        d.close()

    # 4. ArangoDB
    try:
        for c in CONCURRENCY_LEVELS: benchmark_arango(c)
    except Exception as e:
        print(f"❌ ArangoDB Concurrency failed: {e}")

    # 5. FalkorDB
    try:
        for c in CONCURRENCY_LEVELS: benchmark_falkor(c)
    except Exception as e:
        print(f"❌ FalkorDB Concurrency failed: {e}")

    print("\n🎉 Concurrency Benchmark Complete! Check results/concurrency_metrics.csv")