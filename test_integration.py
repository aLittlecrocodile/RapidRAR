import requests
import time
import sys
import os

def test_crack_api():
    base_url = os.environ.get("SERVICE_URL", "http://localhost:80")
    print(f"Testing API at {base_url}")

    # Create a dummy RAR file (simulated interaction) or use an existing one
    # Since we can't easily create a real RAR without 'rar' tool installed in the runner environment (maybe),
    # and the demo kernel "check_password" is hardcoded to "1234",
    # we can send ANY file, as long as the simulated demo kernel is used.
    # Wait, the demo kernel checks valid RAR structure?
    # The `check_rar_password` function in `cuda_kernels.py` just takes `pwd` and checks if it matches "1234".
    # But `src/cracker.py` uses `rarfile` to open it first.
    # So we DO need a valid RAR file.

    # We can try to use the 'test.rar' if we have one, or create one if 'rar' is available.
    # In CI, 'ubuntu-latest' doesn't have 'rar' by default. 
    # But we can perhaps mock the 'rarfile' check if we modify the code, or just install 'rar' in CI.
    # Or, simpler: The user asked to "add an automated test case". 
    # I'll assume we can install 'rar' in the CI runner to generate the file.
    
    # Check health/readiness (simple retry loop)
    # Since we don't have a health endpoint, we'll brute force the crack endpoint.
    
    file_path = "test_1234.rar"
    if not os.path.exists(file_path):
        print(f"File {file_path} not found. Cannot run test.")
        # If we are in the 'kind' workflow, we should have generated this file.
        sys.exit(1)

    url = f"{base_url}/crack"
    
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {
            "mask": "?d?d?d?d",
            "backend": "cpu", # Force CPU as requested
            "concurrent_batches": 4
        }
        
        start_time = time.time()
        print("Sending request...")
        try:
            response = requests.post(url, files=files, data=data, timeout=60)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                json_resp = response.json()
                if json_resp.get("status") == "success" and json_resp.get("password") == "1234":
                    print("✅ Test Passed: Password '1234' found!")
                    sys.exit(0)
                else:
                    print("❌ Test Failed: Password mismatch or failure status.")
                    sys.exit(1)
            else:
                print("❌ Test Failed: Non-200 status code.")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Test Failed: Exception {e}")
            sys.exit(1)

if __name__ == "__main__":
    # Wait loop for service readiness could be handled outside or simple retry here
    # For now, simplistic.
    test_crack_api()
