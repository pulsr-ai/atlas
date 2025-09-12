from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import documents, directories, ingestion, retrieval, subtenants, permissions
from app.database import init_db

app = FastAPI(
    title="Atlas Knowledge Base",
    description="Open source knowledge base management service",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(directories.router, prefix="/api/v1", tags=["directories"])
app.include_router(ingestion.router, prefix="/api/v1", tags=["ingestion"])
app.include_router(retrieval.router, prefix="/api/v1", tags=["retrieval"])
app.include_router(subtenants.router, prefix="/api/v1", tags=["subtenants"])
app.include_router(permissions.router, prefix="/api/v1", tags=["permissions"])

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.get("/")
async def root():
    return {"message": "Atlas Knowledge Base API", "version": "0.1.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}