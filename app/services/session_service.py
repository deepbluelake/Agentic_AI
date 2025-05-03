import uuid
from typing import Dict, Any
from datetime import datetime, timedelta

# Simple in-memory store for pending operations
# In production, consider using Redis or a database
pending_operations = {}

class SessionService:
    @staticmethod
    def store_pending_operation(intent: str, entities: Dict[str, Any]) -> str:
        """Store a pending operation and return its ID"""
        operation_id = str(uuid.uuid4())
        
        pending_operations[operation_id] = {
            "intent": intent,
            "entities": entities,
            "timestamp": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=15)
        }
        
        return operation_id
    
    @staticmethod
    def get_pending_operation(operation_id: str) -> Dict[str, Any]:
        """Retrieve a pending operation by ID"""
        operation = pending_operations.get(operation_id)
        
        if not operation:
            raise Exception("Operation not found or has expired")
        
        # Check if operation has expired
        if operation["expires_at"] < datetime.utcnow():
            del pending_operations[operation_id]
            raise Exception("Operation has expired")
        
        return operation
    
    @staticmethod
    def remove_pending_operation(operation_id: str):
        """Remove a pending operation after it's executed or declined"""
        if operation_id in pending_operations:
            del pending_operations[operation_id]