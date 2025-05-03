import requests
import json

def test_openstack_api():
    print("Testing OpenStack API endpoints...")
    
    # Step 1: Authenticate and get token
    print("\n1. Authenticating...")
    auth_url = "https://api-ap-south-mum-1.openstack.acecloudhosting.com:5000/v3/auth/tokens"
    auth_data = {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "domain": {"name": "Default"},
                        "name": "Hackathon_AIML_1",
                        "password": "Hackathon_AIML_1@567"
                    }
                }
            },
        }
    }
    
    auth_response = requests.post(
        auth_url,
        headers={"Content-Type": "application/json"},
        data=json.dumps(auth_data),
        verify=True
    )
    
    print(f"Authentication status code: {auth_response.status_code}")
    
    if auth_response.status_code != 201:
        print(f"Authentication failed: {auth_response.text}")
        return
    
    token = auth_response.headers.get('X-Subject-Token')
    print(f"Successfully obtained token: {token[:10]}...")
    
    # Get project ID from token response
    project_id = None
    try:
        auth_data = auth_response.json()
        if 'token' in auth_data and 'project' in auth_data['token']:
            project_id = auth_data['token']['project']['id']
            print(f"Project ID from token: {project_id}")
    except Exception as e:
        print(f"Could not get project ID from token: {str(e)}")
    
    # Use hardcoded project ID if not available from token
    if not project_id:
        project_id = "a02b14bcfca64e44bd68f2d00d8555b5"  # Note: corrected project ID
        print(f"Using hardcoded project ID: {project_id}")
    
    # Step 2: Get compute limits
    print("\n2. Getting compute limits...")
    compute_url = "https://api-ap-south-mum-1.openstack.acecloudhosting.com:8774/v2.1/limits"
    compute_response = requests.get(
        compute_url,
        headers={"X-Auth-Token": token}
    )
    
    print(f"Compute limits status code: {compute_response.status_code}")
    if compute_response.status_code == 200:
        compute_data = compute_response.json()
        print("Compute limits retrieved successfully:")
        print(json.dumps(compute_data, indent=2)[:500] + "..." if len(json.dumps(compute_data)) > 500 else json.dumps(compute_data, indent=2))
    else:
        print(f"Failed to get compute limits: {compute_response.text}")
    
    # Step 3: Get servers data
    print("\n3. Getting servers data...")
    servers_url = "https://api-ap-south-mum-1.openstack.acecloudhosting.com:8774/v2.1/servers/detail"
    servers_response = requests.get(
        servers_url,
        headers={"X-Auth-Token": token}
    )
    
    print(f"Servers data status code: {servers_response.status_code}")
    if servers_response.status_code == 200:
        servers_data = servers_response.json()
        print("Servers data retrieved successfully:")
        print(json.dumps(servers_data, indent=2)[:500] + "..." if len(json.dumps(servers_data)) > 500 else json.dumps(servers_data, indent=2))
    else:
        print(f"Failed to get servers data: {servers_response.text}")
    
    # Step 4: Get volumes data
    print("\n4. Getting volumes data...")
    volumes_url = f"https://api-ap-south-mum-1.openstack.acecloudhosting.com:8776/v3/{project_id}/volumes/detail"
    print(f"Volumes URL: {volumes_url}")
    volumes_response = requests.get(
        volumes_url,
        headers={"X-Auth-Token": token}
    )
    
    print(f"Volumes data status code: {volumes_response.status_code}")
    if volumes_response.status_code == 200:
        volumes_data = volumes_response.json()
        print("Volumes data retrieved successfully:")
        print(json.dumps(volumes_data, indent=2)[:500] + "..." if len(json.dumps(volumes_data)) > 500 else json.dumps(volumes_data, indent=2))
        
        # Calculate total storage
        total_storage = sum(volume.get('size', 0) for volume in volumes_data.get('volumes', []))
        print(f"\nTotal storage: {total_storage} GB")
    else:
        print(f"Failed to get volumes data: {volumes_response.text}")
    
    # Step 5: Format and combine all data (similar to production usage)
    print("\n5. Formatting combined usage data...")
    try:
        limits = compute_response.json().get('limits', {}).get('absolute', {})
        servers = servers_response.json().get('servers', [])
        volumes = volumes_data.get('volumes', []) if volumes_response.status_code == 200 else []
        
        usage_result = {
            "summary": {
                "total_servers": len(servers),
                "active_servers": sum(1 for server in servers if server.get('status') == 'ACTIVE'),
                "total_vcpus_used": limits.get('totalCoresUsed', 0),
                "total_ram_used_gb": limits.get('totalRAMUsed', 0) / 1024,
                "total_volumes": len(volumes),
                "total_storage_gb": sum(volume.get('size', 0) for volume in volumes)
            }
        }
        
        print("Formatted usage data:")
        print(json.dumps(usage_result, indent=2))
    except Exception as e:
        print(f"Error formatting usage data: {str(e)}")

if __name__ == "__main__":
    test_openstack_api() 