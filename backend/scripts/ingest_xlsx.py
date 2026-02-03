"""
XLSX Ingestion Script - Extract data from Excel files
Converts tables to text format for RAG and stores in Pinecone
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import openpyxl
from openai import OpenAI
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

from app.core.pinecone_db import init_pinecone, upsert_vectors

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_text_from_xlsx(xlsx_path: str) -> List[Dict[str, str]]:
    """Extract all data from XLSX as formatted text chunks by sheet"""
    print(f"📊 Opening XLSX: {xlsx_path}")
    
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    chunks = []
    
    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        sheet_text = []
        sheet_text.append(f"Sheet: {sheet_name}")
        
        # Get all data from sheet
        for row in sheet.iter_rows(values_only=True):
            # Skip empty rows
            if all(cell is None or str(cell).strip() == '' for cell in row):
                continue
            
            # Format row as text
            row_text = ' | '.join(str(cell) if cell is not None else '' for cell in row)
            sheet_text.append(row_text)
        
        # Create chunk for this sheet
        chunk_text = '\n'.join(sheet_text)
        chunks.append({
            "text": chunk_text,
            "sheet_name": sheet_name
        })
    
    wb.close()
    
    total_chars = sum(len(c["text"]) for c in chunks)
    print(f"✓ Extracted {total_chars} characters across {len(chunks)} sheets")
    return chunks


def chunk_large_sheet(text: str, max_chars: int = 6000) -> List[str]:
    """Split large sheet text into smaller chunks by rows"""
    if len(text) <= max_chars:
        return [text]
    
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_size = 0
    
    # Keep sheet header
    sheet_header = lines[0] if lines else ""
    
    for i, line in enumerate(lines):
        if i == 0:  # Skip header for now
            continue
            
        line_size = len(line) + 1  # +1 for newline
        
        if current_size + line_size > max_chars and current_chunk:
            # Save current chunk with header
            chunk_text = sheet_header + '\n' + '\n'.join(current_chunk)
            chunks.append(chunk_text)
            current_chunk = []
            current_size = 0
        
        current_chunk.append(line)
        current_size += line_size
    
    # Add remaining chunk
    if current_chunk:
        chunk_text = sheet_header + '\n' + '\n'.join(current_chunk)
        chunks.append(chunk_text)
    
    return chunks


def generate_embedding(text: str) -> List[float]:
    """Generate embedding for text"""
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    return response.data[0].embedding


def ingest_xlsx(
    xlsx_path: str,
    title: str,
    corpus_name: str,
    year: int = 2026
):
    """Ingest XLSX file into RAG system with chunking for large files"""
    print(f"\n{'='*60}")
    print(f"INGESTING XLSX: {title}")
    print(f"{'='*60}\n")
    
    try:
        # Initialize Pinecone
        init_pinecone()
        
        # Generate unique ID
        document_id = str(uuid.uuid4())
        
        print(f"✓ Document ID: {document_id}")
        print(f"✓ Corpus: {corpus_name}")
        
        # Extract text from XLSX (returns list of sheet chunks)
        sheet_chunks = extract_text_from_xlsx(xlsx_path)
        
        # Further chunk large sheets if needed
        all_chunks = []
        for sheet_chunk in sheet_chunks:
            sheet_text = sheet_chunk["text"]
            sheet_name = sheet_chunk["sheet_name"]
            
            # Check if sheet is too large (>6000 chars ~= 8000 tokens max / 1.3 safety)
            if len(sheet_text) > 6000:
                print(f"  ⚠️  Sheet '{sheet_name}' is large ({len(sheet_text)} chars), chunking...")
                sub_chunks = chunk_large_sheet(sheet_text, max_chars=6000)
                for i, sub_chunk in enumerate(sub_chunks):
                    all_chunks.append({
                        "text": sub_chunk,
                        "sheet_name": f"{sheet_name} (part {i+1}/{len(sub_chunks)})"
                    })
            else:
                all_chunks.append(sheet_chunk)
        
        print(f"✓ Created {len(all_chunks)} chunks")
        
        # Generate embeddings for all chunks
        print(f"🔢 Generating embeddings for {len(all_chunks)} chunks...")
        vectors = []
        
        for idx, chunk in enumerate(all_chunks):
            embedding = generate_embedding(chunk["text"])
            
            pinecone_id = f"{document_id}_{idx}"
            vector = {
                "id": pinecone_id,
                "values": embedding,
                "metadata": {
                    "corpus_name": corpus_name,
                    "document_id": document_id,
                    "document_title": title,
                    "sheet_name": chunk["sheet_name"],
                    "year": year,
                    "text": chunk["text"][:40000],  # Limit text size in metadata
                    "source_type": "xlsx"
                }
            }
            vectors.append(vector)
            
            if (idx + 1) % 10 == 0:
                print(f"  Processed {idx + 1}/{len(all_chunks)}")
        
        print(f"✓ Generated {len(vectors)} embeddings")
        
        # Store in Pinecone
        print(f"💾 Upserting {len(vectors)} vectors to Pinecone...")
        upsert_vectors(vectors, batch_size=50)
        print(f"  ✓ Pinecone upsert complete")
        
        print(f"\n✅ SUCCESS: {title}")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def batch_ingest_xlsx_folder(folder_path: str, corpus_name: str, year: int = 2026):
    """Batch ingest all XLSX files in folder"""
    folder = Path(folder_path)
    xlsx_files = list(folder.glob("*.xlsx"))
    
    if not xlsx_files:
        print(f"No XLSX files found in {folder_path}")
        return
    
    print(f"\n{'='*70}")
    print(f"BATCH XLSX INGESTION: {corpus_name}")
    print(f"Files found: {len(xlsx_files)}")
    print(f"{'='*70}\n")
    
    success = 0
    failed = 0
    
    for xlsx_file in xlsx_files:
        try:
            title = xlsx_file.stem.replace('_', ' ').upper()
            print(f"[{success + failed + 1}/{len(xlsx_files)}] {xlsx_file.name}")
            
            result = ingest_xlsx(
                xlsx_path=str(xlsx_file),
                title=title,
                corpus_name=corpus_name,
                year=year
            )
            if result:
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Failed: {e}")
            failed += 1
            continue
    
    print(f"\n✅ Success: {success} | ❌ Failed: {failed}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest XLSX files")
    parser.add_argument("folder", help="Path to folder containing XLSX files")
    parser.add_argument("--corpus", required=True, help="Corpus name")
    parser.add_argument("--year", type=int, default=2026, help="Year")
    
    args = parser.parse_args()
    batch_ingest_xlsx_folder(args.folder, args.corpus, args.year)
