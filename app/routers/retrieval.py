from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Subtenant
from app.auth import get_current_active_subtenant
from app.services.agentic_retrieval_service import AgenticRetrievalService
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter()
retrieval_service = AgenticRetrievalService()
security = HTTPBearer()

class RetrievalQuery(BaseModel):
    query: str

class ChunkResult(BaseModel):
    chunk_id: str
    chunk_index: int
    title: Optional[str]
    summary: Optional[str]
    content: str
    document_name: str
    directory_path: str
    reasoning: str
    relevance_explanation: str
    rank: int

class ReasoningPath(BaseModel):
    directories_considered: List[Dict[str, Any]]
    documents_considered: List[Dict[str, Any]]
    chunks_identified: int

class RetrievalResponse(BaseModel):
    query: str
    reasoning_path: ReasoningPath
    results: List[ChunkResult]

@router.post("/retrieve", response_model=RetrievalResponse)
async def agentic_retrieval(
    query: RetrievalQuery,
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    
    try:
        result = await retrieval_service.retrieve(
            db, query.query, str(current_subtenant.id), credentials.credentials
        )
        
        return RetrievalResponse(
            query=result["query"],
            reasoning_path=ReasoningPath(
                directories_considered=result["reasoning_path"]["directories_considered"],
                documents_considered=result["reasoning_path"]["documents_considered"],
                chunks_identified=result["reasoning_path"]["chunks_identified"]
            ),
            results=[
                ChunkResult(
                    chunk_id=chunk["chunk_id"],
                    chunk_index=chunk["chunk_index"],
                    title=chunk["title"],
                    summary=chunk["summary"],
                    content=chunk["content"],
                    document_name=chunk["document_name"],
                    directory_path=chunk["directory_path"],
                    reasoning=chunk["reasoning"],
                    relevance_explanation=chunk["relevance_explanation"],
                    rank=chunk["rank"]
                )
                for chunk in result["results"]
            ]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/retrieve/explain/{query}")
async def explain_retrieval_reasoning(
    query: str,
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    
    try:
        result = await retrieval_service.retrieve(
            db, query, str(current_subtenant.id)
        )
        
        # Return just the reasoning path for explanation
        return {
            "query": query,
            "reasoning_explanation": {
                "directories_analyzed": len(result["reasoning_path"]["directories_considered"]),
                "directories_selected": [
                    {
                        "path": dir_info["path"],
                        "reason": dir_info.get("reasoning", "Selected based on relevance analysis")
                    }
                    for dir_info in result["reasoning_path"]["directories_considered"]
                ],
                "documents_analyzed": len(result["reasoning_path"]["documents_considered"]),
                "documents_selected": [
                    {
                        "name": doc_info["name"],
                        "directory": doc_info["directory_path"],
                        "reason": doc_info.get("reasoning", "Selected based on relevance analysis")
                    }
                    for doc_info in result["reasoning_path"]["documents_considered"]
                ],
                "chunks_identified": result["reasoning_path"]["chunks_identified"],
                "final_results_count": len(result["results"])
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))