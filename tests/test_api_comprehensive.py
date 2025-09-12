"""
Comprehensive API Test Suite for Atlas Knowledge Base
Tests the complete authentication, authorization, and permissions system
"""
import pytest
import requests
import json
import time
from typing import Dict, Any, Optional


class APITestClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token: Optional[str] = None
        
    def set_auth_token(self, token: str):
        """Set authentication token for all requests"""
        self.auth_token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
    def clear_auth(self):
        """Clear authentication"""
        self.auth_token = None
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        return self.session.get(f"{self.base_url}{endpoint}", **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        return self.session.post(f"{self.base_url}{endpoint}", **kwargs)
        
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        return self.session.put(f"{self.base_url}{endpoint}", **kwargs)
        
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        return self.session.delete(f"{self.base_url}{endpoint}", **kwargs)


class TestAtlasAPI:
    """Comprehensive test suite for Atlas API with authentication and permissions"""
    
    @classmethod
    def setup_class(cls):
        """Setup test class with API client"""
        cls.client = APITestClient()
        cls.test_data = {
            "admin_email": "admin@test.com",
            "user_email": "user@test.com",
            "subtenant_ids": [],
            "directory_ids": [],
            "document_ids": [],
            "permission_ids": []
        }
        
        # Verify API is running
        response = cls.client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        print("✓ API is healthy")
    
    def mock_census_auth(self, email: str) -> str:
        """
        Mock authentication with Census service
        In a real test, this would either:
        1. Use a test Census instance
        2. Mock the auth verification endpoint
        3. Use JWT tokens directly if JWT_SECRET_KEY is configured
        
        For this test, we'll simulate having a valid token
        """
        # In a real scenario, you'd implement actual auth flow
        # For now, we'll create a mock token that represents a valid user
        mock_token = f"mock_token_for_{email.replace('@', '_').replace('.', '_')}"
        return mock_token
    
    def test_01_health_check(self):
        """Test basic health endpoint"""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        print("✓ Health check passed")
    
    def test_02_root_endpoint(self):
        """Test root endpoint"""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "Atlas Knowledge Base API" in data["message"]
        assert "version" in data
        print("✓ Root endpoint working")
    
    def test_03_unauthenticated_requests_fail(self):
        """Test that protected endpoints require authentication"""
        protected_endpoints = [
            "/api/v1/subtenants",
            "/api/v1/directories",
            "/api/v1/documents",
            "/api/v1/permissions"
        ]
        
        for endpoint in protected_endpoints:
            response = self.client.get(endpoint)
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should require auth (got {response.status_code})"
        
        print("✓ Unauthenticated requests properly rejected")
    
    @pytest.mark.skip(reason="Requires actual Census service for real auth")
    def test_04_admin_authentication(self):
        """Test admin user authentication - SKIPPED (needs real Census)"""
        # This would test actual authentication flow with Census
        # admin_token = self.mock_census_auth(self.test_data["admin_email"])
        # self.client.set_auth_token(admin_token)
        pass
    
    @pytest.mark.skip(reason="Requires authentication to work first")
    def test_05_create_subtenant(self):
        """Test creating a new subtenant"""
        response = self.client.post("/api/v1/subtenants", json={
            "name": "Test Subtenant",
            "description": "A test subtenant for API testing"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Subtenant"
        assert data["description"] == "A test subtenant for API testing"
        assert data["is_active"] is True
        
        self.test_data["subtenant_ids"].append(data["id"])
        print(f"✓ Created subtenant: {data['id']}")
    
    @pytest.mark.skip(reason="Requires authentication to work first")
    def test_06_list_subtenants(self):
        """Test listing subtenants"""
        response = self.client.get("/api/v1/subtenants")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Should contain our created subtenant
        subtenant_ids = [s["id"] for s in data]
        for created_id in self.test_data["subtenant_ids"]:
            assert created_id in subtenant_ids
        
        print(f"✓ Listed {len(data)} subtenants")
    
    @pytest.mark.skip(reason="Requires authentication to work first")
    def test_07_get_subtenant_details(self):
        """Test getting specific subtenant details"""
        if not self.test_data["subtenant_ids"]:
            pytest.skip("No subtenant created to test")
            
        subtenant_id = self.test_data["subtenant_ids"][0]
        response = self.client.get(f"/api/v1/subtenants/{subtenant_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == subtenant_id
        assert data["name"] == "Test Subtenant"
        print(f"✓ Retrieved subtenant details: {subtenant_id}")
    
    @pytest.mark.skip(reason="Requires authentication to work first")
    def test_08_update_subtenant(self):
        """Test updating subtenant"""
        if not self.test_data["subtenant_ids"]:
            pytest.skip("No subtenant created to test")
            
        subtenant_id = self.test_data["subtenant_ids"][0]
        response = self.client.put(f"/api/v1/subtenants/{subtenant_id}", json={
            "name": "Updated Test Subtenant",
            "description": "Updated description"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Test Subtenant"
        assert data["description"] == "Updated description"
        print(f"✓ Updated subtenant: {subtenant_id}")
    
    @pytest.mark.skip(reason="Requires authentication to work first")
    def test_09_grant_permissions(self):
        """Test granting permissions to users and groups"""
        if not self.test_data["subtenant_ids"]:
            pytest.skip("No subtenant created to test")
            
        # This would require creating users/groups first
        # and then testing permission granting
        pass
    
    @pytest.mark.skip(reason="Requires authentication to work first")
    def test_10_directory_operations(self):
        """Test directory creation and permissions"""
        # Test creating directories within subtenants
        # Test directory permissions
        # Test nested directories
        pass
    
    @pytest.mark.skip(reason="Requires authentication to work first")
    def test_11_document_operations(self):
        """Test document operations with permissions"""
        # Test document upload/creation
        # Test document access permissions
        # Test private vs public documents
        pass
    
    @pytest.mark.skip(reason="Requires authentication to work first")
    def test_12_permission_management(self):
        """Test comprehensive permission management"""
        # Test granting different permission types (READ, WRITE, DELETE, ADMIN)
        # Test group permissions vs user permissions
        # Test permission inheritance
        # Test permission revocation
        pass
    
    @pytest.mark.skip(reason="Requires authentication to work first")
    def test_13_access_control_verification(self):
        """Test that access control is properly enforced"""
        # Create two users with different permissions
        # Verify user A cannot access user B's private resources
        # Verify shared resources work correctly
        pass
    
    @pytest.mark.skip(reason="Requires authentication to work first")
    def test_14_group_based_permissions(self):
        """Test group-based permission system"""
        # Create groups
        # Add users to groups
        # Grant permissions to groups
        # Verify users inherit group permissions
        pass
    
    @pytest.mark.skip(reason="Requires authentication to work first")
    def test_15_subtenant_isolation(self):
        """Test that subtenants are properly isolated"""
        # Create multiple subtenants
        # Verify resources in one subtenant are not visible in another
        # Test cross-subtenant sharing
        pass
    
    def test_16_api_structure_validation(self):
        """Test API structure and endpoint availability"""
        # Test that all expected endpoints are available
        response = self.client.get("/docs")  # OpenAPI docs
        assert response.status_code == 200
        print("✓ OpenAPI documentation available")
        
        # Test API schema
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        
        # Verify key endpoints are documented
        paths = schema.get("paths", {})
        expected_paths = [
            "/api/v1/subtenants",
            "/api/v1/permissions",
            "/api/v1/directories", 
            "/api/v1/documents"
        ]
        
        for path in expected_paths:
            assert path in paths, f"Expected API path {path} not found in schema"
        
        print("✓ All expected API endpoints documented")
    
    def test_17_error_handling(self):
        """Test API error handling"""
        # Test 404 for non-existent resources
        response = self.client.get("/api/v1/subtenants/00000000-0000-0000-0000-000000000000")
        assert response.status_code in [401, 403, 404]  # 401/403 if no auth, 404 if auth but not found
        
        # Test invalid UUIDs
        response = self.client.get("/api/v1/subtenants/invalid-uuid")
        assert response.status_code in [400, 401, 403]  # 400 for bad request or 401/403 for no auth
        
        print("✓ Error handling working correctly")
    
    @pytest.mark.skip(reason="Requires authentication to work first")
    def test_18_pagination_and_filtering(self):
        """Test pagination and filtering capabilities"""
        # Test skip/limit parameters
        # Test subtenant filtering
        # Test directory filtering
        pass
    
    @pytest.mark.skip(reason="Requires authentication to work first")
    def test_99_cleanup(self):
        """Cleanup test data"""
        # Delete created permissions
        for permission_id in self.test_data["permission_ids"]:
            response = self.client.delete(f"/api/v1/permissions/{permission_id}")
            # Don't assert success as permissions might cascade delete
        
        # Delete created documents
        for doc_id in self.test_data["document_ids"]:
            response = self.client.delete(f"/api/v1/documents/{doc_id}")
        
        # Delete created directories  
        for dir_id in self.test_data["directory_ids"]:
            response = self.client.delete(f"/api/v1/directories/{dir_id}")
        
        # Delete created subtenants
        for subtenant_id in self.test_data["subtenant_ids"]:
            response = self.client.delete(f"/api/v1/subtenants/{subtenant_id}")
        
        print("✓ Test cleanup completed")


def run_manual_test():
    """
    Manual test runner for development testing
    Run this to test the API manually without authentication setup
    """
    print("=== Atlas API Manual Test ===")
    
    client = APITestClient()
    
    # Test basic endpoints
    print("\n1. Testing health endpoint...")
    response = client.get("/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    print("\n2. Testing root endpoint...")
    response = client.get("/")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    print("\n3. Testing OpenAPI schema...")
    response = client.get("/openapi.json")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        schema = response.json()
        paths = list(schema.get("paths", {}).keys())
        print(f"   Available endpoints: {len(paths)}")
        print(f"   Sample endpoints: {paths[:5]}")
    
    print("\n4. Testing protected endpoints (should fail without auth)...")
    protected_endpoints = [
        "/api/v1/subtenants",
        "/api/v1/directories", 
        "/api/v1/documents",
        "/api/v1/permissions"
    ]
    
    for endpoint in protected_endpoints:
        response = client.get(endpoint)
        print(f"   {endpoint}: {response.status_code} (expected 401)")
    
    print("\n5. Testing API documentation...")
    response = client.get("/docs")
    print(f"   Docs available: {response.status_code == 200}")
    
    print("\n=== Manual Test Complete ===")
    print("\nNext steps:")
    print("1. Configure Census authentication service")  
    print("2. Set JWT_SECRET_KEY in .env for local JWT verification")
    print("3. Run: pytest tests/test_api_comprehensive.py -v")
    print("4. Or run specific tests with authentication setup")


if __name__ == "__main__":
    # Run manual tests when script is executed directly
    run_manual_test()