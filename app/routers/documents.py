from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Document, Subtenant, PermissionType, ResourceType
from app.auth import get_current_active_subtenant, can_access_resource
from typing import List, Optional
from pydantic import BaseModel
import uuid

router = APIRouter()

class DocumentResponse(BaseModel):
    id: str
    name: str
    original_filename: str
    mime_type: Optional[str]
    directory_id: str
    version: int
    summary: Optional[str]
    tags: Optional[str]
    is_private: bool
    created_at: str
    
    class Config:
        from_attributes = True

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    subtenant_id: Optional[str] = Query(None),
    directory_id: Optional[str] = Query(None),
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    """List documents accessible to current user"""
    query = db.query(Document)
    
    # Filter by subtenant if specified
    if subtenant_id:
        try:
            subtenant_uuid = uuid.UUID(subtenant_id)
            query = query.filter(Document.subtenant_id == subtenant_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid subtenant_id format")
    
    # Filter by directory if specified
    if directory_id:
        try:
            dir_uuid = uuid.UUID(directory_id)
            query = query.filter(Document.directory_id == dir_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid directory_id format")
    
    documents = query.all()
    
    # Filter documents based on ownership and permissions
    accessible_documents = []
    for doc in documents:
        # Check if document belongs to current subtenant or is shared with them
        if doc.subtenant_id == current_subtenant.id or can_access_resource(db, current_subtenant, ResourceType.DOCUMENT, str(doc.id)):
            accessible_documents.append(doc)
    
    return [
        DocumentResponse(
            id=str(doc.id),
            name=doc.name,
            original_filename=doc.original_filename,
            mime_type=doc.mime_type,
            directory_id=str(doc.directory_id),
            version=doc.version,
            summary=doc.summary,
            tags=doc.tags,
            is_private=doc.is_private,
            created_at=doc.created_at.isoformat() if doc.created_at else ""
        )
        for doc in accessible_documents
    ]

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str, 
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    """Get document details"""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    
    document = db.query(Document).filter(Document.id == doc_uuid).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if document belongs to current subtenant or is shared with them
    if document.subtenant_id != current_subtenant.id and not can_access_resource(db, current_subtenant, ResourceType.DOCUMENT, str(document.id)):
        raise HTTPException(status_code=403, detail="Access denied to document")
    
    return DocumentResponse(
        id=str(document.id),
        name=document.name,
        original_filename=document.original_filename,
        mime_type=document.mime_type,
        directory_id=str(document.directory_id),
        version=document.version,
        summary=document.summary,
        tags=document.tags,
        is_private=document.is_private,
        created_at=document.created_at.isoformat() if document.created_at else ""
    )