import httpx
from app.config import settings
from typing import Optional, Dict, Any
import uuid

class LinguaClient:
    def __init__(self):
        self.base_url = settings.LINGUA_API_URL
        
    async def get_or_create_lingua_subtenant(self, token: str) -> str:
        """Get the user's Lingua subtenant from Census, or create it if it doesn't exist"""
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        async with httpx.AsyncClient() as client:
            # Step 1: Get current user info from Census
            census_response = await client.get(
                f"{settings.CENSUS_API_URL}/api/v1/users/me",
                headers=headers
            )
            if census_response.status_code != 200:
                raise Exception(f"Failed to get user info from Census: {census_response.status_code} - {census_response.text}")
            
            user_data = census_response.json()
            user_id = user_data["id"]
            
            # Step 2: Check if user has a Lingua subtenant
            lingua_subtenant_id = None
            for service_access in user_data.get("service_access", []):
                if service_access["service"] == "lingua" and service_access["active"]:
                    lingua_subtenant_id = service_access["subtenant_id"]
                    break
            
            # Step 3: If no Lingua subtenant exists, create one
            if not lingua_subtenant_id:
                # Create subtenant in Lingua
                lingua_response = await client.post(
                    f"{self.base_url}/api/v1/subtenants/",
                    headers=headers,
                    json={
                        "name": f"User {user_data['email']}",
                        "description": f"Lingua subtenant for user {user_data['email']}"
                    }
                )
                if lingua_response.status_code != 200:
                    raise Exception(f"Failed to create Lingua subtenant: {lingua_response.status_code} - {lingua_response.text}")
                
                lingua_subtenant_data = lingua_response.json()
                lingua_subtenant_id = lingua_subtenant_data["id"]
                
                # Store the subtenant mapping in Census
                census_grant_response = await client.post(
                    f"{settings.CENSUS_API_URL}/api/v1/users/{user_id}/service-access",
                    headers=headers,
                    json={
                        "service": "lingua",
                        "subtenant_id": lingua_subtenant_id
                    }
                )
                if census_grant_response.status_code != 200:
                    print(f"Warning: Failed to store Lingua subtenant in Census: {census_grant_response.status_code} - {census_grant_response.text}")
            
            return lingua_subtenant_id

    async def create_chat_for_user(self, title: str = "Atlas Retrieval Session", token: Optional[str] = None) -> str:
        """Create a chat session for the current user and return the chat_id"""
        if not token:
            raise Exception("Token required for chat creation")
            
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        
        # Get or create the user's Lingua subtenant
        lingua_subtenant_id = await self.get_or_create_lingua_subtenant(token)
        
        async with httpx.AsyncClient() as client:
            # Create the chat session
            chat_response = await client.post(
                f"{self.base_url}/api/v1/subtenants/{lingua_subtenant_id}/chats",
                headers=headers,
                json={"title": title}
            )
            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                return chat_data["id"]
            else:
                raise Exception(f"Failed to create chat: {chat_response.status_code} - {chat_response.text}")
    
    async def send_message(self, chat_id: str, message: str, token: Optional[str] = None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/chats/{chat_id}/messages",
                headers=headers,
                json={"content": message}
            )
            if response.status_code == 200:
                response_data = response.json()
                # Extract the assistant's message content from the response
                if "message" in response_data and "content" in response_data["message"]:
                    return {"content": response_data["message"]["content"]}
                else:
                    return response_data
            else:
                raise Exception(f"Failed to send message: {response.status_code} - {response.text}")
    
    async def get_messages(self, chat_id: str, token: Optional[str] = None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/chats/{chat_id}/messages",
                headers=headers
            )
            return response.json()

lingua_client = LinguaClient()