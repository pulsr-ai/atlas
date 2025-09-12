from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class Directory(Base):
    __tablename__ = "directories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    path = Column(String(1000), nullable=False, unique=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("directories.id"), nullable=True)
    summary = Column(Text, nullable=True)
    subtenant_id = Column(UUID(as_uuid=True), ForeignKey("subtenants.id"), nullable=True)
    is_private = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    parent = relationship("Directory", remote_side=[id], back_populates="children")
    children = relationship("Directory", back_populates="parent")
    documents = relationship("Document", back_populates="directory")
    subtenant = relationship("Subtenant", back_populates="directories")