"""Test Phase 7 chat endpoint"""
import urllib.request
import json

url = 'http://127.0.0.1:8000/api/chat'
data = json.dumps({
    'corpus_id': '122ef605-2d85-43a3-a0d4-918e4c4882cd',
    'message': 'What is the GDP growth forecast?'
}).encode('utf-8')

headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X2dvb2dsZV9zdWIiLCJlbWFpbCI6InRlc3RfdXNlckBleGFtcGxlLmNvbSIsImV4cCI6MTc3MDQ1MzE1MiwiaWF0IjoxNzY5ODQ4MzUyfQ.iIJCj88StbjIElvINqErEAvxWPyXx7t0icKULZcbg-4'
}

req = urllib.request.Request(url, data=data, headers=headers)
try:
    response = urllib.request.urlopen(req)
    result = json.loads(response.read().decode('utf-8'))
    print('✅ Chat endpoint test PASSED')
    print(f'Response keys: {list(result.keys())}')
    print(f'Conversation ID: {result.get("conversation_id")}')
    print(f'Answer: {result.get("answer")[:100]}...')
    print(f'Evidence items: {len(result.get("evidence", []))}')
    print(f'Follow-ups: {len(result.get("followups", []))}')
except urllib.error.HTTPError as e:
    print(f'❌ HTTP Error {e.code}')
    print(e.read().decode('utf-8'))
except Exception as e:
    print(f'❌ Error: {e}')
