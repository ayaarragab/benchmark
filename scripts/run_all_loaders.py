import subprocess
import os
import sys

def run_script(script_name):
    print(f"\n{'='*50}")
    print(f"🚀 Running {script_name}...")
    print(f"{'='*50}\n")
    
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    
    try:
        # Use the same python executable that is running this script (the .venv python)
        result = subprocess.run([sys.executable, script_path], check=True)
        print(f"\n✅ Successfully finished {script_name}")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running {script_name}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Starting Global Data Loader...")
    
    scripts_to_run = [
        "load_cypher_dbs.py",  # Runs CognoDB, Neo4j, and Memgraph
        "load_arango_db.py",   # Runs ArangoDB
        "load_memgraph_db.py", # Runs Memgraph
        "load_falkor_db.py"    # Runs FalkorDB
    ]
    
    for script in scripts_to_run:
        run_script(script)
        
    print("\n🎉 All databases have been loaded successfully! Check results/load_metrics.csv")