"""
Generate responses for all test questions
"""

import json
import requests
from datetime import datetime
import time
from pathlib import Path
import os

# API endpoint - GCP Cloud Run
API_URL = os.getenv("CHAT_API_URL", "https://ecosurvey-backend-812016027146.asia-south1.run.app/api/rag-chat")

def load_test_questions(file_path):
    """Load test questions from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                raise ValueError(f"File is empty: {file_path}")
            data = json.loads(content)
        return data
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"File path: {file_path}")
        raise
    except Exception as e:
        print(f"Error loading file: {e}")
        raise

def call_api(question, top_k=5, retries=3):
    """Call the RAG API with retry logic"""
    for attempt in range(retries):
        try:
            response = requests.post(
                API_URL,
                json={"question": question, "top_k": top_k},
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"  Attempt {attempt + 1} failed: {str(e)}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return {"error": str(e), "answer": "ERROR: API call failed", "citations": [], "context_used": 0}

def generate_responses(test_data, max_questions=None):
    """Generate responses and add answer field to each question"""
    questions = test_data.get('questions', [])
    
    if max_questions:
        questions = questions[:max_questions]
    
    print(f"Processing {len(questions)} questions...")
    print("=" * 80)
    
    for i, q_data in enumerate(questions, 1):
        q_id = q_data.get('id', f'q{i:03d}')
        question = q_data.get('question', '')
        is_adversarial = q_data.get('is_adversarial', False)
        category = q_data.get('category', 'unknown')
        
        print(f"\n[{i}/{len(questions)}] {q_id} ({category})")
        print(f"Question: {question[:80]}...")
        if is_adversarial:
            print("⚠️  ADVERSARIAL")
        
        # Call API
        result = call_api(question, top_k=5)
        
        # Add answer field directly to question object
        q_data['answer'] = result.get('answer', '')
        
        # Show snippet of answer
        if result.get('answer'):
            snippet = result['answer'][:150].replace('\n', ' ')
            print(f"Answer: {snippet}...")
        else:
            print(f"❌ Error: {result.get('error', 'No answer')}")
        
        # Rate limiting - small delay between requests
        if i < len(questions):
            time.sleep(0.5)
    
    return test_data

def save_responses(test_data, output_file):
    """Save updated test data with answers to JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Responses saved to: {output_file}")

def main():
    # Paths
    project_root = Path(__file__).parent.parent.parent
    test_questions_file = project_root / "test_questions_restored.json"
    output_file = project_root / "test_questions_with_answers.json"
    
    # Check if test questions file exists
    if not test_questions_file.exists():
        print(f"❌ Test questions file not found: {test_questions_file}")
        return
    
    # Load test questions
    print(f"Loading test questions from: {test_questions_file}")
    test_data = load_test_questions(test_questions_file)
    
    total_questions = len(test_data.get('questions', []))
    print(f"Found {total_questions} questions in test suite")
    print(f"Suite: {test_data.get('test_suite_name', 'Unknown')}")
    print(f"API URL: {API_URL}")
    
    # Generate responses (all questions)
    test_data = generate_responses(test_data, max_questions=None)
    
    # Save to file
    save_responses(test_data, output_file)
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    questions = test_data.get('questions', [])
    successful = sum(1 for q in questions if q.get('answer') and not q['answer'].startswith('ERROR'))
    failed = sum(1 for q in questions if not q.get('answer') or q['answer'].startswith('ERROR'))
    adversarial = sum(1 for q in questions if q.get('is_adversarial'))
    
    print(f"Total questions processed: {len(questions)}")
    print(f"Successful responses: {successful}")
    print(f"Failed responses: {failed}")
    print(f"Adversarial questions: {adversarial}")
    
    print(f"\nOutput file: {output_file}")

if __name__ == "__main__":
    main()
