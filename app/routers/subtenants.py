from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel

from app.database import get_db
from app.models import Subtenant, Permission, PermissionType, ResourceType
from app.auth import get_current_active_subtenant

router = APIRouter()


class SubtenantCreate(BaseModel):
    name: str
    description: str = None


@router.post("/subtenants", response_model=dict)
def create_subtenant(
    subtenant_data: SubtenantCreate,
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    """Create a new subtenant"""
    subtenant = Subtenant(
        census_user_id=current_subtenant.census_user_id,
        name=subtenant_data.name,
        description=subtenant_data.description,
        is_active=True
    )
    db.add(subtenant)
    db.commit()
    db.refresh(subtenant)
    
    return {
        "id": subtenant.id,
        "name": subtenant.name,
        "description": subtenant.description,
        "is_active": subtenant.is_active,
        "created_at": subtenant.created_at,
        "census_user_id": subtenant.census_user_id
    }


@router.get("/subtenants", response_model=List[dict])
def list_subtenants(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    """List subtenants accessible to current user"""
    # Return the current subtenant (1:1 mapping with Census user)
    return [
        {
            "id": current_subtenant.id,
            "name": current_subtenant.name,
            "description": current_subtenant.description,
            "is_active": current_subtenant.is_active,
            "created_at": current_subtenant.created_at,
            "census_user_id": current_subtenant.census_user_id
        }
    ]


@router.get("/subtenants/{subtenant_id}", response_model=dict)
def get_subtenant(
    subtenant_id: UUID,
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    """Get subtenant details"""
    # Only allow access to own subtenant
    if current_subtenant.id != subtenant_id:
        raise HTTPException(status_code=403, detail="Access denied - can only view own subtenant")
    
    return {
        "id": current_subtenant.id,
        "name": current_subtenant.name,
        "description": current_subtenant.description,
        "is_active": current_subtenant.is_active,
        "created_at": current_subtenant.created_at,
        "census_user_id": current_subtenant.census_user_id
    }


@router.put("/subtenants/{subtenant_id}", response_model=dict)
def update_subtenant(
    subtenant_id: UUID,
    name: str = None,
    description: str = None,
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    """Update subtenant"""
    # Only allow updating own subtenant
    if current_subtenant.id != subtenant_id:
        raise HTTPException(status_code=403, detail="Access denied - can only update own subtenant")
    
    if name is not None:
        current_subtenant.name = name
    if description is not None:
        current_subtenant.description = description
    
    db.commit()
    db.refresh(current_subtenant)
    
    return {
        "id": current_subtenant.id,
        "name": current_subtenant.name,
        "description": current_subtenant.description,
        "is_active": current_subtenant.is_active,
        "created_at": current_subtenant.created_at,
        "census_user_id": current_subtenant.census_user_id
    }


@router.delete("/subtenants/{subtenant_id}")
def delete_subtenant(
    subtenant_id: UUID,
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    """Delete subtenant"""
    # Only allow deleting own subtenant
    if current_subtenant.id != subtenant_id:
        raise HTTPException(status_code=403, detail="Access denied - can only delete own subtenant")
    
    # Mark as inactive instead of hard delete
    current_subtenant.is_active = False
    db.commit()
    
    return {"message": "Subtenant deactivated successfully"}