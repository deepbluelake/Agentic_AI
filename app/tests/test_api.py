from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

@patch("app.services.openstack_service.OpenStackService.create_vm")
def test_create_vm(mock_create_vm):
    # Mock return value
    mock_create_vm.return_value = {
        "id": "vm-123",
        "name": "dev-box",
        "status": "ACTIVE",
        "ip": "10.0.0.2"
    }

    response = client.post("/nl/process", json={"text": "Create an S.4 VM named dev‑box."})
    
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["requires_confirmation"] == True
    assert "create" in json_resp["response"].lower()
    assert "dev-box" in json_resp["response"].lower()

@patch("app.services.openstack_service.OpenStackService.resize_vm")
def test_resize_vm(mock_resize_vm):
    mock_resize_vm.return_value = {
        "id": "vm-123",
        "name": "dev-box",
        "status": "VERIFY_RESIZE",
        "flavor": "M.8"
    }

    response = client.post("/nl/process", json={"text": "Resize dev‑box to flavor M.8."})
    
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["requires_confirmation"] == True
    assert "resize" in json_resp["response"].lower()
    assert "dev-box" in json_resp["response"].lower()
