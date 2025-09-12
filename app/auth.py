from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import requests
import logging

from app.database import get_db
from app.models import Subtenant, Permission, PermissionType, ResourceType, GrantedToType
from app.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()


class TokenData:
    def __init__(self, user_id: str, email: str):
        self.user_id = user_id
        self.email = email


def verify_token_with_census(token: str) -> Optional[TokenData]:
    """Verify JWT token with Census authentication service"""
    try:
        # First try to verify locally if we have the secret
        if hasattr(settings, 'JWT_SECRET_KEY') and settings.JWT_SECRET_KEY:
            try:
                payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get("sub")
                email = payload.get("email")
                if user_id and email:
                    return TokenData(user_id=user_id, email=email)
            except JWTError:
                pass
        
        # Fall back to Census service verification
        if not settings.CENSUS_API_URL:
            logger.error("No CENSUS_API_URL configured and local JWT verification failed")
            return None
            
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{settings.CENSUS_API_URL.rstrip('/')}/api/v1/users/me",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            user_data = response.json()
            return TokenData(
                user_id=user_data.get("id"),
                email=user_data.get("email")
            )
        else:
            logger.warning(f"Census token verification failed: {response.status_code}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error verifying token with Census: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        return None


def get_current_subtenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Subtenant:
    """Get current authenticated subtenant"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token with Census
    token_data = verify_token_with_census(credentials.credentials)
    if not token_data:
        raise credentials_exception
    
    # Get or create subtenant for this Census user
    subtenant = get_or_create_subtenant(db, token_data.user_id, token_data.email)
    if not subtenant:
        raise credentials_exception
        
    return subtenant


def get_or_create_subtenant(db: Session, census_user_id: str, email: str = None) -> Subtenant:
    """Get existing subtenant or create new one based on Census user ID"""
    subtenant = db.query(Subtenant).filter(Subtenant.census_user_id == census_user_id).first()
    
    if subtenant:
        return subtenant
    
    # Create new subtenant for this Census user
    subtenant = Subtenant(
        census_user_id=census_user_id,
        name=f"User {email.split('@')[0] if email else 'Unknown'}",
        description=f"Subtenant for Census user {email or census_user_id}",
        is_active=True
    )
    db.add(subtenant)
    db.commit()
    db.refresh(subtenant)
    
    return subtenant


def get_user_groups_from_census(census_user_id: str) -> list[str]:
    """Get list of group IDs that the Census user belongs to"""
    try:
        if not settings.CENSUS_API_URL:
            logger.warning("No CENSUS_API_URL configured for group lookup")
            return []
            
        # Note: This would need a service-to-service token or admin token
        # For now, return empty list - implement when Census provides group lookup API
        # response = requests.get(
        #     f"{settings.CENSUS_API_URL.rstrip('/')}/api/v1/users/{census_user_id}/groups",
        #     headers={"Authorization": f"Bearer {service_token}"}
        # )
        # if response.status_code == 200:
        #     groups = response.json()
        #     return [group["id"] for group in groups]
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching user groups from Census: {e}")
        return []


def get_current_active_subtenant(current_subtenant: Subtenant = Depends(get_current_subtenant)) -> Subtenant:
    """Get current active subtenant"""
    if not current_subtenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive subtenant"
        )
    return current_subtenant


def check_resource_access(
    db: Session,
    current_subtenant: Subtenant,
    resource_type: ResourceType,
    resource_id: str,
    permission_type: PermissionType
) -> bool:
    """Check if subtenant has access to a resource"""
    
    # 1. Check if resource belongs to current subtenant (owner always has full access)
    if resource_type == ResourceType.DIRECTORY:
        from app.models import Directory
        resource = db.query(Directory).filter(Directory.id == resource_id).first()
        if resource and resource.subtenant_id == current_subtenant.id:
            return True
    elif resource_type == ResourceType.DOCUMENT:
        from app.models import Document
        resource = db.query(Document).filter(Document.id == resource_id).first()
        if resource and resource.subtenant_id == current_subtenant.id:
            return True
    
    # 2. Check direct subtenant permissions
    permission = db.query(Permission).filter(
        Permission.granted_to_type == GrantedToType.SUBTENANT,
        Permission.granted_to_id == current_subtenant.id,
        Permission.resource_type == resource_type,
        Permission.resource_id == resource_id,
        Permission.permission_type == permission_type
    ).first()
    
    if permission:
        # Check if permission has expired
        if permission.expires_at is None or permission.expires_at > func.now():
            return True
    
    # 3. Check group permissions (need to get user's groups from Census)
    user_groups = get_user_groups_from_census(current_subtenant.census_user_id)
    if user_groups:
        for group_id in user_groups:
            group_permission = db.query(Permission).filter(
                Permission.granted_to_type == GrantedToType.GROUP,
                Permission.granted_to_id == group_id,
                Permission.resource_type == resource_type,
                Permission.resource_id == resource_id,
                Permission.permission_type == permission_type
            ).first()
            
            if group_permission:
                # Check if permission has expired
                if group_permission.expires_at is None or group_permission.expires_at > func.now():
                    return True
    
    return False


def can_access_resource(
    db: Session,
    current_subtenant: Subtenant, 
    resource_type: ResourceType,
    resource_id: str
) -> bool:
    """Check if subtenant can read a resource (any permission level)"""
    # Check for any permission level on the resource
    for perm_type in [PermissionType.READ, PermissionType.WRITE, PermissionType.DELETE]:
        if check_resource_access(db, current_subtenant, resource_type, resource_id, perm_type):
            return True
    return False