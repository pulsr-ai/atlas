from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter()

@router.get("/documents")
async def list_documents(db: Session = Depends(get_db)):
    return {"message": "Document listing - to be implemented"}

@router.get("/documents/{document_id}")
async def get_document(document_id: str, db: Session = Depends(get_db)):
    return {"message": f"Get document {document_id} - to be implemented"}