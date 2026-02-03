"""
PDF Ingestion Script for Economic Survey
Extracts text, chunks, generates embeddings, and stores in Pinecone
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import fitz  # PyMuPDF
from openai import OpenAI
from typing import List, Dict
import argparse
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

from app.core.pinecone_db import init_pinecone, upsert_vectors

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    """Extract text from PDF by pages"""
    print(f"📄 Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        pages.append({
            'page_num': page_num + 1,
            'text': text.strip()
        })
    
    doc.close()
    print(f"✓ Extracted {len(pages)} pages")
    return pages


def clean_text(text: str) -> str:
    """Aggressively clean text while preserving content"""
    import re
    
    # Remove common page headers/footers
    text = re.sub(r'Economic Survey \d{4}-\d{2}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Page \d+', '', text)
    text = re.sub(r'^\d+$', '', text, flags=re.MULTILINE)  # Standalone page numbers
    
    # Remove copyright and boilerplate
    text = re.sub(r'©.*?Ministry of Finance.*?India', '', text, flags=re.IGNORECASE)
    text = re.sub(r'All rights reserved', '', text, flags=re.IGNORECASE)
    
    # Remove figure/table labels without content
    text = re.sub(r'^(Figure|Table|Chart|Box)\s+[\d\.]+\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    
    # Remove URLs (keep domain name but remove http://)
    text = re.sub(r'https?://', '', text)
    
    # Normalize multiple spaces to single space
    text = re.sub(r' +', ' ', text)
    
    # Remove multiple newlines (keep max 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(line for line in lines if line)
    
    return text.strip()


def chunk_by_sections(pages: List[Dict]) -> List[Dict]:
    """
    Smart chunking by document sections (chapters, sections, subsections)
    Detects headers and creates semantic chunks
    """
    import re
    
    chunks = []
    current_chunk = []
    current_chapter = "Introduction"
    current_section = ""
    chunk_idx = 0
    page_start = 1
    
    # Patterns for section headers
    chapter_pattern = r'^(CHAPTER|Chapter)\s+[IVXLCDM\d]+[:\.]?\s*(.+?)$'
    section_pattern = r'^(\d+\.?\d*)\s+(.+?)$'  # e.g., "1.1 Introduction"
    
    for page in pages:
        page_num = page['page_num']
        text = clean_text(page['text'])
        
        if not text:
            continue
        
        # Split into lines
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line is a chapter header
            chapter_match = re.match(chapter_pattern, line, re.IGNORECASE)
            if chapter_match:
                # Save previous chunk if exists
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    if len(chunk_text) > 100:  # Skip tiny chunks
                        chunks.append({
                            'text': chunk_text,
                            'page_start': page_start,
                            'page_end': page_num - 1,
                            'chunk_index': chunk_idx,
                            'chapter': current_chapter,
                            'section': current_section
                        })
                        chunk_idx += 1
                
                # Start new chunk
                current_chapter = line
                current_section = ""
                current_chunk = [line]
                page_start = page_num
                continue
            
            # Check if line is a section header
            section_match = re.match(section_pattern, line)
            if section_match and len(line) < 100:  # Headers are usually short
                # Save previous chunk if it's getting large
                if len(' '.join(current_chunk)) > 2000:  # ~400 words
                    chunk_text = ' '.join(current_chunk)
                    chunks.append({
                        'text': chunk_text,
                        'page_start': page_start,
                        'page_end': page_num - 1,
                        'chunk_index': chunk_idx,
                        'chapter': current_chapter,
                        'section': current_section
                    })
                    chunk_idx += 1
                    current_chunk = []
                    page_start = page_num
                
                current_section = line
                current_chunk.append(line)
                continue
            
            # Regular text - add to current chunk
            current_chunk.append(line)
            
            # If chunk is getting too large, split it
            if len(' '.join(current_chunk)) > 3000:  # ~600 words max
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'page_start': page_start,
                    'page_end': page_num,
                    'chunk_index': chunk_idx,
                    'chapter': current_chapter,
                    'section': current_section
                })
                chunk_idx += 1
                current_chunk = []
                page_start = page_num
    
    # Don't forget the last chunk
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        if len(chunk_text) > 100:
            chunks.append({
                'text': chunk_text,
                'page_start': page_start,
                'page_end': pages[-1]['page_num'] if pages else 1,
                'chunk_index': chunk_idx,
                'chapter': current_chapter,
                'section': current_section
            })
    
    print(f"✓ Created {len(chunks)} semantic chunks")
    return chunks


def chunk_text(pages: List[Dict], chunk_size: int = 800, overlap: int = 100) -> List[Dict]:
    """
    DEPRECATED: Old word-based chunking
    Use chunk_by_sections() for better semantic chunking
    """
    return chunk_by_sections(pages)


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using OpenAI"""
    print(f"🔢 Generating embeddings for {len(texts)} chunks...")
    
    # OpenAI has a batch limit, process in batches of 100
    batch_size = 100
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=batch
        )
        embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(embeddings)
        print(f"  Processed {min(i + batch_size, len(texts))}/{len(texts)}")
    
    print(f"✓ Generated {len(all_embeddings)} embeddings")
    return all_embeddings


def ingest_document(
    pdf_path: str,
    title: str,
    corpus_name: str = "Economic Survey 2025-26",
    year: int = 2026
):
    """Main ingestion pipeline"""
    print(f"\n{'='*60}")
    print(f"INGESTING: {title}")
    print(f"{'='*60}\n")
    
    try:
        # Initialize Pinecone
        init_pinecone()
        
        # Generate unique IDs
        document_id = str(uuid.uuid4())
        
        print(f"✓ Document ID: {document_id}")
        print(f"✓ Corpus: {corpus_name}")
        
        # Extract text from PDF
        pages = extract_text_from_pdf(pdf_path)
        
        # Chunk text
        chunks_data = chunk_text(pages)
        
        # Generate embeddings
        chunk_texts = [c['text'] for c in chunks_data]
        embeddings = generate_embeddings(chunk_texts)
        
        # Prepare vectors for Pinecone with ALL metadata
        print(f"💾 Storing {len(chunks_data)} chunks in Pinecone...")
        vectors = []
        
        for idx, (chunk_data, embedding) in enumerate(zip(chunks_data, embeddings)):
            pinecone_id = f"{document_id}_{idx}"
            
            # Extract chapter/section for citation (keep short)
            chapter = chunk_data.get('chapter', '')[:100]  # Max 100 chars
            section = chunk_data.get('section', '')[:100]
            
            vectors.append({
                "id": pinecone_id,
                "values": embedding,
                "metadata": {
                    "corpus_name": corpus_name,
                    "document_title": title,
                    "year": year,
                    "page_start": chunk_data['page_start'],
                    "page_end": chunk_data['page_end'],
                    "chapter": chapter,
                    "section": section,
                    "text": chunk_data['text'],
                    "source_type": "pdf"
                }
            })
        
        # Upsert to Pinecone
        print(f"  Upserting {len(vectors)} vectors to Pinecone in batches...")
        upsert_vectors(vectors, batch_size=50)  # Smaller batches to avoid size limits
        print(f"  ✓ Pinecone upsert complete")
        
        print(f"\n✅ SUCCESS: Ingested '{title}'")
        print(f"   📊 {len(pages)} pages")
        print(f"   📦 {len(chunks_data)} chunks")
        print(f"   🔢 {len(embeddings)} embeddings")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR ingesting '{title}': {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Ingest PDF document")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--title", help="Document title", required=True)
    parser.add_argument("--corpus", default="Economic Survey 2025-26", help="Corpus name")
    parser.add_argument("--year", type=int, default=2026, help="Year")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"❌ File not found: {args.pdf_path}")
        return
    
    success = ingest_document(args.pdf_path, args.title, args.corpus, args.year)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
