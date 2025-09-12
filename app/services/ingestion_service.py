import os
import uuid
from typing import Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session
from markitdown import MarkItDown
from app.models import Directory, Document, Chunk
from app.database import get_mongodb
from app.services.chunking_service import ChunkingService
from app.services.summary_service import SummaryService

class IngestionService:
    def __init__(self):
        self.md = MarkItDown()
        self.mongodb = get_mongodb()
        self.chunking_service = ChunkingService()
        self.summary_service = SummaryService()
    
    async def ingest_document(
        self,
        db: Session,
        file: UploadFile,
        directory_path: str = "/",
        subtenant_id: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> Document:
        
        # Ensure directory exists
        directory = await self._ensure_directory_exists(db, directory_path, subtenant_id)
        
        # Read file content
        content = await file.read()
        
        # Convert to markdown using MarkItDown - create a BytesIO stream from content
        import io
        content_stream = io.BytesIO(content)
        markdown_content = self.md.convert_stream(content_stream, file_extension=self._get_file_extension(file.filename))
        
        # Create document record
        document = Document(
            name=self._get_document_name(file.filename),
            original_filename=file.filename,
            mime_type=file.content_type,
            directory_id=directory.id,
            version=1,
            subtenant_id=uuid.UUID(subtenant_id) if subtenant_id else None,
            is_private=bool(subtenant_id),
            mongodb_id=str(uuid.uuid4())  # Will be replaced with actual MongoDB ID
        )
        
        # Store document content in MongoDB
        mongodb_doc = {
            "_id": document.mongodb_id,
            "content": markdown_content.text_content,
            "metadata": {
                "title": markdown_content.title or file.filename,
                "original_filename": file.filename,
                "mime_type": file.content_type
            }
        }
        
        result = self.mongodb.documents.insert_one(mongodb_doc)
        document.mongodb_id = str(result.inserted_id)
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Chunk the document
        await self._chunk_document(db, document, markdown_content.text_content)
        
        # Generate summaries
        await self._generate_summaries(db, document, auth_token)
        
        # Update directory summary if needed
        await self._update_directory_summary(db, directory, auth_token)
        
        return document
    
    async def ingest_document_version(
        self,
        db: Session,
        document_id: str,
        file: UploadFile,
        auth_token: Optional[str] = None
    ) -> Document:
        
        # Get existing document
        existing_doc = db.query(Document).filter(Document.id == document_id).first()
        if not existing_doc:
            raise ValueError(f"Document with id {document_id} not found")
        
        # Get next version number
        max_version = db.query(Document).filter(
            Document.name == existing_doc.name,
            Document.directory_id == existing_doc.directory_id
        ).order_by(Document.version.desc()).first().version
        
        # Read file content
        content = await file.read()
        
        # Convert to markdown using MarkItDown - create a BytesIO stream from content
        import io
        content_stream = io.BytesIO(content)
        markdown_content = self.md.convert_stream(content_stream, file_extension=self._get_file_extension(file.filename))
        
        # Create new document version
        new_version = Document(
            name=existing_doc.name,
            original_filename=file.filename,
            mime_type=file.content_type,
            directory_id=existing_doc.directory_id,
            version=max_version + 1,
            subtenant_id=existing_doc.subtenant_id,
            is_private=existing_doc.is_private,
            mongodb_id=str(uuid.uuid4())
        )
        
        # Store document content in MongoDB
        mongodb_doc = {
            "_id": new_version.mongodb_id,
            "content": markdown_content.text_content,
            "metadata": {
                "title": markdown_content.title or file.filename,
                "original_filename": file.filename,
                "mime_type": file.content_type,
                "version": new_version.version
            }
        }
        
        result = self.mongodb.documents.insert_one(mongodb_doc)
        new_version.mongodb_id = str(result.inserted_id)
        
        db.add(new_version)
        db.commit()
        db.refresh(new_version)
        
        # Chunk the document
        await self._chunk_document(db, new_version, markdown_content.text_content)
        
        # Generate summaries
        await self._generate_summaries(db, new_version, auth_token)
        
        return new_version
    
    async def _ensure_directory_exists(
        self,
        db: Session,
        directory_path: str,
        subtenant_id: Optional[str] = None
    ) -> Directory:
        
        # Check if directory already exists
        existing_dir = db.query(Directory).filter(Directory.path == directory_path).first()
        if existing_dir:
            return existing_dir
        
        # Create directory hierarchy if needed
        path_parts = [part for part in directory_path.split('/') if part]
        current_path = ""
        parent_id = None
        
        for part in path_parts:
            current_path += f"/{part}"
            
            # Check if this level exists
            dir_at_level = db.query(Directory).filter(Directory.path == current_path).first()
            if not dir_at_level:
                # Create directory
                dir_at_level = Directory(
                    name=part,
                    path=current_path,
                    parent_id=parent_id,
                    subtenant_id=uuid.UUID(subtenant_id) if subtenant_id else None,
                    is_private=bool(subtenant_id)
                )
                db.add(dir_at_level)
                db.commit()
                db.refresh(dir_at_level)
            
            parent_id = dir_at_level.id
        
        # Return the final directory
        return db.query(Directory).filter(Directory.path == directory_path).first()
    
    async def _chunk_document(self, db: Session, document: Document, content: str):
        chunks = await self.chunking_service.chunk_document(content, document.original_filename)
        
        for i, chunk_content in enumerate(chunks):
            # Store chunk content in MongoDB
            chunk_mongodb_id = str(uuid.uuid4())
            mongodb_chunk = {
                "_id": chunk_mongodb_id,
                "content": chunk_content,
                "document_id": str(document.id),
                "chunk_index": i
            }
            
            result = self.mongodb.chunks.insert_one(mongodb_chunk)
            chunk_mongodb_id = str(result.inserted_id)
            
            # Create chunk record
            chunk = Chunk(
                document_id=document.id,
                chunk_index=i,
                title=self._extract_chunk_title(chunk_content),
                mongodb_id=chunk_mongodb_id
            )
            
            db.add(chunk)
        
        db.commit()
    
    async def _generate_summaries(self, db: Session, document: Document, auth_token: Optional[str] = None):
        # Generate summaries for chunks and document
        for chunk in document.chunks:
            chunk_content = self.mongodb.chunks.find_one({"_id": chunk.mongodb_id})["content"]
            chunk.summary = await self.summary_service.generate_chunk_summary(chunk_content, auth_token)
        
        # Generate document summary
        document.summary = await self.summary_service.generate_document_summary(document, auth_token)
        
        db.commit()
    
    async def _update_directory_summary(self, db: Session, directory: Directory, auth_token: Optional[str] = None):
        # Check if directory summary needs updating
        should_update = await self.summary_service.should_update_directory_summary(directory, auth_token)
        if should_update:
            directory.summary = await self.summary_service.generate_directory_summary(directory, auth_token)
            db.commit()
    
    def _get_file_extension(self, filename: str) -> str:
        return os.path.splitext(filename)[1].lower()
    
    def _get_document_name(self, filename: str) -> str:
        return os.path.splitext(filename)[0]
    
    def _extract_chunk_title(self, content: str) -> Optional[str]:
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                return line.lstrip('#').strip()
        return None