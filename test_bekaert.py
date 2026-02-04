"""
Test script to verify guardrails allow company-specific questions
Bypasses Firebase auth by calling the RAG function directly
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.conversational_rag import conversational_retrieve
from app.services.guardrails import apply_guardrails, GuardrailViolation

def test_bekaert_question():
    """Test if Bekaert question passes guardrails"""
    question = "whats in this Budget for Bekaert India"
    
    print("=" * 80)
    print(f"Testing question: {question}")
    print("=" * 80)
    
    # Test guardrails
    print("\n1. Testing guardrails...")
    try:
        apply_guardrails(
            query=question,
            answer=None,
            enable_llm_validation=False
        )
        print("✅ PASSED: Guardrails allow the question")
    except GuardrailViolation as e:
        print(f"❌ BLOCKED: {e.message}")
        print(f"   Violation type: {e.violation_type}")
        print(f"   Severity: {e.severity}")
        return
    
    # Test retrieval (this will call Pinecone)
    print("\n2. Testing retrieval from Pinecone...")
    try:
        chunks = conversational_retrieve(
            query=question,
            conversation_history=[],
            top_k=5
        )
        print(f"✅ Retrieved {len(chunks)} chunks")
        
        if chunks:
            print("\nTop 3 most relevant chunks:")
            for i, chunk in enumerate(chunks[:3], 1):
                score = chunk.get('score', 0)
                text_preview = chunk.get('text', '')[:150] + "..."
                source = chunk.get('metadata', {}).get('source', 'Unknown')
                print(f"\n   Chunk {i} (score: {score:.4f}):")
                print(f"   Source: {source}")
                print(f"   Text: {text_preview}")
    except Exception as e:
        print(f"❌ Retrieval failed: {e}")
        return
    
    print("\n" + "=" * 80)
    print("✅ TEST SUCCESSFUL: Question passes all checks!")
    print("=" * 80)

if __name__ == "__main__":
    test_bekaert_question()
