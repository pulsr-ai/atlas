from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel

from app.database import get_db
from app.models import Permission, PermissionType, ResourceType, GrantedToType, Subtenant
from app.auth import get_current_active_subtenant

router = APIRouter()


class PermissionCreate(BaseModel):
    granted_to_type: GrantedToType
    granted_to_id: UUID
    resource_type: ResourceType
    resource_id: UUID
    permission_type: PermissionType
    expires_at: str = None  # ISO format datetime string, optional


@router.post("/permissions", response_model=dict)
def grant_permission(
    permission_data: PermissionCreate,
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    """Grant permission to a subtenant or group"""
    
    # Check if resource belongs to current subtenant (only owners can grant permissions)
    if permission_data.resource_type == ResourceType.DIRECTORY:
        from app.models import Directory
        resource = db.query(Directory).filter(
            Directory.id == permission_data.resource_id,
            Directory.subtenant_id == current_subtenant.id
        ).first()
    elif permission_data.resource_type == ResourceType.DOCUMENT:
        from app.models import Document
        resource = db.query(Document).filter(
            Document.id == permission_data.resource_id,
            Document.subtenant_id == current_subtenant.id
        ).first()
    
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found or not owned by current subtenant")
    
    # Check if permission already exists
    existing = db.query(Permission).filter(
        Permission.granted_by == current_subtenant.id,
        Permission.granted_to_type == permission_data.granted_to_type,
        Permission.granted_to_id == permission_data.granted_to_id,
        Permission.resource_type == permission_data.resource_type,
        Permission.resource_id == permission_data.resource_id,
        Permission.permission_type == permission_data.permission_type
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Permission already exists")
    
    # Parse expires_at if provided
    expires_at = None
    if permission_data.expires_at:
        from datetime import datetime
        try:
            expires_at = datetime.fromisoformat(permission_data.expires_at.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expires_at format. Use ISO format.")
    
    # Create permission
    permission = Permission(
        granted_by=current_subtenant.id,
        granted_to_type=permission_data.granted_to_type,
        granted_to_id=permission_data.granted_to_id,
        resource_type=permission_data.resource_type,
        resource_id=permission_data.resource_id,
        permission_type=permission_data.permission_type,
        expires_at=expires_at
    )
    
    db.add(permission)
    db.commit()
    db.refresh(permission)
    
    return {
        "id": permission.id,
        "granted_by": permission.granted_by,
        "granted_to_type": permission.granted_to_type.value,
        "granted_to_id": permission.granted_to_id,
        "resource_type": permission.resource_type.value,
        "resource_id": permission.resource_id,
        "permission_type": permission.permission_type.value,
        "created_at": permission.created_at,
        "expires_at": permission.expires_at
    }


@router.get("/permissions", response_model=List[dict])
def list_permissions(
    resource_type: ResourceType = None,
    resource_id: UUID = None,
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    """List permissions granted by current subtenant"""
    
    query = db.query(Permission).filter(Permission.granted_by == current_subtenant.id)
    
    if resource_type:
        query = query.filter(Permission.resource_type == resource_type)
    if resource_id:
        query = query.filter(Permission.resource_id == resource_id)
    
    permissions = query.all()
    
    return [
        {
            "id": p.id,
            "granted_by": p.granted_by,
            "granted_to_type": p.granted_to_type.value,
            "granted_to_id": p.granted_to_id,
            "resource_type": p.resource_type.value,
            "resource_id": p.resource_id,
            "permission_type": p.permission_type.value,
            "created_at": p.created_at,
            "expires_at": p.expires_at
        }
        for p in permissions
    ]


@router.delete("/permissions/{permission_id}")
def revoke_permission(
    permission_id: UUID,
    current_subtenant: Subtenant = Depends(get_current_active_subtenant),
    db: Session = Depends(get_db)
):
    """Revoke permission"""
    
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    # Only the granting subtenant can revoke permissions they granted
    if permission.granted_by != current_subtenant.id:
        raise HTTPException(status_code=403, detail="Only permission granter can revoke")
    
    db.delete(permission)
    db.commit()
    
    return {"message": "Permission revoked successfully"}