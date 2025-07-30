from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.ingestion_service import IngestionService
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
ingestion_service = IngestionService()

class DocumentResponse(BaseModel):
    id: str
    name: str
    original_filename: str
    directory_path: str
    version: int
    summary: Optional[str]
    is_private: bool
    
    class Config:
        from_attributes = True

@router.post("/ingest", response_model=DocumentResponse)
async def ingest_document(
    file: UploadFile = File(...),
    directory_path: str = "/",
    subtenant_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    
    try:
        document = await ingestion_service.ingest_document(
            db, file, directory_path, subtenant_id
        )
        
        return DocumentResponse(
            id=str(document.id),
            name=document.name,
            original_filename=document.original_filename,
            directory_path=document.directory.path,
            version=document.version,
            summary=document.summary,
            is_private=document.is_private
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest/version/{document_id}", response_model=DocumentResponse)
async def ingest_document_version(
    document_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    
    try:
        document = await ingestion_service.ingest_document_version(
            db, document_id, file
        )
        
        return DocumentResponse(
            id=str(document.id),
            name=document.name,
            original_filename=document.original_filename,
            directory_path=document.directory.path,
            version=document.version,
            summary=document.summary,
            is_private=document.is_private
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))