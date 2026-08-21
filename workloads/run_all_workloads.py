import subprocess
import os
import sys

def run_script(script_path):
    print(f"\n{'='*60}")
    print(f"🚀 Running {os.path.basename(script_path)}...")
    print(f"{'='*60}\n")
    
    try:
        # Use the same python executable (from .venv)
        result = subprocess.run([sys.executable, script_path], check=True)
        print(f"\n✅ Successfully finished {os.path.basename(script_path)}")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running script: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🎯 Starting Global End-to-End Benchmarking Suite...")
    
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    SCRIPTS_DIR = os.path.join(BASE_DIR, "workloads") # أو workloads حسب مكان ملفاتك
    
    # قائمة السكريبتات شاملة الـ Workloads، الـ Concurrency، والـ Footprint
    benchmark_scripts = [
        os.path.join(SCRIPTS_DIR, "run_cypher_workloads.py"),
        os.path.join(SCRIPTS_DIR, "run_arango_workloads.py"),
        os.path.join(SCRIPTS_DIR, "run_falkor_workloads.py"),
        os.path.join(SCRIPTS_DIR, "run_concurrency_benchmark.py"),
        os.path.join(SCRIPTS_DIR, "collect_footprint.py")
    ]
    
    for script in benchmark_scripts:
        if os.path.exists(script):
            run_script(script)
        else:
            print(f"⚠️ Warning: Script not found at {script}, skipping...")
            
    print("\n🎉 All benchmarks and footprints completed successfully!")
    print("📁 Check your results/ folder for:")
    print("   - workload_metrics.csv & workload_raw_latencies.csv")
    print("   - concurrency_metrics.csv")
    print("   - footprint_metrics.csv")