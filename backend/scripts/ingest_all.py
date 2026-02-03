"""
Master Ingestion Script - Ingest ALL content in parallel
Handles PDFs and XLSX files across all folders
"""

import subprocess
import sys
from pathlib import Path

# Base paths
CONTENT_DIR = Path("../Content")
BACKEND_DIR = Path(".")

# Define ingestion tasks - PDFs FIRST, then XLSX
INGESTION_TASKS = [
    # === PHASE 1: ALL PDFs (tested and working) ===
    
    # Economic Survey PDF (already done, but included for completeness)
    {
        "type": "pdf",
        "folder": CONTENT_DIR / "Report",
        "corpus": "Economic Survey 2025-26",
        "year": 2026
    },
    # Union Budget PDFs (30 files)
    {
        "type": "pdf",
        "folder": CONTENT_DIR / "Budget",
        "corpus": "Union Budget 2025-26",
        "year": 2026
    },
    
    # === PHASE 2: XLSX files (not yet tested) ===
    
    # Statistical Index XLSX (105 files)
    {
        "type": "xlsx",
        "folder": CONTENT_DIR / "Statistical_Index",
        "corpus": "Economic Survey 2025-26 - Statistical Appendix",
        "year": 2026
    },
    # Charts and Tables XLSX (13 files)
    {
        "type": "xlsx",
        "folder": CONTENT_DIR / "Charts_and_Tables",
        "corpus": "Economic Survey 2025-26 - Charts & Tables",
        "year": 2026
    }
]


def run_ingestion_task(task):
    """Run a single ingestion task"""
    folder = task["folder"]
    corpus = task["corpus"]
    year = task["year"]
    task_type = task["type"]
    
    if not folder.exists():
        print(f"⚠️  Folder not found: {folder}")
        return
    
    if task_type == "pdf":
        script = "batch_ingest.py"
    else:
        script = "ingest_xlsx.py"
    
    cmd = [
        sys.executable,
        f"scripts/{script}",
        str(folder),
        "--corpus", corpus,
        "--year", str(year)
    ]
    
    print(f"\n{'='*70}")
    print(f"Starting: {corpus}")
    print(f"Folder: {folder}")
    print(f"Type: {task_type.upper()}")
    print(f"{'='*70}\n")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"\n✅ COMPLETED: {corpus}\n")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ FAILED: {corpus} - {e}\n")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                   MASTER INGESTION PIPELINE                       ║
║           Economic Survey + Budget + Data Tables                  ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    print(f"Tasks to run: {len(INGESTION_TASKS)}")
    for i, task in enumerate(INGESTION_TASKS, 1):
        print(f"  {i}. {task['corpus']} ({task['type'].upper()})")
    
    print("\n⚠️  NOTE: This will run tasks SEQUENTIALLY to avoid API rate limits")
    print("   Estimated time: ~30-60 minutes\n")
    
    input("Press ENTER to start ingestion...")
    
    # Run all tasks sequentially
    for i, task in enumerate(INGESTION_TASKS, 1):
        print(f"\n{'#'*70}")
        print(f"TASK {i}/{len(INGESTION_TASKS)}")
        print(f"{'#'*70}")
        run_ingestion_task(task)
    
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                   ALL INGESTION COMPLETE!                         ║
╚═══════════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
