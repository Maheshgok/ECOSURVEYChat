"""
Test Pinecone Query - Retrieve relevant chunks
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from openai import OpenAI
from dotenv import load_dotenv
from app.core.pinecone_db import get_pinecone_index

# Load environment variables
load_dotenv()

# Initialize clients
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_query_embedding(query: str):
    """Generate embedding for the query"""
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=query
    )
    return response.data[0].embedding


def search_pinecone(query: str, top_k: int = 5):
    """Search Pinecone for relevant chunks"""
    print(f"\n{'='*70}")
    print(f"QUERY: {query}")
    print(f"{'='*70}\n")
    
    # Generate embedding for query
    print("🔍 Generating query embedding...")
    query_embedding = generate_query_embedding(query)
    
    # Search Pinecone
    print(f"📊 Searching Pinecone for top {top_k} matches...\n")
    index = get_pinecone_index()
    
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )
    
    # Display results
    print(f"✅ Found {len(results['matches'])} results:\n")
    
    for i, match in enumerate(results['matches'], 1):
        print(f"\n{'='*70}")
        print(f"RESULT #{i}")
        print(f"{'='*70}")
        print(f"Score: {match['score']:.4f}")
        print(f"ID: {match['id']}")
        
        metadata = match.get('metadata', {})
        print(f"\nMetadata:")
        print(f"  Corpus: {metadata.get('corpus_name', 'N/A')}")
        print(f"  Document: {metadata.get('document_title', 'N/A')}")
        print(f"  Year: {metadata.get('year', 'N/A')}")
        print(f"  Source Type: {metadata.get('source_type', 'N/A')}")
        
        # PDF-specific metadata
        if metadata.get('source_type') == 'pdf':
            chapter = metadata.get('chapter', '')
            section = metadata.get('section', '')
            pages = f"{metadata.get('page_start', '?')}-{metadata.get('page_end', '?')}"
            print(f"  Pages: {pages}")
            if chapter:
                print(f"  Chapter: {chapter}")
            if section:
                print(f"  Section: {section}")
        
        # XLSX-specific metadata
        elif metadata.get('source_type') == 'xlsx':
            sheet_name = metadata.get('sheet_name', 'N/A')
            print(f"  Sheet: {sheet_name}")
        
        # Display text preview
        text = metadata.get('text', '')
        if text:
            preview = text[:500] + "..." if len(text) > 500 else text
            print(f"\nText Preview:")
            print(f"{preview}")
    
    print(f"\n{'='*70}\n")
    return results


def main():
    # Example queries
    queries = [
        "What is India's GDP growth rate?",
        "Tell me about inflation trends",
        "What are the key economic indicators?"
    ]
    
    print("\n" + "="*70)
    print("PINECONE QUERY TEST")
    print("="*70)
    
    # Allow custom query or use examples
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        search_pinecone(query, top_k=3)
    else:
        print("\nTesting with example queries...\n")
        for query in queries:
            search_pinecone(query, top_k=3)
            input("\nPress Enter to continue to next query...")


if __name__ == "__main__":
    main()
