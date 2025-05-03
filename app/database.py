from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Get database URL from environment or use default
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cloud_operations.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    """User model for authentication and session management"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="user")
    resources = relationship("Resource", back_populates="owner")
    
class Session(Base):
    """Session model for tracking user sessions"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_token = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
class Resource(Base):
    """Resource model for tracking cloud resources"""
    __tablename__ = "resources"
    
    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(String, index=True)  # The OpenStack ID
    name = Column(String, index=True)
    resource_type = Column(String, index=True)  # VM, Network, Volume
    status = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    properties = Column(JSON)  # Store resource-specific properties
    
    # Relationships
    owner = relationship("User", back_populates="resources")
    operations = relationship("OperationLog", back_populates="resource")

class OperationLog(Base):
    """Log of all operations performed on resources"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    operation_type = Column(String, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=True)
    resource_name = Column(String)
    request_data = Column(JSON)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    resource = relationship("Resource", back_populates="operations")

class UsageSnapshot(Base):
    """Periodic snapshots of resource usage"""
    __tablename__ = "usage_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    vcpu_used = Column(Integer)
    ram_used = Column(Integer)  # In MB
    volumes_used = Column(Integer)
    storage_used = Column(Float)  # In GB
    max_vcpu = Column(Integer)
    max_ram = Column(Integer)  # In MB
    max_volumes = Column(Integer)
    max_storage = Column(Float)  # In GB

# Create all tables
def init_db():
    Base.metadata.create_all(bind=engine)

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize DB if this file is run directly
if __name__ == "__main__":
    init_db()
    print("Database tables created successfully!")