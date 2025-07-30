import re
from typing import List

SUPPORTED_EXTENSIONS = ['.md', '.markdown']

async def chunk(content: str, filename: str) -> List[str]:
    """
    Custom chunking for Markdown files.
    Splits by headers and maintains logical structure.
    """
    
    chunks = []
    current_chunk = ""
    current_level = 0
    
    lines = content.split('\n')
    
    for line in lines:
        # Check if line is a header
        header_match = re.match(r'^(#{1,6})\s+(.+)', line)
        
        if header_match:
            header_level = len(header_match.group(1))
            
            # If we have a current chunk and this is a top-level or same-level header
            if current_chunk and (header_level <= current_level or header_level == 1):
                chunks.append(current_chunk.strip())
                current_chunk = line + '\n'
                current_level = header_level
            else:
                current_chunk += line + '\n'
                if current_level == 0:
                    current_level = header_level
        else:
            current_chunk += line + '\n'
            
            # If chunk is getting too large, split it
            if len(current_chunk) > 3000:
                chunks.append(current_chunk.strip())
                current_chunk = ""
                current_level = 0
    
    # Add the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # If no chunks were created (no headers), fall back to simple chunking
    if not chunks:
        return _simple_markdown_chunk(content)
    
    return chunks


def _simple_markdown_chunk(content: str, max_size: int = 2000) -> List[str]:
    """
    Simple fallback chunking for markdown without clear header structure.
    """
    chunks = []
    current_chunk = ""
    
    paragraphs = content.split('\n\n')
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) > max_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph + '\n\n'
            else:
                # Paragraph itself is too long
                chunks.append(paragraph[:max_size])
                current_chunk = paragraph[max_size:] + '\n\n'
        else:
            current_chunk += paragraph + '\n\n'
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks