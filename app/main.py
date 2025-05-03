import os
import pathlib
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
import openstack
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Agentic AI for Cloud Operations")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)  # optional: create to avoid startup errors
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class VMRequest(BaseModel):
    name: str
    flavor: str
    image: str
    network: Optional[str] = None

class VolumeRequest(BaseModel):
    name: str
    size: int

class NetworkRequest(BaseModel):
    name: str
    cidr: str

class NLRequest(BaseModel):
    text: str

class ConfirmationRequest(BaseModel):
    request_id: str
    confirmed: bool

# OpenStack connection
def get_openstack_connection():
    conn = openstack.connect(
        auth_url="https://api-ap-south-mum-1.openstack.acecloudhosting.com:5000/v3",
        username="Hackathon_AIML_1",
        password="Hackathon_AIML_1@567",
        project_name="Agentic_AI",
        user_domain_name="Default",
        project_domain_id="default",
        identity_api_version="3",
        region_name="mum1"
    )
    return conn

# Import services
from app.services.openstack_service import OpenStackService
from app.services.nlp_service import NLPService
from app.services.session_service import SessionService
from app.database import get_db, OperationLog

# Initialize services
nlp_service = NLPService()

# Dependencies
def get_openstack_service(conn: openstack.connection = Depends(get_openstack_connection)):
    return OpenStackService(conn)

# Routes
@app.get("/")
async def root():
    return {"message": "Agentic AI for Cloud Operations API"}

@app.get("/ui", response_class=HTMLResponse)
async def get_ui():
    html_file = pathlib.Path(static_dir, "index.html").read_text()
    return HTMLResponse(content=html_file)

@app.post("/nl/process")
async def process_nl_request(
    request: NLRequest,
    db: Session = Depends(get_db),
    openstack_service: OpenStackService = Depends(get_openstack_service)
):
    try:
        intent, entities = nlp_service.parse_request(request.text)
        log = OperationLog(
            operation_type=intent,
            resource_name=entities.get("name", "unknown"),
            request_data=entities,
            status="pending"
        )
        db.add(log)
        db.commit()

        if intent == "QUERY_USAGE":
            result = openstack_service.get_usage()
            response = nlp_service.generate_response(intent, result)
            log.status = "completed"
            log.completed_at = datetime.utcnow()
            db.commit()
            return {
                "requires_confirmation": False,
                "response": response,
                "result": result,
                "log_id": log.id
            }

        confirmation_message = nlp_service.generate_confirmation_message(intent, entities)
        operation_id = SessionService.store_pending_operation(intent, entities)
        return {
            "requires_confirmation": True,
            "request_id": operation_id,
            "response": confirmation_message,
            "log_id": log.id
        }

    except Exception as e:
        if 'log' in locals():
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/nl/confirm")
async def confirm_operation(
    confirmation: ConfirmationRequest,
    db: Session = Depends(get_db),
    openstack_service: OpenStackService = Depends(get_openstack_service)
):
    try:
        operation = SessionService.get_pending_operation(confirmation.request_id)
        intent = operation["intent"]
        entities = operation["entities"]

        if not confirmation.confirmed:
            SessionService.remove_pending_operation(confirmation.request_id)
            return {"status": "cancelled", "message": "Operation cancelled by user"}

        if intent == "CREATE_VM":
            result = openstack_service.create_vm(**entities)
        elif intent == "DELETE_VM":
            result = openstack_service.delete_vm(name=entities["name"])
        elif intent == "RESIZE_VM":
            result = openstack_service.resize_vm(**entities)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported intent: {intent}")

        response = nlp_service.generate_response(intent, result)

        log = db.query(OperationLog).filter(
            OperationLog.operation_type == intent,
            OperationLog.resource_name == entities.get("name", "unknown"),
            OperationLog.status == "pending"
        ).order_by(OperationLog.created_at.desc()).first()
        if log:
            log.status = "completed"
            log.completed_at = datetime.utcnow()
            db.commit()

        SessionService.remove_pending_operation(confirmation.request_id)

        return {
            "status": "completed",
            "response": response,
            "result": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vm/create")
async def create_vm(
    request: VMRequest,
    openstack_service: OpenStackService = Depends(get_openstack_service)
):
    try:
        return openstack_service.create_vm(**request.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vm/resize")
async def resize_vm(
    vm_name: str,
    new_flavor: str,
    openstack_service: OpenStackService = Depends(get_openstack_service)
):
    try:
        return openstack_service.resize_vm(vm_name=vm_name, new_flavor=new_flavor)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/vm/{vm_name}")
async def delete_vm(
    vm_name: str,
    openstack_service: OpenStackService = Depends(get_openstack_service)
):
    try:
        return openstack_service.delete_vm(vm_name=vm_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage")
async def get_usage(
    openstack_service: OpenStackService = Depends(get_openstack_service)
):
    try:
        return openstack_service.get_usage()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

