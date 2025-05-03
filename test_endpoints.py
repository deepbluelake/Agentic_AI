import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def wait_for_server(max_retries=5, delay=2):
    """Wait for the server to become available"""
    for i in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/")
            if response.status_code == 200:
                print("Server is running!")
                return True
        except requests.exceptions.ConnectionError:
            if i < max_retries - 1:
                print(f"Waiting for server to start... (attempt {i+1}/{max_retries})")
                time.sleep(delay)
            else:
                print("Error: Could not connect to server. Make sure to run 'python run.py' first.")
                return False
    return False

def test_nl_process(text):
    print(f"\nTesting with text: {text}")
    try:
        response = requests.post(
            f"{BASE_URL}/nl/process",
            json={"text": text}
        )
        print(f"Status code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {str(e)}")
        return None

# Test cases
test_cases = [
    "Create a VM named dev-box",
    "Resize dev-box to flavor M.8",
    "Delete dev-box",
    "Show usage"
]

if __name__ == "__main__":
    print("Testing NLP endpoints...")
    
    # Check if server is running
    if not wait_for_server():
        sys.exit(1)
    
    # Run tests
    for test_case in test_cases:
        test_nl_process(test_case)