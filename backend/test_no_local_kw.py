"""Test to verify local_kw is not required"""
import requests

url = 'http://127.0.0.1:8000/api/chat'
data = {
    'corpus_id': '122ef605-2d85-43a3-a0d4-918e4c4882cd',
    'message': 'test'
}

try:
    # Test WITHOUT any auth - should get 401, NOT 422 for missing local_kw
    response = requests.post(url, json=data)
    print(f'Status: {response.status_code}')
    error = response.json()
    
    if response.status_code == 401:
        print('✅ Got 401 Unauthorized (expected)')
        print(f'   Detail: {error.get("detail")}')
        print('✅ NO local_kw requirement!')
    elif response.status_code == 422:
        print('❌ Got 422 Validation Error')
        print(f'   Errors: {error.get("detail")}')
        has_local_kw = any('local_kw' in str(err) for err in error.get('detail', []))
        if has_local_kw:
            print('❌ local_kw IS required!')
        else:
            print('✅ local_kw NOT in errors')
    else:
        print(f'Unexpected status: {response.status_code}')
        print(f'Response: {error}')
except Exception as e:
    print(f'Exception: {e}')
