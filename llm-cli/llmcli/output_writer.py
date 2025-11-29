"""
Output writer for streaming LLM responses
"""

import sys
from typing import Optional, TextIO


class OutputWriter:
    """Handles streaming output to stdout or file"""
    
    def __init__(self, output_path: Optional[str] = None):
        """
        Initialize output writer
        
        Args:
            output_path: File path for output, or None for stdout
        """
        self.output_path = output_path
        self.file_handle: Optional[TextIO] = None
        self._opened = False
    
    def open(self):
        """Open the output destination"""
        if self.output_path:
            try:
                self.file_handle = open(self.output_path, 'w', encoding='utf-8')
                self._opened = True
            except Exception as e:
                raise IOError(f"Failed to open output file '{self.output_path}': {e}")
        else:
            # Use stdout
            self.file_handle = sys.stdout
            self._opened = True
    
    def write_token(self, token: str):
        """
        Write a single token (streaming)
        
        Args:
            token: Token to write
        """
        if not self._opened or not self.file_handle:
            raise RuntimeError("OutputWriter not opened")
        
        self.file_handle.write(token)
        self.file_handle.flush()
    
    def finalize(self):
        """Flush and close output"""
        if self.file_handle and self._opened:
            self.file_handle.flush()
            # Only close if we opened a file (don't close stdout)
            if self.output_path and self.file_handle != sys.stdout:
                self.file_handle.close()
            self._opened = False
    
    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.finalize()
        return False
