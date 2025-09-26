"""
Common Utilities for Excel Consolidator

This module contains shared utility functions used across the application
to avoid code duplication and follow DRY principles.

Author: Excel Consolidator Team  
Version: 1.0.0
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import platform
from datetime import datetime


def setup_project_path():
    """
    Setup project path for imports.
    Centralized function to avoid duplication across modules.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    return project_root


def setup_logging(log_name: str = "app", log_dir: str = "logs") -> logging.Logger:
    """
    Setup standardized logging configuration.
    
    Args:
        log_name: Name for the logger
        log_dir: Directory for log files
        
    Returns:
        Configured logger instance
    """
    try:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path / f"{log_name}.log"),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(log_name)
    except Exception:
        # Fallback if logging setup fails
        return logging.getLogger(log_name)


def get_system_info() -> Dict[str, Any]:
    """
    Get comprehensive system information.
    Centralized function to avoid duplication in error reporting.
    
    Returns:
        Dictionary containing system information
    """
    try:
        return {
            "platform": platform.platform(),
            "python_version": sys.version,
            "architecture": platform.architecture(),
            "processor": platform.processor(),
            "machine": platform.machine(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version()
        }
    except Exception:
        return {"platform": "Unknown", "python_version": sys.version}


def safe_path_join(*args) -> str:
    """
    Safely join path components.
    
    Args:
        *args: Path components to join
        
    Returns:
        Joined path string
    """
    return os.path.join(*args)


def ensure_directory(directory_path: str) -> bool:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        directory_path: Path to directory
        
    Returns:
        True if directory exists or was created successfully
    """
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def format_timestamp(timestamp: Optional[float] = None) -> str:
    """
    Format timestamp to standard string format.
    
    Args:
        timestamp: Unix timestamp (defaults to current time)
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = datetime.now().timestamp()
    
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing/replacing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename string
    """
    import re
    # Remove or replace invalid characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing whitespace and dots
    safe_name = safe_name.strip(' .')
    return safe_name if safe_name else "unnamed"


def get_file_size_readable(size_bytes: int) -> str:
    """
    Convert file size in bytes to human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human readable size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


# Common constants to avoid duplication
DEFAULT_ENCODING = 'utf-8'
TEMP_FILE_PREFIX = '~$'
SUPPORTED_EXCEL_EXTENSIONS = ['.xlsx', '.xls']
SUPPORTED_CSV_EXTENSIONS = ['.csv']
ALL_SUPPORTED_EXTENSIONS = SUPPORTED_EXCEL_EXTENSIONS + SUPPORTED_CSV_EXTENSIONS
