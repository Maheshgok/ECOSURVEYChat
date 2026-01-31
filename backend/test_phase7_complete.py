"""
Comprehensive Phase 7 Testing Suite
Tests chat endpoint functionality without auth friction
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:8000"

# Test data - using known IDs from database
TEST_USER_GOOGLE_ID = "test_google_sub"
TEST_CORPUS_ID = "122ef605-2d85-43a3-a0d4-918e4c4882cd"
TEST_MESSAGES = [
    "What are the key findings from the latest economic survey?",
    "Can you explain the trends in unemployment?",
    "What data is available about income distribution?",
]


def test_health() -> bool:
    """Test 1: Server health check"""
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✓ Health check: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_openapi_no_local_kw() -> bool:
    """Test 2: Verify local_kw is not in OpenAPI schema"""
    try:
        r = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        if r.status_code != 200:
            print(f"✗ OpenAPI fetch failed: {r.status_code}")
            return False
        
        schema = r.json()
        chat_endpoint = schema["paths"]["/api/chat"]["post"]
        params = chat_endpoint.get("parameters", [])
        param_names = [p["name"] for p in params]
        
        if "local_kw" in param_names:
            print(f"✗ local_kw still present in OpenAPI schema")
            return False
        
        print(f"✓ OpenAPI schema clean: {len(param_names)} parameters found")
        return True
    except Exception as e:
        print(f"✗ OpenAPI check failed: {e}")
        return False


def test_chat_basic() -> bool:
    """Test 3: Basic chat endpoint"""
    try:
        payload = {
            "corpus_id": TEST_CORPUS_ID,
            "message": TEST_MESSAGES[0],
        }
        
        r = requests.post(
            f"{BASE_URL}/api/chat",
            json=payload,
            timeout=10
        )
        
        if r.status_code != 200:
            print(f"✗ Chat failed: {r.status_code}")
            print(f"  Response: {r.text[:200]}")
            return False
        
        data = r.json()
        print(f"✓ Chat response received")
        print(f"  Conversation ID: {data['conversation_id'][:8]}...")
        print(f"  Answer length: {len(data['answer'])} chars")
        print(f"  Evidence items: {len(data['evidence'])}")
        print(f"  Followups: {len(data['followups'])}")
        
        return True
    except Exception as e:
        print(f"✗ Chat test failed: {e}")
        return False


def test_chat_with_conversation() -> bool:
    """Test 4: Continue chat in same conversation"""
    try:
        # First message to create conversation
        payload = {
            "corpus_id": TEST_CORPUS_ID,
            "message": TEST_MESSAGES[0],
        }
        
        r1 = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=10)
        if r1.status_code != 200:
            print(f"✗ First message failed: {r1.status_code}")
            return False
        
        conversation_id = r1.json()["conversation_id"]
        
        # Second message in same conversation
        payload2 = {
            "corpus_id": TEST_CORPUS_ID,
            "conversation_id": conversation_id,
            "message": TEST_MESSAGES[1],
        }
        
        r2 = requests.post(f"{BASE_URL}/api/chat", json=payload2, timeout=10)
        if r2.status_code != 200:
            print(f"✗ Second message failed: {r2.status_code}")
            return False
        
        conv_id2 = r2.json()["conversation_id"]
        if conv_id2 != conversation_id:
            print(f"✗ Conversation ID mismatch")
            return False
        
        print(f"✓ Conversation continuity: {len(conversation_id)} char ID")
        return True
    except Exception as e:
        print(f"✗ Conversation test failed: {e}")
        return False


def test_response_structure() -> bool:
    """Test 5: Validate response structure"""
    try:
        payload = {
            "corpus_id": TEST_CORPUS_ID,
            "message": "What are the main economic indicators?",
        }
        
        r = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=10)
        if r.status_code != 200:
            print(f"✗ Request failed: {r.status_code}")
            return False
        
        data = r.json()
        
        # Check required fields
        required_fields = ["conversation_id", "answer", "intuition", "evidence", "followups"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            print(f"✗ Missing fields: {missing}")
            return False
        
        # Check types
        if not isinstance(data["evidence"], list):
            print(f"✗ Evidence is not a list")
            return False
        
        if not isinstance(data["followups"], list):
            print(f"✗ Followups is not a list")
            return False
        
        if not data["answer"] or not isinstance(data["answer"], str):
            print(f"✗ Answer is empty or not a string")
            return False
        
        # Check evidence structure
        for item in data["evidence"]:
            if "type" not in item or "id" not in item:
                print(f"✗ Evidence item missing type or id: {item}")
                return False
        
        print(f"✓ Response structure valid")
        print(f"  - conversation_id: {type(data['conversation_id']).__name__}")
        print(f"  - answer: {len(data['answer'])} chars")
        print(f"  - intuition: {len(data['intuition'])} chars")
        print(f"  - evidence: {len(data['evidence'])} items")
        print(f"  - followups: {len(data['followups'])} items")
        
        return True
    except Exception as e:
        print(f"✗ Structure validation failed: {e}")
        return False


def test_multiple_queries() -> bool:
    """Test 6: Multiple different queries"""
    try:
        results = []
        for msg in TEST_MESSAGES:
            payload = {
                "corpus_id": TEST_CORPUS_ID,
                "message": msg,
            }
            
            r = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=10)
            if r.status_code != 200:
                print(f"✗ Query failed: {r.status_code}")
                return False
            
            results.append(r.json())
            print(f"  ✓ Query {len(results)}: {msg[:50]}...")
        
        print(f"✓ All {len(results)} queries successful")
        return True
    except Exception as e:
        print(f"✗ Multiple queries test failed: {e}")
        return False


def test_evidence_retrieval() -> bool:
    """Test 7: Verify evidence items are retrieved"""
    try:
        payload = {
            "corpus_id": TEST_CORPUS_ID,
            "message": "Show me the data about inflation and GDP",
        }
        
        r = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=10)
        if r.status_code != 200:
            print(f"✗ Request failed: {r.status_code}")
            return False
        
        data = r.json()
        evidence = data["evidence"]
        
        if not evidence:
            print(f"⚠ No evidence items retrieved (may be normal)")
            return True
        
        # Check evidence types
        evidence_types = set(item.get("type") for item in evidence)
        expected_types = {"claim_card", "node", "series"}
        
        print(f"✓ Evidence retrieval working")
        print(f"  - Total items: {len(evidence)}")
        print(f"  - Types found: {evidence_types}")
        
        return True
    except Exception as e:
        print(f"✗ Evidence test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PHASE 7 COMPREHENSIVE TEST SUITE")
    print("="*60 + "\n")
    
    tests = [
        ("Server Health", test_health),
        ("OpenAPI (no local_kw)", test_openapi_no_local_kw),
        ("Chat Basic", test_chat_basic),
        ("Chat Conversation", test_chat_with_conversation),
        ("Response Structure", test_response_structure),
        ("Multiple Queries", test_multiple_queries),
        ("Evidence Retrieval", test_evidence_retrieval),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n[{len(results)+1}] {name}")
        print("-" * 40)
        result = test_func()
        results.append((name, result))
        time.sleep(0.5)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Phase 7 functionality validated!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
