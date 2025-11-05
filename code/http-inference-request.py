"""
HTTP Inference Request - Simple REST API test
"""
import requests
import json

# For port-forwarded service
SERVICE_URL = "http://localhost:8000/v1/chat/completions"

# For in-cluster service (when running from a pod)
# SERVICE_URL = "http://vllm-service.kubeflow.svc.cluster.local:8000/v1/chat/completions"

payload = {
    "model": "facebook/opt-125m",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain distributed machine learning in one sentence."}
    ],
    "max_tokens": 100,
    "temperature": 0.7
}

print(f"Sending request to: {SERVICE_URL}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("-" * 60)

try:
    response = requests.post(
        SERVICE_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    
    response.raise_for_status()
    
    result = response.json()
    print("\n✓ Response received:")
    print("-" * 60)
    print(result["choices"][0]["message"]["content"])
    print("-" * 60)
    print(f"\nTokens used: {result['usage']['total_tokens']}")
    
except requests.exceptions.RequestException as e:
    print(f"\n❌ Error: {e}")
    if hasattr(e.response, 'text'):
        print(f"Response: {e.response.text}")

