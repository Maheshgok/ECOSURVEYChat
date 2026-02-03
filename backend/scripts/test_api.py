"""
Test RAG Chat API
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def test_rag_chat(question: str):
    """Test the RAG chat endpoint"""
    url = f"{BASE_URL}/rag-chat"
    
    payload = {
        "question": question,
        "top_k": 3
    }
    
    print(f"\n{'='*70}")
    print(f"QUESTION: {question}")
    print(f"{'='*70}\n")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            
            print("ANSWER:")
            print(data["answer"])
            print(f"\n{'-'*70}")
            print(f"CITATIONS ({len(data['citations'])}):")
            
            for i, citation in enumerate(data["citations"], 1):
                print(f"\n{i}. {citation['document']} (Score: {citation['score']:.4f})")
                print(f"   Source: {citation['source']}")
                if citation.get('page'):
                    print(f"   Pages: {citation['page']}")
                if citation.get('sheet'):
                    print(f"   Sheet: {citation['sheet']}")
                if citation.get('chapter'):
                    print(f"   Chapter: {citation['chapter'][:80]}...")
                    
            print(f"\n{'-'*70}")
            print(f"Context chunks used: {data['context_used']}")
            
        else:
            print(f"ERROR {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to server. Make sure it's running at http://127.0.0.1:8000")
    except Exception as e:
        print(f"❌ ERROR: {e}")


if __name__ == "__main__":
    # Test questions
    questions = [
        "What is India's GDP growth rate for 2025-26?",
        "Tell me about inflation trends in India",
        "What are India's export statistics?"
    ]
    
    for question in questions:
        test_rag_chat(question)
        print("\n" + "="*70 + "\n")
