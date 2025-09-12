from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pymongo import MongoClient
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

mongo_client = MongoClient(settings.MONGODB_URL)
mongodb = mongo_client[settings.MONGODB_DB]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_mongodb():
    return mongodb

async def init_db():
    from app.models import Directory, Document, Chunk, Subtenant, Permission
    Base.metadata.create_all(bind=engine)