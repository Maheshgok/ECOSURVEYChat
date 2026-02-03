"""
Re-ingest failed XLSX files
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
from ingest_xlsx import ingest_xlsx

# Failed files from the error log
FAILED_FILES = [
    "tabchart1.xlsx",
    "tabchart10.xlsx", 
    "tabchart14.xlsx",
    "tabchart4.xlsx",
    "tabchart5.xlsx",
    "tabchart7.xlsx",
    "tabchart8.xlsx"
]

CHARTS_FOLDER = Path("..") / "Content" / "Charts_and_Tables"

def main():
    print("\n" + "="*70)
    print("RE-INGESTING FAILED XLSX FILES")
    print("="*70 + "\n")
    
    success = 0
    failed = 0
    
    for filename in FAILED_FILES:
        file_path = CHARTS_FOLDER / filename
        
        if not file_path.exists():
            print(f"❌ File not found: {filename}")
            failed += 1
            continue
        
        title = filename.replace('.xlsx', '').replace('_', ' ').upper()
        print(f"\n[{success + failed + 1}/{len(FAILED_FILES)}] {filename}")
        
        result = ingest_xlsx(
            xlsx_path=str(file_path),
            title=title,
            corpus_name="Economic Survey 2025-26 - Charts & Tables",
            year=2026
        )
        
        if result:
            success += 1
        else:
            failed += 1
    
    print("\n" + "="*70)
    print(f"✅ Success: {success} | ❌ Failed: {failed}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
