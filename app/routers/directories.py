from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.database import get_db
from app.models import Directory, Document, Subtenant, PermissionType, ResourceType
from app.auth import get_current_active_subtenant, check_resource_access, can_access_resource
from pydantic import BaseModel
from typing import List, Optional
import uuid

router = APIRouter()

class DirectoryItem(BaseModel):
    id: str
    name: str
    path: str
    is_directory: bool
    summary: Optional[str]
    is_private: bool
    created_at: str
    
    class Config:
        from_attributes = True

class DocumentItem(BaseModel):
    id: str
    name: str
    original_filename: str
    version: int
    summary: Optional[str]
    is_private: bool
    created_at: str
    
    class Config:
        from_attributes = True

class DirectoryContents(BaseModel):
    directory: DirectoryItem
    subdirectories: List[DirectoryItem]
    documents: List[DocumentItem]

@router.get("/directories", response_model=List[DirectoryItem])
async def list_directories(
    subtenant_id: Optional[str] = Query(None),
    include_private: bool = Query(False),
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    
    query = db.query(Directory)
    
    # Filter by subtenant if specified
    if subtenant_id:
        try:
            subtenant_uuid = uuid.UUID(subtenant_id)
            query = query.filter(Directory.subtenant_id == subtenant_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid subtenant_id format")
    
    # Filter private directories unless explicitly requested
    if not include_private:
        query = query.filter(Directory.is_private == False)
    
    directories = query.all()
    
    # Filter directories based on ownership and permissions
    accessible_directories = []
    for dir in directories:
        # Check if directory belongs to current subtenant or is shared with them
        if dir.subtenant_id == current_subtenant.id or can_access_resource(db, current_subtenant, ResourceType.DIRECTORY, str(dir.id)):
            accessible_directories.append(dir)
    
    return [
        DirectoryItem(
            id=str(dir.id),
            name=dir.name,
            path=dir.path,
            is_directory=True,
            summary=dir.summary,
            is_private=dir.is_private,
            created_at=dir.created_at.isoformat() if dir.created_at else ""
        )
        for dir in accessible_directories
    ]

@router.get("/directories/traverse", response_model=DirectoryContents)
async def traverse_directory(
    path: str = Query("/"),
    subtenant_id: Optional[str] = Query(None),
    include_private: bool = Query(False),
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    
    # Get the directory by path
    query = db.query(Directory).filter(Directory.path == path)
    
    if subtenant_id:
        try:
            subtenant_uuid = uuid.UUID(subtenant_id)
            query = query.filter(Directory.subtenant_id == subtenant_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid subtenant_id format")
    
    directory = query.first()
    
    if not directory:
        # If root directory doesn't exist, create it
        if path == "/":
            directory = Directory(
                name="root",
                path="/",
                parent_id=None,
                subtenant_id=current_subtenant.id,
                is_private=True
            )
            db.add(directory)
            db.commit()
            db.refresh(directory)
        else:
            raise HTTPException(status_code=404, detail="Directory not found")
    
    # Check if directory belongs to current subtenant or is shared with them
    if directory.subtenant_id != current_subtenant.id and not can_access_resource(db, current_subtenant, ResourceType.DIRECTORY, str(directory.id)):
        raise HTTPException(status_code=403, detail="Access denied to directory")
    
    # Get subdirectories
    subdirs_query = db.query(Directory).filter(Directory.parent_id == directory.id)
    if not include_private:
        subdirs_query = subdirs_query.filter(Directory.is_private == False)
    
    subdirectories = subdirs_query.all()
    
    # Get documents in this directory
    docs_query = db.query(Document).filter(Document.directory_id == directory.id)
    if not include_private:
        docs_query = docs_query.filter(Document.is_private == False)
    
    documents = docs_query.all()
    
    return DirectoryContents(
        directory=DirectoryItem(
            id=str(directory.id),
            name=directory.name,
            path=directory.path,
            is_directory=True,
            summary=directory.summary,
            is_private=directory.is_private,
            created_at=directory.created_at.isoformat() if directory.created_at else ""
        ),
        subdirectories=[
            DirectoryItem(
                id=str(subdir.id),
                name=subdir.name,
                path=subdir.path,
                is_directory=True,
                summary=subdir.summary,
                is_private=subdir.is_private,
                created_at=subdir.created_at.isoformat() if subdir.created_at else ""
            )
            for subdir in subdirectories
        ],
        documents=[
            DocumentItem(
                id=str(doc.id),
                name=doc.name,
                original_filename=doc.original_filename,
                version=doc.version,
                summary=doc.summary,
                is_private=doc.is_private,
                created_at=doc.created_at.isoformat() if doc.created_at else ""
            )
            for doc in documents
        ]
    )

@router.get("/directories/{directory_id}", response_model=DirectoryContents)
async def get_directory(
    directory_id: str,
    include_private: bool = Query(False),
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    
    try:
        dir_uuid = uuid.UUID(directory_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid directory ID format")
    
    directory = db.query(Directory).filter(Directory.id == dir_uuid).first()
    
    if not directory:
        raise HTTPException(status_code=404, detail="Directory not found")
    
    # Check if directory belongs to current subtenant or is shared with them
    if directory.subtenant_id != current_subtenant.id and not can_access_resource(db, current_subtenant, ResourceType.DIRECTORY, str(directory.id)):
        raise HTTPException(status_code=403, detail="Access denied to directory")
    
    # Get subdirectories
    subdirs_query = db.query(Directory).filter(Directory.parent_id == directory.id)
    if not include_private:
        subdirs_query = subdirs_query.filter(Directory.is_private == False)
    
    subdirectories = subdirs_query.all()
    
    # Get documents in this directory
    docs_query = db.query(Document).filter(Document.directory_id == directory.id)
    if not include_private:
        docs_query = docs_query.filter(Document.is_private == False)
    
    documents = docs_query.all()
    
    return DirectoryContents(
        directory=DirectoryItem(
            id=str(directory.id),
            name=directory.name,
            path=directory.path,
            is_directory=True,
            summary=directory.summary,
            is_private=directory.is_private,
            created_at=directory.created_at.isoformat() if directory.created_at else ""
        ),
        subdirectories=[
            DirectoryItem(
                id=str(subdir.id),
                name=subdir.name,
                path=subdir.path,
                is_directory=True,
                summary=subdir.summary,
                is_private=subdir.is_private,
                created_at=subdir.created_at.isoformat() if subdir.created_at else ""
            )
            for subdir in subdirectories
        ],
        documents=[
            DocumentItem(
                id=str(doc.id),
                name=doc.name,
                original_filename=doc.original_filename,
                version=doc.version,
                summary=doc.summary,
                is_private=doc.is_private,
                created_at=doc.created_at.isoformat() if doc.created_at else ""
            )
            for doc in documents
        ]
    )