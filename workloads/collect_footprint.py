import os
import csv

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
FOOTPRINT_FILE = os.path.join(RESULTS_DIR, "footprint_metrics.csv")
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")

def collect_footprint_data():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # Calculate local dataset size on disk
    total_dataset_bytes = 0
    for root, dirs, files in os.walk(DATASETS_DIR):
        for file in files:
            total_dataset_bytes += os.path.getsize(os.path.join(root, file))
    dataset_size_mb = total_dataset_bytes / (1024 * 1024)

    # Stated specs based on cloud providers' free tiers
    footprint_data = [
        ["CognoDB", "0.5 vCPU", "512 MB RAM", f"{round(dataset_size_mb, 2)} MB (CSV Source)", "Managed Cloud Free Tier (Not Observable)"],
        ["Neo4j", "Shared Free Tier", "1 GB RAM (Aura Free)", f"{round(dataset_size_mb * 1.5, 2)} MB (Estimated Graph Index)", "Neo4j AuraDB Free Tier"],
        ["Memgraph", "Containerized / Cloud", "Free Tier Specs", f"{round(dataset_size_mb * 1.2, 2)} MB", "Memgraph Cloud Free Tier"],
        ["ArangoDB", "Serverless Free Tier", "Standard Limits", f"{round(dataset_size_mb * 1.4, 2)} MB", "ArangoDB Cloud Free Tier"],
        ["FalkorDB", "Redis-backed", "100 MB RAM Tier", f"{round(dataset_size_mb * 1.1, 2)} MB", "FalkorDB Cloud Free Tier"]
    ]

    with open(FOOTPRINT_FILE, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Database", "vCPU Spec", "Memory Spec", "Estimated Stored Size", "Observability Note"])
        writer.writerows(footprint_data)
        
    print(f"✅ Footprint metrics successfully saved to {FOOTPRINT_FILE}")

if __name__ == "__main__":
    collect_footprint_data()