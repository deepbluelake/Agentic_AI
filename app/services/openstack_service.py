import openstack
from typing import Optional, Dict, Any
from datetime import datetime
from app.database import SessionLocal, OperationLog  # Corrected import


class OpenStackService:
    def __init__(self, conn: openstack.connection.Connection):
        self.conn = conn

    def create_vm(self, name: str, flavor: str, image: str, network: Optional[str] = None) -> Dict[str, Any]:
        try:
            flavor_obj = self.conn.compute.find_flavor(flavor)
            if not flavor_obj:
                raise ValueError(f"Flavor '{flavor}' not found")

            image_obj = self.conn.image.find_image(image)
            if not image_obj:
                raise ValueError(f"Image '{image}' not found")

            networks = None
            if network:
                net_obj = self.conn.network.find_network(network)
                if not net_obj:
                    raise ValueError(f"Network '{network}' not found")
                networks = [{"uuid": net_obj.id}]  # Networks list creation

            server = self.conn.compute.create_server(
                name=name,
                flavor_id=flavor_obj.id,
                image_id=image_obj.id,
                networks=networks
            )
            server = self.conn.compute.wait_for_server(server)

            ip_address = None
            for network_data in server.addresses.values():
                for address in network_data:
                    if address.get('addr'):
                        ip_address = address.get('addr')
                        break

            result = {
                "id": server.id,
                "name": server.name,
                "status": server.status,
                "ip": ip_address or server.access_ipv4
            }

            self.log_operation("CREATE_VM", name, {"flavor": flavor, "image": image}, "SUCCESS")
            return result
        except Exception as e:
            self.log_operation("CREATE_VM", name, {"flavor": flavor, "image": image}, "FAILED", str(e))
            raise Exception(f"Failed to create VM: {str(e)}")

    def resize_vm(self, vm_name: str, new_flavor: str) -> Dict[str, Any]:
        try:
            server = self.conn.compute.find_server(vm_name)
            if not server:
                raise ValueError(f"VM '{vm_name}' not found")

            flavor = self.conn.compute.find_flavor(new_flavor)
            if not flavor:
                raise ValueError(f"Flavor '{new_flavor}' not found")

            self.conn.compute.resize_server(server, flavor.id)
            server = self.conn.compute.wait_for_server(server, status='VERIFY_RESIZE')
            self.conn.compute.confirm_server_resize(server)
            server = self.conn.compute.wait_for_server(server)

            result = {
                "id": server.id,
                "name": server.name,
                "status": server.status,
                "flavor": new_flavor
            }

            self.log_operation("RESIZE_VM", vm_name, {"flavor": new_flavor}, "SUCCESS")
            return result
        except Exception as e:
            self.log_operation("RESIZE_VM", vm_name, {"flavor": new_flavor}, "FAILED", str(e))
            raise Exception(f"Failed to resize VM: {str(e)}")

    def delete_vm(self, vm_name: str) -> Dict[str, Any]:
        try:
            server = self.conn.compute.find_server(vm_name)
            if not server:
                raise ValueError(f"VM '{vm_name}' not found")

            self.conn.compute.delete_server(server)
            self.conn.compute.wait_for_delete(server)

            result = {"name": vm_name, "status": "deleted"}
            self.log_operation("DELETE_VM", vm_name, {}, "SUCCESS")
            return result
        except Exception as e:
            self.log_operation("DELETE_VM", vm_name, {}, "FAILED", str(e))
            raise Exception(f"Failed to delete VM: {str(e)}")

    def create_network(self, name: str, cidr: str = "192.168.0.0/24") -> Dict[str, Any]:
        try:
            network = self.conn.network.create_network(name=name)
            subnet = self.conn.network.create_subnet(
                name=f"{name}-subnet",
                network_id=network.id,
                ip_version=4,
                cidr=cidr
            )

            result = {
                "network_id": network.id,
                "network_name": network.name,
                "subnet_id": subnet.id,
                "subnet_name": subnet.name,
                "cidr": subnet.cidr
            }

            self.log_operation("CREATE_NETWORK", name, {"cidr": cidr}, "SUCCESS")
            return result
        except Exception as e:
            self.log_operation("CREATE_NETWORK", name, {"cidr": cidr}, "FAILED", str(e))
            raise Exception(f"Failed to create network: {str(e)}")

    def delete_network(self, network_name: str) -> Dict[str, Any]:
        try:
            network = self.conn.network.find_network(network_name)
            if not network:
                raise ValueError(f"Network '{network_name}' not found")

            for subnet in self.conn.network.subnets():
                if subnet.network_id == network.id:
                    self.conn.network.delete_subnet(subnet)

            self.conn.network.delete_network(network)

            result = {"name": network_name, "status": "deleted"}
            self.log_operation("DELETE_NETWORK", network_name, {}, "SUCCESS")
            return result
        except Exception as e:
            self.log_operation("DELETE_NETWORK", network_name, {}, "FAILED", str(e))
            raise Exception(f"Failed to delete network: {str(e)}")

    def create_volume(self, name: str, size: int) -> Dict[str, Any]:
        try:
            volume = self.conn.block_storage.create_volume(name=name, size=size)
            volume = self.conn.block_storage.wait_for_status(volume)

            result = {
                "id": volume.id,
                "name": volume.name,
                "size": volume.size,
                "status": volume.status
            }

            self.log_operation("CREATE_VOLUME", name, {"size": size}, "SUCCESS")
            return result
        except Exception as e:
            self.log_operation("CREATE_VOLUME", name, {"size": size}, "FAILED", str(e))
            raise Exception(f"Failed to create volume: {str(e)}")

    def delete_volume(self, volume_name: str) -> Dict[str, Any]:
        try:
            volume = self.conn.block_storage.find_volume(volume_name)
            if not volume:
                raise ValueError(f"Volume '{volume_name}' not found")

            self.conn.block_storage.delete_volume(volume)
            self.conn.block_storage.wait_for_delete(volume)

            result = {"name": volume_name, "status": "deleted"}
            self.log_operation("DELETE_VOLUME", volume_name, {}, "SUCCESS")
            return result
        except Exception as e:
            self.log_operation("DELETE_VOLUME", volume_name, {}, "FAILED", str(e))
            raise Exception(f"Failed to delete volume: {str(e)}")

    def get_usage(self) -> Dict[str, Any]:
        try:
            import requests
            import json
            
            # Step 1: Authenticate and get token
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
                    }
                }
            }
            
            auth_response = requests.post(
                auth_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(auth_data),
                verify=True
            )
            
            if auth_response.status_code != 201:
                raise Exception(f"Authentication failed: {auth_response.text}")
                
            token = auth_response.headers.get('X-Subject-Token')
            
            # Get project ID from token response if available
            project_id = None
            try:
                auth_data = auth_response.json()
                if 'token' in auth_data and 'project' in auth_data['token']:
                    project_id = auth_data['token']['project']['id']
            except Exception:
                pass
            
            # Use hardcoded project ID if not available from token
            if not project_id:
                project_id = "a02b14bcfca64e44bd68f2d00d8555b5"
            
            # Step 2: Get compute limits
            compute_url = "https://api-ap-south-mum-1.openstack.acecloudhosting.com:8774/v2.1/limits"
            compute_response = requests.get(
                compute_url,
                headers={"X-Auth-Token": token}
            )
            
            if compute_response.status_code != 200:
                raise Exception(f"Failed to get compute limits: {compute_response.text}")
                
            compute_data = compute_response.json()
            limits = compute_data.get('limits', {}).get('absolute', {})
            
            # Step 3: Get servers data
            servers_url = "https://api-ap-south-mum-1.openstack.acecloudhosting.com:8774/v2.1/servers/detail"
            servers_response = requests.get(
                servers_url,
                headers={"X-Auth-Token": token}
            )
            
            servers_data = []
            if servers_response.status_code == 200:
                servers_data = servers_response.json().get('servers', [])
            
            # Step 4: Get volume data
            volumes_url = f"https://api-ap-south-mum-1.openstack.acecloudhosting.com:8776/v3/{project_id}/volumes/detail"
            volumes_response = requests.get(
                volumes_url,
                headers={"X-Auth-Token": token}
            )
            
            volumes_data = []
            total_storage_gb = 0
            if volumes_response.status_code == 200:
                volumes_data = volumes_response.json().get('volumes', [])
                total_storage_gb = sum(volume.get('size', 0) for volume in volumes_data)
            
            # Process data to get usage information
            server_count = len(servers_data)
            active_servers = sum(1 for server in servers_data if server.get('status') == 'ACTIVE')
            
            # Format compute quotas
            vcpus_used = limits.get('totalCoresUsed', 0)
            vcpus_limit = limits.get('maxTotalCores', 'unlimited')
            ram_used_mb = limits.get('totalRAMUsed', 0)
            ram_limit_mb = limits.get('maxTotalRAMSize', 'unlimited')
            
            # Convert RAM to more readable format
            ram_used_gb = ram_used_mb / 1024 if isinstance(ram_used_mb, (int, float)) else 0
            ram_limit_gb = ram_limit_mb / 1024 if isinstance(ram_limit_mb, (int, float)) else 'unlimited'
            
            # Prepare formatted result
            result = {
                "summary": {
                    "total_servers": server_count,
                    "active_servers": active_servers,
                    "total_vcpus_used": vcpus_used,
                    "total_ram_used_gb": round(ram_used_gb, 2),
                    "total_volumes": len(volumes_data),
                    "total_storage_gb": total_storage_gb
                },
                "compute_quotas": {
                    "vcpus": {
                        "used": vcpus_used,
                        "limit": vcpus_limit
                    },
                    "ram_gb": {
                        "used": round(ram_used_gb, 2),
                        "limit": round(ram_limit_gb, 2) if isinstance(ram_limit_gb, (int, float)) else ram_limit_gb
                    },
                    "instances": {
                        "used": limits.get('totalInstancesUsed', 0),
                        "limit": limits.get('maxTotalInstances', 'unlimited')
                    }
                },
                "servers": [
                    {
                        "name": server.get('name', 'unknown'),
                        "id": server.get('id', 'unknown'),
                        "status": server.get('status', 'unknown'),
                        "flavor": server.get('flavor', {}).get('original_name', 'unknown'),
                        "created": server.get('created', 'unknown')
                    } for server in servers_data[:5]  # Limit to first 5 servers
                ],
                "volumes": [
                    {
                        "name": volume.get('name', 'unknown'),
                        "id": volume.get('id', 'unknown'),
                        "size_gb": volume.get('size', 0),
                        "status": volume.get('status', 'unknown'),
                        "attached_to": [attachment.get('server_id') for attachment in volume.get('attachments', [])]
                    } for volume in volumes_data[:5]  # Limit to first 5 volumes
                ]
            }
            
            self.log_operation("QUERY_USAGE", "project", {}, "SUCCESS")
            return result
            
        except Exception as e:
            self.log_operation("QUERY_USAGE", "project", {}, "FAILED", str(e))
            raise Exception(f"Failed to get usage: {str(e)}")

    def log_operation(self, operation_type: str, resource_name: str, request_data: Dict[str, Any],
                      status: str, error_message: Optional[str] = None):
        db = SessionLocal()
        try:
            log = OperationLog(
                operation_type=operation_type,
                resource_name=resource_name,
                request_data=request_data,
                status=status,
                completed_at=datetime.utcnow(),
                error_message=error_message
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
