from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base


class PermissionType(enum.Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"


class ResourceType(enum.Enum):
    DIRECTORY = "directory"
    DOCUMENT = "document"


class GrantedToType(enum.Enum):
    SUBTENANT = "subtenant"
    GROUP = "group"


class Permission(Base):
    """Permissions for sharing resources with subtenants or groups"""
    __tablename__ = "permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Which subtenant is granting the permission
    granted_by = Column(UUID(as_uuid=True), ForeignKey("subtenants.id"), nullable=False)
    
    # What type of entity is being granted access (subtenant or group)
    granted_to_type = Column(Enum(GrantedToType), nullable=False)
    
    # ID of the subtenant or group being granted access
    granted_to_id = Column(UUID(as_uuid=True), nullable=False)
    
    # What resource is being shared
    resource_type = Column(Enum(ResourceType), nullable=False)
    resource_id = Column(UUID(as_uuid=True), nullable=False)  # ID of directory or document
    
    # What level of access
    permission_type = Column(Enum(PermissionType), nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    granting_subtenant = relationship("Subtenant", back_populates="granted_permissions")