from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Subtenant
from app.auth import get_current_active_subtenant
from app.services.ingestion_service import IngestionService
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
ingestion_service = IngestionService()
security = HTTPBearer()

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
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    
    try:
        document = await ingestion_service.ingest_document(
            db, file, directory_path, str(current_subtenant.id), credentials.credentials
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
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    
    try:
        document = await ingestion_service.ingest_document_version(
            db, document_id, file, credentials.credentials
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