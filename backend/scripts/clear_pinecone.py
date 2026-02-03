"""
Clear all vectors from Pinecone index
Use this before re-ingesting with new chunking strategy
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from app.core.pinecone_db import get_pinecone_index


def clear_all_vectors():
    """Delete all vectors from Pinecone index"""
    print("⚠️  WARNING: This will delete ALL vectors from Pinecone index!")
    print(f"Index: {os.getenv('PINECONE_INDEX_NAME')}")
    
    response = input("\nAre you sure? Type 'yes' to confirm: ")
    
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    try:
        print("\n🗑️  Deleting all vectors...")
        index = get_pinecone_index()
        index.delete(delete_all=True)
        print("✅ Successfully cleared all vectors from Pinecone!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    clear_all_vectors()
