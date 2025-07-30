from typing import Optional
from sqlalchemy.orm import Session
from app.models import Document, Directory, Chunk
from app.services.lingua_client import lingua_client
from app.database import get_mongodb

class SummaryService:
    def __init__(self):
        self.mongodb = get_mongodb()
    
    async def generate_chunk_summary(self, content: str) -> str:
        
        prompt = f"""
        Please provide a concise summary (2-3 sentences) of the following text chunk:
        
        {content}
        """
        
        try:
            chat_id = "chunk_summary_session"
            response = await lingua_client.send_message(chat_id, prompt)
            
            if "content" in response and response["content"]:
                return response["content"].strip()
            else:
                return self._generate_simple_summary(content)
                
        except Exception as e:
            print(f"LLM summary generation failed: {e}")
            return self._generate_simple_summary(content)
    
    async def generate_document_summary(self, document: Document) -> str:
        
        # Get document content from MongoDB
        doc_content = self.mongodb.documents.find_one({"_id": document.mongodb_id})
        if not doc_content:
            return "No content available for summary"
        
        content = doc_content["content"]
        
        # Get chunk summaries if available
        chunk_summaries = []
        for chunk in document.chunks:
            if chunk.summary:
                chunk_summaries.append(chunk.summary)
        
        if chunk_summaries:
            # Summarize based on chunk summaries
            chunks_text = "\n".join([f"- {summary}" for summary in chunk_summaries])
            prompt = f"""
            Based on the following chunk summaries from a document titled "{document.name}", 
            provide a comprehensive document summary (3-5 sentences):
            
            Chunk summaries:
            {chunks_text}
            """
        else:
            # Summarize based on full content (truncated if too long)
            truncated_content = content[:3000] + "..." if len(content) > 3000 else content
            prompt = f"""
            Please provide a comprehensive summary (3-5 sentences) of the following document:
            
            Title: {document.name}
            Content: {truncated_content}
            """
        
        try:
            chat_id = "document_summary_session"
            response = await lingua_client.send_message(chat_id, prompt)
            
            if "content" in response and response["content"]:
                return response["content"].strip()
            else:
                return self._generate_simple_summary(content)
                
        except Exception as e:
            print(f"LLM document summary generation failed: {e}")
            return self._generate_simple_summary(content)
    
    async def generate_directory_summary(self, directory: Directory) -> str:
        
        # Get summaries of documents in this directory
        document_summaries = []
        for document in directory.documents:
            if document.summary:
                document_summaries.append(f"- {document.name}: {document.summary}")
        
        # Get summaries of subdirectories
        subdirectory_summaries = []
        for subdir in directory.children:
            if subdir.summary:
                subdirectory_summaries.append(f"- {subdir.name}/: {subdir.summary}")
        
        all_summaries = document_summaries + subdirectory_summaries
        
        if not all_summaries:
            return f"Directory '{directory.name}' contains no summarized content"
        
        summaries_text = "\n".join(all_summaries)
        
        prompt = f"""
        Please provide a summary (2-4 sentences) of the directory "{directory.name}" 
        based on the following content summaries:
        
        {summaries_text}
        
        The summary should describe what types of documents and information are contained in this directory.
        """
        
        try:
            chat_id = "directory_summary_session"
            response = await lingua_client.send_message(chat_id, prompt)
            
            if "content" in response and response["content"]:
                return response["content"].strip()
            else:
                return f"Directory containing {len(document_summaries)} documents and {len(subdirectory_summaries)} subdirectories"
                
        except Exception as e:
            print(f"LLM directory summary generation failed: {e}")
            return f"Directory containing {len(document_summaries)} documents and {len(subdirectory_summaries)} subdirectories"
    
    async def should_update_directory_summary(self, directory: Directory) -> bool:
        
        if not directory.summary:
            return True
        
        # Get current directory content
        current_docs = [doc.summary for doc in directory.documents if doc.summary]
        current_subdirs = [subdir.summary for subdir in directory.children if subdir.summary]
        
        current_content = "\n".join(current_docs + current_subdirs)
        
        prompt = f"""
        Current directory summary: {directory.summary}
        
        Current directory content summaries:
        {current_content}
        
        Does the current directory summary accurately reflect the content? 
        Answer with only "YES" or "NO".
        """
        
        try:
            chat_id = "directory_update_check_session"
            response = await lingua_client.send_message(chat_id, prompt)
            
            if "content" in response and response["content"]:
                answer = response["content"].strip().upper()
                return answer == "NO"
            else:
                return False  # Conservative: don't update if we can't determine
                
        except Exception as e:
            print(f"Directory update check failed: {e}")
            return False  # Conservative: don't update if we can't determine
    
    def _generate_simple_summary(self, content: str) -> str:
        
        # Simple fallback: take first few sentences
        sentences = content.split('. ')
        if len(sentences) >= 3:
            return '. '.join(sentences[:3]) + '.'
        else:
            return content[:200] + '...' if len(content) > 200 else content