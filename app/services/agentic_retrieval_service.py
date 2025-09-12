from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Directory, Document, Chunk
from app.services.lingua_client import lingua_client
from app.database import get_mongodb
import uuid

class AgenticRetrievalService:
    def __init__(self):
        self.mongodb = get_mongodb()
    
    async def retrieve(
        self,
        db: Session,
        query: str,
        subtenant_id: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        
        # Step 1: Get directory structure and summaries
        directory_structure = await self._get_directory_structure(db, subtenant_id)
        
        # Step 2: LLM reasoning to identify relevant directories
        relevant_directories = await self._identify_relevant_directories(
            query, directory_structure, subtenant_id, auth_token
        )
        
        # Step 3: For each relevant directory, identify relevant documents
        relevant_documents = []
        for directory_info in relevant_directories:
            docs = await self._identify_relevant_documents(
                db, query, directory_info, auth_token
            )
            relevant_documents.extend(docs)
        
        # Step 4: For each relevant document, identify relevant chunks
        relevant_chunks = []
        for document_info in relevant_documents:
            chunks = await self._identify_relevant_chunks(
                db, query, document_info, auth_token
            )
            relevant_chunks.extend(chunks)
        
        # Step 5: Compile and rank the final results
        final_results = await self._compile_and_rank_results(
            query, relevant_chunks, auth_token
        )
        
        return {
            "query": query,
            "reasoning_path": {
                "directories_considered": relevant_directories,
                "documents_considered": relevant_documents,
                "chunks_identified": len(relevant_chunks)
            },
            "results": final_results
        }
    
    async def _get_directory_structure(
        self,
        db: Session,
        subtenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        
        query = db.query(Directory)
        
        if subtenant_id:
            subtenant_uuid = uuid.UUID(subtenant_id)
            query = query.filter(Directory.subtenant_id == subtenant_uuid)
        else:
            query = query.filter(Directory.is_private == False)
        
        directories = query.all()
        
        structure = []
        for directory in directories:
            structure.append({
                "id": str(directory.id),
                "name": directory.name,
                "path": directory.path,
                "summary": directory.summary or "No summary available",
                "document_count": len(directory.documents),
                "subdirectory_count": len(directory.children)
            })
        
        return structure
    
    async def _identify_relevant_directories(
        self,
        query: str,
        directory_structure: List[Dict[str, Any]],
        subtenant_id: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        
        directories_text = "\n".join([
            f"- {dir['path']} ({dir['name']}): {dir['summary']} "
            f"[{dir['document_count']} docs, {dir['subdirectory_count']} subdirs]"
            for dir in directory_structure
        ])
        
        prompt = f"""
        Given the user query: "{query}"
        
        Available directories:
        {directories_text}
        
        Analyze which directories are most likely to contain relevant information for this query.
        Provide your reasoning step by step and list the directory paths in order of relevance.
        
        Format your response as:
        REASONING: [Your step-by-step reasoning]
        DIRECTORIES: [comma-separated list of directory paths, in order of relevance]
        """
        
        try:
            if auth_token:
                # Create a chat session using the user's Lingua subtenant
                print("Creating chat for directory analysis...")
                chat_id = await lingua_client.create_chat_for_user(
                    "Directory Analysis", 
                    auth_token
                )
                print(f"Chat created: {chat_id}")
                response = await lingua_client.send_message(chat_id, prompt, auth_token)
                print(f"Raw LLM response: {response}")
            else:
                raise Exception("Missing auth_token for LLM interaction")
            
            if "content" in response and response["content"]:
                content = response["content"]
                print(f"Directory LLM Response: {content}")  # Debug logging
                
                # Parse the response
                reasoning = ""
                directory_paths = []
                
                if "REASONING:" in content:
                    reasoning = content.split("REASONING:")[1].split("DIRECTORIES:")[0].strip()
                
                if "DIRECTORIES:" in content:
                    dirs_text = content.split("DIRECTORIES:")[1].strip()
                    directory_paths = [path.strip() for path in dirs_text.split(",")]
                
                print(f"Parsed reasoning: {reasoning}")  # Debug logging
                print(f"Parsed directories: {directory_paths}")  # Debug logging
                
                # Filter and return relevant directories
                relevant_dirs = []
                for path in directory_paths:
                    for dir_info in directory_structure:
                        if dir_info["path"] == path:
                            dir_info["reasoning"] = reasoning
                            relevant_dirs.append(dir_info)
                            break
                
                if relevant_dirs:
                    print(f"Found {len(relevant_dirs)} relevant directories with LLM reasoning")
                    return relevant_dirs[:5]  # Limit to top 5 directories
            
        except Exception as e:
            print(f"Directory identification failed: {e}")
        
        # Fallback: return all directories
        return directory_structure[:3]
    
    async def _identify_relevant_documents(
        self,
        db: Session,
        query: str,
        directory_info: Dict[str, Any],
        auth_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        
        directory_id = uuid.UUID(directory_info["id"])
        documents = db.query(Document).filter(Document.directory_id == directory_id).all()
        
        if not documents:
            return []
        
        documents_text = "\n".join([
            f"- {doc.name} (v{doc.version}): {doc.summary or 'No summary available'}"
            for doc in documents
        ])
        
        prompt = f"""
        Given the user query: "{query}"
        
        In directory "{directory_info['path']}" which contains:
        {documents_text}
        
        Which documents are most likely to contain relevant information?
        Provide your reasoning and list the document names in order of relevance.
        
        Format your response as:
        REASONING: [Your reasoning]
        DOCUMENTS: [comma-separated list of document names]
        """
        
        try:
            if auth_token:
                chat_id = await lingua_client.create_chat_for_user(
                    "Document Analysis", 
                    auth_token
                )
                response = await lingua_client.send_message(chat_id, prompt, auth_token)
            else:
                raise Exception("Missing auth_token for LLM interaction")
            
            if "content" in response and response["content"]:
                content = response["content"]
                
                reasoning = ""
                document_names = []
                
                if "REASONING:" in content:
                    reasoning = content.split("REASONING:")[1].split("DOCUMENTS:")[0].strip()
                
                if "DOCUMENTS:" in content:
                    docs_text = content.split("DOCUMENTS:")[1].strip()
                    document_names = [name.strip() for name in docs_text.split(",")]
                
                # Filter and return relevant documents
                relevant_docs = []
                for name in document_names:
                    for doc in documents:
                        if doc.name == name:
                            relevant_docs.append({
                                "id": str(doc.id),
                                "name": doc.name,
                                "summary": doc.summary,
                                "directory_path": directory_info["path"],
                                "reasoning": reasoning
                            })
                            break
                
                return relevant_docs[:3]  # Limit to top 3 documents per directory
                
        except Exception as e:
            print(f"Document identification failed: {e}")
        
        # Fallback: return first few documents
        return [{
            "id": str(doc.id),
            "name": doc.name,
            "summary": doc.summary,
            "directory_path": directory_info["path"],
            "reasoning": "Fallback selection"
        } for doc in documents[:2]]
    
    async def _identify_relevant_chunks(
        self,
        db: Session,
        query: str,
        document_info: Dict[str, Any],
        auth_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        
        document_id = uuid.UUID(document_info["id"])
        chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
        
        if not chunks:
            return []
        
        chunks_text = "\n".join([
            f"- Chunk {chunk.chunk_index}: {chunk.title or 'No title'} - {chunk.summary or 'No summary'}"
            for chunk in chunks
        ])
        
        prompt = f"""
        Given the user query: "{query}"
        
        In document "{document_info['name']}" which contains these chunks:
        {chunks_text}
        
        Which chunks are most likely to contain relevant information?
        Provide your reasoning and list the chunk indices in order of relevance.
        
        Format your response as:
        REASONING: [Your reasoning]  
        CHUNKS: [comma-separated list of chunk indices]
        """
        
        try:
            if auth_token:
                chat_id = await lingua_client.create_chat_for_user(
                    "Chunk Analysis", 
                    auth_token
                )
                response = await lingua_client.send_message(chat_id, prompt, auth_token)
            else:
                raise Exception("Missing auth_token for LLM interaction")
            
            if "content" in response and response["content"]:
                content = response["content"]
                
                reasoning = ""
                chunk_indices = []
                
                if "REASONING:" in content:
                    reasoning = content.split("REASONING:")[1].split("CHUNKS:")[0].strip()
                
                if "CHUNKS:" in content:
                    chunks_text = content.split("CHUNKS:")[1].strip()
                    try:
                        chunk_indices = [int(idx.strip()) for idx in chunks_text.split(",")]
                    except ValueError:
                        chunk_indices = []
                
                # Get actual chunk content from MongoDB and return
                relevant_chunks = []
                for idx in chunk_indices:
                    for chunk in chunks:
                        if chunk.chunk_index == idx:
                            # Get chunk content from MongoDB
                            chunk_doc = self.mongodb.chunks.find_one({"_id": chunk.mongodb_id})
                            content_text = chunk_doc["content"] if chunk_doc else ""
                            
                            relevant_chunks.append({
                                "chunk_id": str(chunk.id),
                                "chunk_index": chunk.chunk_index,
                                "title": chunk.title,
                                "summary": chunk.summary,
                                "content": content_text,
                                "document_name": document_info["name"],
                                "directory_path": document_info["directory_path"],
                                "reasoning": reasoning
                            })
                            break
                
                return relevant_chunks[:5]  # Limit to top 5 chunks per document
                
        except Exception as e:
            print(f"Chunk identification failed: {e}")
        
        # Fallback: return first chunk with content
        if chunks:
            chunk = chunks[0]
            chunk_doc = self.mongodb.chunks.find_one({"_id": chunk.mongodb_id})
            content_text = chunk_doc["content"] if chunk_doc else ""
            
            return [{
                "chunk_id": str(chunk.id),
                "chunk_index": chunk.chunk_index,
                "title": chunk.title,
                "summary": chunk.summary,
                "content": content_text,
                "document_name": document_info["name"],
                "directory_path": document_info["directory_path"],
                "reasoning": "Fallback selection"
            }]
        
        return []
    
    async def _compile_and_rank_results(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        auth_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        
        if not chunks:
            return []
        
        chunks_summary = "\n".join([
            f"Chunk {i+1}: {chunk['document_name']} - {chunk['title'] or 'No title'} "
            f"(from {chunk['directory_path']})"
            for i, chunk in enumerate(chunks)
        ])
        
        prompt = f"""
        Given the user query: "{query}"
        
        I have identified these potentially relevant chunks:
        {chunks_summary}
        
        Rank these chunks by relevance to the query (1 being most relevant).
        Also provide a brief explanation of why each chunk is relevant.
        
        Format your response as:
        RANKING: [comma-separated list of chunk numbers in order of relevance]
        EXPLANATIONS: 
        1: [explanation for chunk 1]
        2: [explanation for chunk 2]
        ...
        """
        
        try:
            if auth_token:
                chat_id = await lingua_client.create_chat_for_user(
                    "Result Ranking", 
                    auth_token
                )
                response = await lingua_client.send_message(chat_id, prompt, auth_token)
            else:
                raise Exception("Missing auth_token for LLM interaction")
            
            if "content" in response and response["content"]:
                content = response["content"]
                
                # Parse ranking
                ranking = []
                if "RANKING:" in content:
                    ranking_text = content.split("RANKING:")[1].split("EXPLANATIONS:")[0].strip()
                    try:
                        ranking = [int(num.strip()) - 1 for num in ranking_text.split(",")]  # Convert to 0-based
                    except ValueError:
                        ranking = list(range(len(chunks)))
                
                # Parse explanations
                explanations = {}
                if "EXPLANATIONS:" in content:
                    explanations_text = content.split("EXPLANATIONS:")[1].strip()
                    for line in explanations_text.split("\n"):
                        if ":" in line:
                            try:
                                num, explanation = line.split(":", 1)
                                explanations[int(num.strip()) - 1] = explanation.strip()  # Convert to 0-based
                            except ValueError:
                                continue
                
                # Reorder chunks according to ranking
                ranked_chunks = []
                for i in ranking:
                    if i < len(chunks):
                        chunk = chunks[i].copy()
                        chunk["relevance_explanation"] = explanations.get(i, "No explanation provided")
                        chunk["rank"] = len(ranked_chunks) + 1
                        ranked_chunks.append(chunk)
                
                return ranked_chunks
                
        except Exception as e:
            print(f"Result ranking failed: {e}")
        
        # Fallback: return chunks as-is with generic ranking
        for i, chunk in enumerate(chunks):
            chunk["relevance_explanation"] = "Potentially relevant based on directory/document selection"
            chunk["rank"] = i + 1
        
        return chunks