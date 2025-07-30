import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/atlas")
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB = os.getenv("MONGODB_DB", "atlas_documents")
    LINGUA_API_URL = os.getenv("LINGUA_API_URL", "http://localhost:8080")
    
    class Config:
        env_file = ".env"

settings = Settings()