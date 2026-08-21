import os
import csv
import base64
from neo4j import GraphDatabase
from arango import ArangoClient
from falkordb import FalkorDB
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
FOOTPRINT_FILE = os.path.join(RESULTS_DIR, "footprint_metrics.csv")

def get_cypher_footprint(uri, user, password, db_label, vcpu, mem):
    if not uri:
        return [db_label, vcpu, mem, "N/A", "Credentials missing"]
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            # 1. Try APOC (Neo4j/CognoDB)
            try:
                res = session.run("CALL apoc.monitor.store() YIELD totalStoreSize RETURN totalStoreSize")
                size = res.single()[0]
                return [db_label, vcpu, mem, f"{size / (1024*1024):.2f} MB", "Measured via apoc.monitor.store()"]
            except Exception:
                pass
            
            # 2. Try Memgraph specific command
            try:
                res = session.run("SHOW STORAGE INFO")
                records = list(res)
                if records:
                    return [db_label, vcpu, mem, "Observable", "Measured via SHOW STORAGE INFO (Check specific output format)"]
            except Exception:
                pass
            
            return [db_label, vcpu, mem, "Not observable", "Free-tier limits admin/APOC procedures"]
    except Exception as e:
        return [db_label, vcpu, mem, "Not observable", f"Connection/execution error: {e}"]

def get_arango_footprint():
    uri = os.environ.get("ARANGO_HOST")
    user = os.environ.get("ARANGO_USERNAME")
    password = os.environ.get("ARANGO_PASSWORD")
    encodedCA = os.environ.get("ARANGO_ENCODED_CA")
    
    if not uri or not encodedCA:
        return ["ArangoDB", "Serverless", "Standard Limits", "N/A", "Credentials missing"]
        
    try:
        cert_path = os.path.join(BASE_DIR, "cert_file.crt")
        with open(cert_path, "w+") as f:
            f.write(base64.b64decode(encodedCA).decode("utf-8"))
            
        client = ArangoClient(hosts=uri, verify_override=cert_path)
        sys_db = client.db("_system", username=user, password=password)
        
        # NOTE: Fetching statistics requires appropriate privileges
        p_stats = sys_db.collection("Person").statistics()
        f_stats = sys_db.collection("FOLLOWS").statistics()
        
        total_size = (p_stats.get("figures", {}).get("documentsSize", 0) + 
                      f_stats.get("figures", {}).get("documentsSize", 0))
        
        return ["ArangoDB", "Serverless", "Standard Limits", f"{total_size / (1024*1024):.2f} MB", "Measured via collection statistics"]
    except Exception as e:
        return ["ArangoDB", "Serverless", "Standard Limits", "Not observable", f"Privilege/API restriction: {e}"]

def get_falkor_footprint():
    url = os.environ.get("FALKOR_URL")
    user = os.environ.get("FALKOR_USERNAME")
    password = os.environ.get("FALKOR_PASSWORD")
    
    if not url:
        return ["FalkorDB", "Shared vCPU", "100 MB RAM", "N/A", "Credentials missing"]
        
    try:
        client = FalkorDB.from_url(url, username=user, password=password)
        graph = client.select_graph("benchmark")
        
        # Attempt to run a memory usage query if supported by the DB version
        res = graph.query("CALL db.info()") 
        return ["FalkorDB", "Shared vCPU", "100 MB RAM", "Observable", "Measured via CALL db.info() (Check output dictionary)"]
    except Exception as e:
        return ["FalkorDB", "Shared vCPU", "100 MB RAM", "Not observable", f"API restriction or unsupported call: {e}"]

def collect_footprint_data():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    data = []
    # 1. CognoDB
    data.append(get_cypher_footprint(
        os.environ.get("CONGODB_CONNECTION_URI"), os.environ.get("CONGODB_USERNAME"), os.environ.get("CONGODB_PASSWORD"),
        "CognoDB", "0.5 vCPU", "512 MB RAM"
    ))
    # 2. Neo4j
    data.append(get_cypher_footprint(
        os.environ.get("NEO4J_URI"), os.environ.get("NEO4J_USERNAME"), os.environ.get("NEO4J_PASSWORD"),
        "Neo4j", "Shared vCPU", "1 GB RAM"
    ))
    # 3. Memgraph
    data.append(get_cypher_footprint(
        f"bolt+ssc://{os.environ.get('MEMGRAPH_HOST')}:{os.environ.get('MEMGRAPH_PORT')}" if os.environ.get('MEMGRAPH_HOST') else None,
        os.environ.get("MEMGRAPH_USERNAME"), os.environ.get("MEMGRAPH_PASSWORD"),
        "Memgraph", "Containerized", "Free Tier Specs"
    ))
    # 4. ArangoDB
    data.append(get_arango_footprint())
    # 5. FalkorDB
    data.append(get_falkor_footprint())

    with open(FOOTPRINT_FILE, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Database", "vCPU Spec", "Memory Spec", "Measured Stored Size", "Observability Note"])
        writer.writerows(data)
        
    print(f"✅ Footprint metrics successfully saved to {FOOTPRINT_FILE}")

if __name__ == "__main__":
    collect_footprint_data()