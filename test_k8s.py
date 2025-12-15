import requests
import sys
import os
import time

def test_k8s_deployment(url, rar_file_path):
    """
    Tests the deployed RapidRAR instance by sending a known RAR file.
    """
    print(f"Testing deployment at {url} with {rar_file_path}...")
    
    if not os.path.exists(rar_file_path):
        print(f"Error: Test file {rar_file_path} not found.")
        sys.exit(1)

    try:
        # Create a dummy password-protected RAR if not exists or use provided
        # For this script we assume it exists.
        
        with open(rar_file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'min_length': 1,
                'max_length': 4,
                'mask': '?d?d?d?d' # Assume numeric for quick test
            }
            
            # Including X-API-Key header for authentication
            # Using default 'dev-secret' which matches the fallback in api.py
            headers = {"X-API-Key": "dev-secret"}

            start = time.time()
            response = requests.post(f"{url}/crack", files=files, data=data, headers=headers, timeout=30)
            elapsed = time.time() - start
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                json_resp = response.json()
                if json_resp.get('status') == 'success':
                    print("SUCCESS: Password recovered!")
                    return True
                else:
                    print(f"FAILURE: API returned {json_resp.get('status')}")
                    return False
            else:
                print("FAILURE: Non-200 status code")
                return False

    except Exception as e:
        print(f"ERROR: Exception occurred: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_k8s.py <ingress_url> <test_rar_file>")
        sys.exit(1)
        
    url = sys.argv[1]
    rar_file = sys.argv[2]
    
    success = test_k8s_deployment(url, rar_file)
    if not success:
        sys.exit(1)
