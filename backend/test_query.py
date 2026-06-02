import requests
import json

# Test query
url = "http://localhost:8001/query"
payload = {
    "query": "what is work through inspection",
    "include_sources": True
}

print("Testing query to backend...")
print(f"Question: {payload['query']}")
print()

try:
    response = requests.post(url, json=payload, timeout=120)
    
    if response.status_code == 200:
        data = response.json()
        print("=" * 60)
        print("SUCCESS! Answer received:")
        print("=" * 60)
        print(data.get('answer', 'No answer'))
        print()
        
        if data.get('sources'):
            print("Sources:")
            for src in data['sources']:
                print(f"  - {src.get('document_name')} ({src.get('relevance_score', 0)*100:.1f}%)")
        
        print()
        print(f"Confidence: {data.get('confidence_score', 0)*100:.1f}%")
        print(f"Time: {data.get('processing_time', 0):.2f}s")
    else:
        print(f"ERROR: Status {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"ERROR: {e}")
