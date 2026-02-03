"""
Batch PDF Ingestion - Ingest all PDFs in a folder
Can run multiple folders in parallel for different corpuses
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
from pathlib import Path
from ingest_pdf import ingest_document


def batch_ingest_folder(
    folder_path: str,
    corpus_name: str,
    year: int = 2026,
    pattern: str = "*.pdf"
):
    """Ingest all PDFs in a folder"""
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"❌ Folder not found: {folder_path}")
        return
    
    # Find all PDFs
    pdf_files = list(folder.glob(pattern))
    
    if not pdf_files:
        print(f"❌ No PDF files found in: {folder_path}")
        return
    
    print(f"\n{'='*70}")
    print(f"BATCH INGESTION: {corpus_name}")
    print(f"Folder: {folder_path}")
    print(f"Files found: {len(pdf_files)}")
    print(f"{'='*70}\n")
    
    success_count = 0
    fail_count = 0
    
    for pdf_file in pdf_files:
        try:
            title = pdf_file.stem.replace('_', ' ').replace('-', ' ').title()
            print(f"\n[{success_count + fail_count + 1}/{len(pdf_files)}] Processing: {pdf_file.name}")
            
            result = ingest_document(
                pdf_path=str(pdf_file),
                title=title,
                corpus_name=corpus_name,
                year=year
            )
            if result:
                success_count += 1
            else:
                fail_count += 1
            
        except Exception as e:
            print(f"❌ Failed to ingest {pdf_file.name}: {e}")
            fail_count += 1
            continue
    
    print(f"\n{'='*70}")
    print(f"BATCH COMPLETE: {corpus_name}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Batch ingest PDFs from folder")
    parser.add_argument("folder", help="Path to folder containing PDFs")
    parser.add_argument("--corpus", required=True, help="Corpus name (e.g., 'Economic Survey 2025-26' or 'Union Budget 2025-26')")
    parser.add_argument("--year", type=int, default=2026, help="Document year")
    parser.add_argument("--pattern", default="*.pdf", help="File pattern (default: *.pdf)")
    
    args = parser.parse_args()
    
    batch_ingest_folder(
        folder_path=args.folder,
        corpus_name=args.corpus,
        year=args.year,
        pattern=args.pattern
    )


if __name__ == "__main__":
    main()
