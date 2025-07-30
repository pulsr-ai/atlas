# Atlas Knowledge Base

An open-source Python service for managing knowledge bases with intelligent document organization and agentic retrieval.

## Features

### Core Functionality
- **Single-tenant with sub-tenants**: Open source service running in private environments with optional private document spaces
- **Hierarchical document organization**: S3-style directory structure for organizing documents
- **Document versioning**: Full version control for documents with metadata tracking
- **Intelligent chunking**: LLM-powered and custom chunking strategies for optimal document segmentation
- **Agentic retrieval**: LLM-powered reasoning for context retrieval instead of traditional vector search

### Document Processing
- **Multi-format support**: Uses Microsoft's MarkItDown for converting various document formats to Markdown
- **Automatic summarization**: AI-generated summaries for chunks, documents, and directories
- **Custom chunking services**: Extensible framework for domain-specific chunking logic
- **Metadata extraction**: Rich metadata storage including tags, summaries, and document relationships

### Data Architecture
- **PostgreSQL**: Stores metadata, directory structure, document versions, and summaries
- **MongoDB**: Stores document and chunk content
- **Hierarchical organization**: Directory > Subdirectory > Document > Chunk structure

## Tech Stack

- **Python 3.12+**
- **FastAPI + Uvicorn**: High-performance async web framework
- **SQLAlchemy + Psycopg2**: PostgreSQL ORM with async support
- **MongoDB + PyMongo**: Document storage
- **Alembic**: Database migrations
- **MarkItDown**: Document format conversion
- **Pydantic**: Data validation and serialization

## API Endpoints

### Document Ingestion
- `POST /api/v1/ingest` - Upload new documents
- `POST /api/v1/ingest/version/{document_id}` - Upload new document versions

### Directory Traversal
- `GET /api/v1/directories` - List all directories
- `GET /api/v1/directories/traverse?path=/some/path` - Browse directory contents
- `GET /api/v1/directories/{directory_id}` - Get specific directory

### Document Retrieval
- `GET /api/v1/documents` - List documents
- `GET /api/v1/documents/{document_id}` - Get specific document

### Agentic Retrieval
- `POST /api/v1/retrieve` - Intelligent context retrieval using LLM reasoning
- `GET /api/v1/retrieve/explain/{query}` - Explain retrieval reasoning process

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd atlas
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Set up databases**
   - Ensure PostgreSQL is running
   - Ensure MongoDB is running
   - Run migrations: `alembic upgrade head`

6. **Start the service**
   ```bash
   python run.py
   ```

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
DATABASE_URL=postgresql://user:password@localhost/atlas
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=atlas_documents
LINGUA_API_URL=http://localhost:8080
```

### Lingua Integration

This service integrates with the Lingua LLM service for:
- Document chunking decisions
- Summary generation
- Agentic retrieval reasoning

Ensure Lingua is running and accessible at the configured URL.

## Custom Chunking Services

Create custom chunking logic by adding Python files to `app/chunking_services/`:

```python
# app/chunking_services/my_chunker.py
SUPPORTED_EXTENSIONS = ['.ext']

async def chunk(content: str, filename: str) -> List[str]:
    # Your custom chunking logic
    return chunks
```

### Built-in Chunkers
- **Markdown chunker**: Splits by headers while preserving structure
- **Python chunker**: Splits by classes and functions with context
- **Default chunker**: LLM-powered intelligent chunking

## Agentic Retrieval

The service uses LLM reasoning instead of vector search:

1. **Directory Analysis**: LLM analyzes directory summaries to identify relevant paths
2. **Document Selection**: LLM evaluates documents within relevant directories  
3. **Chunk Identification**: LLM identifies specific chunks containing relevant information
4. **Result Ranking**: LLM ranks and explains the relevance of each result

This approach provides transparent, explainable retrieval with reasoning traces.

## Data Model

```
Directory (PostgreSQL)
├── id: UUID
├── name: string
├── path: string (unique)
├── parent_id: UUID (self-referential)
├── summary: text
├── subtenant_id: UUID (optional)
└── is_private: boolean

Document (PostgreSQL)
├── id: UUID
├── name: string
├── directory_id: UUID (FK)
├── version: integer
├── summary: text
├── subtenant_id: UUID (optional)
├── is_private: boolean
└── mongodb_id: string

Chunk (PostgreSQL)
├── id: UUID
├── document_id: UUID (FK)
├── chunk_index: integer
├── title: string
├── summary: text
└── mongodb_id: string

Document Content (MongoDB)
├── _id: ObjectId
├── content: string (markdown)
└── metadata: object

Chunk Content (MongoDB)
├── _id: ObjectId
├── content: string
├── document_id: string
└── chunk_index: integer
```

## Sub-tenant Support

The service supports multiple sub-tenants through UUID-based isolation:

- Documents can be shared (default) or private to specific sub-tenants
- Directory structure can be private or shared
- API endpoints accept `subtenant_id` parameter for filtering
- Privacy is managed through boolean flags and UUID associations

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Adding New Features

1. Update models in `app/models/`
2. Create/update services in `app/services/`
3. Add API endpoints in `app/routers/`
4. Create database migrations with Alembic
5. Update tests and documentation

## License

[License information here]

## Contributing

[Contributing guidelines here]