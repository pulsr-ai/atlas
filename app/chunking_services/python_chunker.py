import ast
from typing import List

SUPPORTED_EXTENSIONS = ['.py']

async def chunk(content: str, filename: str) -> List[str]:
    """
    Custom chunking for Python files.
    Splits by classes and functions while maintaining context.
    """
    
    try:
        tree = ast.parse(content)
        chunks = []
        
        # Extract module-level docstring and imports
        module_header = _extract_module_header(content)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                chunk_content = _extract_node_content(content, node, module_header)
                if chunk_content:
                    chunks.append(chunk_content)
        
        # If no functions/classes found, fall back to simple chunking
        if not chunks:
            return _simple_python_chunk(content)
        
        return chunks
        
    except SyntaxError:
        # If Python parsing fails, fall back to simple chunking
        return _simple_python_chunk(content)


def _extract_module_header(content: str) -> str:
    """
    Extract module-level docstring and imports.
    """
    lines = content.split('\n')
    header_lines = []
    
    in_docstring = False
    docstring_delimiter = None
    
    for line in lines:
        stripped = line.strip()
        
        # Check for docstring start
        if not in_docstring and (stripped.startswith('"""') or stripped.startswith("'''")):
            in_docstring = True
            docstring_delimiter = stripped[:3]
            header_lines.append(line)
            
            # Check if docstring ends on same line
            if stripped.count(docstring_delimiter) >= 2:
                in_docstring = False
                continue
        
        # Check for docstring end
        elif in_docstring and docstring_delimiter in stripped:
            header_lines.append(line)
            in_docstring = False
            continue
        
        # Include line if in docstring or is import
        elif in_docstring or stripped.startswith(('import ', 'from ')):
            header_lines.append(line)
        
        # Stop at first non-import, non-docstring code
        elif stripped and not stripped.startswith('#'):
            break
        
        # Include comments and blank lines
        else:
            header_lines.append(line)
    
    return '\n'.join(header_lines)


def _extract_node_content(content: str, node: ast.AST, module_header: str) -> str:
    """
    Extract the content of a specific AST node (class or function).
    """
    lines = content.split('\n')
    
    # Get the lines for this node
    start_line = node.lineno - 1  # AST line numbers are 1-based
    end_line = node.end_lineno if hasattr(node, 'end_lineno') else len(lines)
    
    node_lines = lines[start_line:end_line]
    node_content = '\n'.join(node_lines)
    
    # Include module header for context
    if module_header.strip():
        return f"{module_header}\n\n{node_content}"
    else:
        return node_content


def _simple_python_chunk(content: str, max_size: int = 2000) -> List[str]:
    """
    Simple fallback chunking for Python files.
    """
    chunks = []
    current_chunk = ""
    
    lines = content.split('\n')
    
    for line in lines:
        if len(current_chunk) + len(line) > max_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = line + '\n'
            else:
                chunks.append(line)
        else:
            current_chunk += line + '\n'
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks