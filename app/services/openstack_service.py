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
            limits = self.conn.compute.get_limits().absolute
            servers = list(self.conn.compute.servers())
            volumes = list(self.conn.block_storage.volumes())

            vcpu_used = sum(getattr(server.flavor, 'vcpus', 0) for server in servers)
            ram_used = sum(getattr(server.flavor, 'ram', 0) for server in servers)
            volume_count = len(volumes)
            total_storage = sum(getattr(volume, 'size', 0) for volume in volumes)

            result = {
                "vCPU_used": vcpu_used,
                "RAM_used": ram_used,
                "volumes_used": volume_count,
                "total_storage": total_storage,
                "limits": {
                    "max_vCPU": getattr(limits, 'max_total_cores', 'unknown'),
                    "max_RAM": getattr(limits, 'max_total_ram_size', 'unknown'),
                    "max_volumes": getattr(limits, 'max_total_volumes', 'unknown'),
                    "max_storage": getattr(limits, 'max_total_volume_gigabytes', 'unknown')
                }
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
