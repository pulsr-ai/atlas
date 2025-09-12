from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Subtenant(Base):
    __tablename__ = "subtenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    census_user_id = Column(UUID(as_uuid=True), unique=True, nullable=False)  # Maps to Census user ID
    name = Column(String(255), nullable=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    directories = relationship("Directory", back_populates="subtenant")
    documents = relationship("Document", back_populates="subtenant")
    granted_permissions = relationship("Permission", back_populates="granting_subtenant")