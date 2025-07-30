import os
import importlib.util
from typing import List, Optional
from app.services.lingua_client import lingua_client

class ChunkingService:
    def __init__(self):
        self.default_chunk_size = 2000  # characters
        self.custom_chunkers = self._load_custom_chunkers()
    
    async def chunk_document(self, content: str, filename: str) -> List[str]:
        
        file_extension = os.path.splitext(filename)[1].lower()
        
        # Check if we have a custom chunker for this file type
        custom_chunker = self._get_custom_chunker(file_extension)
        if custom_chunker:
            return await custom_chunker(content, filename)
        
        # Use default chunking strategy
        return await self._default_chunk(content)
    
    async def _default_chunk(self, content: str) -> List[str]:
        
        # If content is small enough, return as single chunk
        if len(content) <= self.default_chunk_size:
            return [content]
        
        # Use LLM-based chunking for larger documents
        return await self._llm_chunk(content)
    
    async def _llm_chunk(self, content: str) -> List[str]:
        
        # Create a chat session for chunking
        chat_id = "chunking_session"  # In practice, you'd create unique chat IDs
        
        prompt = f"""
        Please analyze the following document and break it down into logical chunks (chapters, sections, or topics).
        Each chunk should be self-contained but not exceed 2000 characters.
        Return the chunks separated by "---CHUNK---".
        
        Document:
        {content}
        """
        
        try:
            response = await lingua_client.send_message(chat_id, prompt)
            
            # Parse the response to extract chunks
            if "content" in response and response["content"]:
                chunks_text = response["content"]
                chunks = [chunk.strip() for chunk in chunks_text.split("---CHUNK---") if chunk.strip()]
                
                # If LLM chunking failed, fall back to simple chunking
                if not chunks:
                    return self._simple_chunk(content)
                
                return chunks
            else:
                # Fall back to simple chunking
                return self._simple_chunk(content)
                
        except Exception as e:
            print(f"LLM chunking failed: {e}")
            # Fall back to simple chunking
            return self._simple_chunk(content)
    
    def _simple_chunk(self, content: str) -> List[str]:
        
        chunks = []
        current_chunk = ""
        
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(paragraph) > self.default_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # Paragraph itself is too long, split by sentences
                    sentences = paragraph.split('. ')
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) > self.default_chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                current_chunk = sentence
                            else:
                                # Sentence is too long, split by character limit
                                chunks.append(sentence[:self.default_chunk_size])
                                current_chunk = sentence[self.default_chunk_size:]
                        else:
                            current_chunk += sentence + ". "
            else:
                current_chunk += paragraph + "\n\n"
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _load_custom_chunkers(self) -> dict:
        
        chunkers = {}
        chunking_services_dir = "app/chunking_services"
        
        if not os.path.exists(chunking_services_dir):
            return chunkers
        
        for filename in os.listdir(chunking_services_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]
                module_path = os.path.join(chunking_services_dir, filename)
                
                try:
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Look for a chunk function and supported extensions
                    if hasattr(module, 'chunk') and hasattr(module, 'SUPPORTED_EXTENSIONS'):
                        for ext in module.SUPPORTED_EXTENSIONS:
                            chunkers[ext] = module.chunk
                            
                except Exception as e:
                    print(f"Failed to load chunking service {filename}: {e}")
        
        return chunkers
    
    def _get_custom_chunker(self, file_extension: str) -> Optional[callable]:
        return self.custom_chunkers.get(file_extension)