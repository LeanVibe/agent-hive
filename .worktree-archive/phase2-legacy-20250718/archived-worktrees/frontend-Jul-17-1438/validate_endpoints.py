
import requests
import json

def validate_endpoints():
    base_url = "http://localhost:8000"
    endpoints = ["/api/metrics", "/api/health", "/api/message-bus/status"]
    results = []
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            results.append({
                "endpoint": endpoint,
                "status": response.status_code,
                "valid": response.status_code == 200
            })
        except Exception as e:
            results.append({
                "endpoint": endpoint,
                "status": "error",
                "error": str(e)
            })
    
    return results

if __name__ == "__main__":
    results = validate_endpoints()
    print(json.dumps(results, indent=2))
