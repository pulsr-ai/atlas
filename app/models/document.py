from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=True)
    directory_id = Column(UUID(as_uuid=True), ForeignKey("directories.id"), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    summary = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    subtenant_id = Column(UUID(as_uuid=True), nullable=True)
    is_private = Column(Boolean, default=False)
    mongodb_id = Column(String(24), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    directory = relationship("Directory", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")