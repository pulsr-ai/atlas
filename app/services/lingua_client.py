import httpx
from app.config import settings

class LinguaClient:
    def __init__(self):
        self.base_url = settings.LINGUA_API_URL
        
    async def send_message(self, chat_id: str, message: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/chats/{chat_id}/messages",
                json={"message": message}
            )
            return response.json()
    
    async def get_messages(self, chat_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/chats/{chat_id}/messages"
            )
            return response.json()

lingua_client = LinguaClient()