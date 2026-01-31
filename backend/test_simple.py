"""Simple test to verify auth and no local_kw"""
import requests

url = 'http://127.0.0.1:8000/api/chat'
headers = {
    'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X2dvb2dsZV9zdWIiLCJlbWFpbCI6InRlc3RfdXNlckBleGFtcGxlLmNvbSIsImV4cCI6MTc3MDQ1MzE1MiwiaWF0IjoxNzY5ODQ4MzUyfQ.iIJCj88StbjIElvINqErEAvxWPyXx7t0icKULZcbg-4'
}
data = {
    'corpus_id': '122ef605-2d85-43a3-a0d4-918e4c4882cd',
    'message': 'What is the GDP growth?'
}

try:
    response = requests.post(url, json=data, headers=headers)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        result = response.json()
        print(f'✅ SUCCESS!')
        print(f'Conversation ID: {result.get("conversation_id")}')
        print(f'Answer: {result.get("answer")[:100]}...')
        print(f'Evidence items: {len(result.get("evidence", []))}')
    else:
        print(f'❌ Error: {response.text}')
except Exception as e:
    print(f'❌ Exception: {e}')
