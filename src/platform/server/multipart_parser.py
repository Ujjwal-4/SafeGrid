"""
server/multipart_parser.py
Parses multipart/form-data payloads from HTTP request body.
Extracts uploaded files and form fields without external dependencies.
"""

import re
from typing import Dict, Any, Tuple, Optional

def parse_multipart_form_data(
    body_bytes: bytes,
    content_type_header: str
) -> Tuple[Dict[str, str], Dict[str, Tuple[str, bytes]]]:
    """
    Parses multipart/form-data body.
    Returns:
    - fields: {field_name: string_value}
    - files: {field_name: (filename, file_bytes)}
    """
    fields = {}
    files = {}
    
    # Extract boundary from header
    match = re.search(r'boundary=([^;]+)', content_type_header, re.IGNORECASE)
    if not match:
        return fields, files
        
    boundary = match.group(1).strip('"\'').encode('ascii')
    boundary_marker = b'--' + boundary
    
    parts = body_bytes.split(boundary_marker)
    for part in parts:
        part = part.strip(b'\r\n')
        if not part or part == b'--':
            continue
            
        header_end = part.find(b'\r\n\r\n')
        if header_end == -1:
            continue
            
        header_bytes = part[:header_end]
        content_bytes = part[header_end + 4:]
        
        # Remove trailing \r\n if present
        if content_bytes.endswith(b'\r\n'):
            content_bytes = content_bytes[:-2]
            
        headers_text = header_bytes.decode('utf-8', errors='replace')
        
        # Parse Content-Disposition
        cd_match = re.search(r'Content-Disposition:\s*form-data;\s*name="([^"]+)"(?:;\s*filename="([^"]+)")?', headers_text, re.IGNORECASE)
        if not cd_match:
            continue
            
        name = cd_match.group(1)
        filename = cd_match.group(2)
        
        if filename:
            files[name] = (filename, content_bytes)
        else:
            fields[name] = content_bytes.decode('utf-8', errors='replace')
            
    return fields, files
