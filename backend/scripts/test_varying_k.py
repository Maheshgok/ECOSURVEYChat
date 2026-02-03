"""
Test RAG endpoint with varying k values
Tests questions from test_questions.json with k=3, 5, 10
"""

import json
import requests
import time
from pathlib import Path
import sys

# API endpoint
API_URL = "https://ecosurvey-backend-812016027146.asia-south1.run.app/api/rag-chat"

# K values to test
K_VALUES = [3, 5, 10]

def load_test_questions():
    """Load test questions from JSON file"""
    questions_file = Path(__file__).parent.parent.parent / "test_questions.json"
    with open(questions_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['questions']

def test_question(question_text, k_value, timeout=120):
    """Test a single question with specific k value"""
    try:
        payload = {
            "question": question_text,
            "top_k": k_value
        }
        
        response = requests.post(
            API_URL,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "k_value": k_value,
                "answer": result.get("answer", ""),
                "answer_length": len(result.get("answer", "")),
                "citations": result.get("citations", []),
                "citations_count": len(result.get("citations", [])),
                "context_used": result.get("context_used", 0)
            }
        else:
            return {
                "success": False,
                "k_value": k_value,
                "error": f"HTTP {response.status_code}: {response.text[:200]}"
            }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "k_value": k_value,
            "error": "Request timeout (>120s)"
        }
    except Exception as e:
        return {
            "success": False,
            "k_value": k_value,
            "error": f"{type(e).__name__}: {str(e)[:200]}"
        }

def main():
    print("=" * 80)
    print("Testing RAG Endpoint with Varying K Values")
    print("=" * 80)
    print(f"API: {API_URL}")
    print(f"K Values: {K_VALUES}")
    print()
    
    # Load questions
    questions = load_test_questions()
    total_questions = len(questions)
    
    print(f"Loaded {total_questions} test questions\n")
    
    # Results storage
    results = {
        "metadata": {
            "api_url": API_URL,
            "k_values": K_VALUES,
            "total_questions": total_questions,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "results": []
    }
    
    # Test each question with each k value
    for idx, q in enumerate(questions, 1):
        question_id = q['id']
        question_text = q['question']
        is_adversarial = q.get('is_adversarial', False)
        category = q.get('category', 'unknown')
        
        print(f"\n[{idx}/{total_questions}] {question_id} ({category})")
        print(f"Question: {question_text[:80]}...")
        if is_adversarial:
            print("⚠️  ADVERSARIAL")
        
        question_result = {
            "id": question_id,
            "question": question_text,
            "category": category,
            "is_adversarial": is_adversarial,
            "k_tests": {}
        }
        
        # Test with each k value
        for k in K_VALUES:
            print(f"  Testing k={k}...", end=" ", flush=True)
            result = test_question(question_text, k)
            
            if result["success"]:
                print(f"✓ {result['citations_count']} citations, {result['answer_length']} chars")
                question_result["k_tests"][f"k_{k}"] = result
            else:
                print(f"✗ {result['error'][:80]}")
                question_result["k_tests"][f"k_{k}"] = result
            
            # Rate limiting
            time.sleep(1)
        
        results["results"].append(question_result)
        
        # Progress checkpoint every 10 questions
        if idx % 10 == 0:
            checkpoint_file = Path(__file__).parent.parent / "test_k_results_checkpoint.json"
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Checkpoint saved: {idx}/{total_questions} questions tested\n")
    
    # Save final results
    output_file = Path(__file__).parent.parent / "test_k_results_final.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print("Testing Complete!")
    print(f"Results saved to: {output_file}")
    print("=" * 80)
    
    # Summary statistics
    print("\nSummary Statistics:")
    print("-" * 80)
    
    for k in K_VALUES:
        k_key = f"k_{k}"
        successes = sum(1 for r in results["results"] if r["k_tests"].get(k_key, {}).get("success", False))
        failures = total_questions - successes
        
        if successes > 0:
            avg_citations = sum(
                r["k_tests"][k_key]["citations_count"] 
                for r in results["results"] 
                if r["k_tests"].get(k_key, {}).get("success", False)
            ) / successes
            
            avg_length = sum(
                r["k_tests"][k_key]["answer_length"] 
                for r in results["results"] 
                if r["k_tests"].get(k_key, {}).get("success", False)
            ) / successes
            
            print(f"\nK={k}:")
            print(f"  Success: {successes}/{total_questions} ({successes/total_questions*100:.1f}%)")
            print(f"  Failures: {failures}")
            print(f"  Avg Citations: {avg_citations:.1f}")
            print(f"  Avg Answer Length: {avg_length:.0f} chars")
        else:
            print(f"\nK={k}: All tests failed")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
