"""
Centralized File Processing Utilities for Excel Consolidator

This module consolidates all file processing functionality to avoid duplication
between FileProcessor and AsyncFileProcessor classes.

Author: Excel Consolidator Team
Version: 1.0.0
"""

import os
import pandas as pd
import openpyxl
import xlrd
from typing import Optional, Tuple, Union, Any
import logging


class FileProcessor:
    """
    Centralized file processor that handles different file formats.
    Consolidates functionality from multiple processor classes to follow DRY principles.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def read_excel_file(filepath: str, sheet_name: Optional[str] = None, 
                       data_only: bool = True) -> Tuple[Any, Any, str]:
        """
        Read Excel file (.xlsx, .xls)
        
        Args:
            filepath: Path to the Excel file
            sheet_name: Optional sheet name to read
            data_only: Whether to read data only (no formulas)
            
        Returns:
            Tuple of (workbook, worksheet, format_type)
        """
        try:
            if filepath.endswith('.xlsx'):
                wb = openpyxl.load_workbook(filepath, data_only=data_only)
                if sheet_name and sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                else:
                    ws = wb.active
                return wb, ws, "xlsx"
            
            elif filepath.endswith('.xls'):
                # Handle legacy Excel format
                wb_xlrd = xlrd.open_workbook(filepath)
                if sheet_name:
                    try:
                        sheet_idx = wb_xlrd.sheet_names().index(sheet_name)
                        ws_xlrd = wb_xlrd.sheet_by_index(sheet_idx)
                    except ValueError:
                        ws_xlrd = wb_xlrd.sheet_by_index(0)
                else:
                    ws_xlrd = wb_xlrd.sheet_by_index(0)
                return wb_xlrd, ws_xlrd, "xls"
            
        except Exception as e:
            return None, None, FileProcessor._get_file_read_error_message(filepath, e)
        
        return None, None, "unsupported_format"
    
    @staticmethod
    def read_csv_file(filepath: str) -> Tuple[Optional[pd.DataFrame], str]:
        """
        Read CSV file
        
        Args:
            filepath: Path to the CSV file
            
        Returns:
            Tuple of (DataFrame, status)
        """
        try:
            df = pd.read_csv(filepath)
            return df, "csv"
        except Exception as e:
            return None, FileProcessor._get_file_read_error_message(filepath, e)
    
    def validate_file(self, filepath: str) -> bool:
        """
        Validate if file exists and is readable.
        
        Args:
            filepath: Path to the file
            
        Returns:
            True if file is valid, False otherwise
        """
        try:
            return os.path.exists(filepath) and os.path.isfile(filepath)
        except Exception as e:
            self.logger.error(f"Error validating file {filepath}: {e}")
            return False
    
    def get_file_info(self, filepath: str) -> dict:
        """
        Get comprehensive file information.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Dictionary containing file information
        """
        try:
            if not self.validate_file(filepath):
                return {"exists": False}
            
            stat = os.stat(filepath)
            return {
                "exists": True,
                "filename": os.path.basename(filepath),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "extension": os.path.splitext(filepath)[1].lower(),
                "path": filepath
            }
        except Exception as e:
            self.logger.error(f"Error getting file info for {filepath}: {e}")
            return {"exists": False, "error": self._get_file_access_error_message(filepath, e)}

    @staticmethod
    def _get_file_read_error_message(filepath: str, error: Exception) -> str:
        """Get user-friendly error message for file reading errors."""
        error_str = str(error).lower()
        filename = os.path.basename(filepath)
        
        # File access/permission errors
        if ("permission denied" in error_str or "access denied" in error_str or 
            "sharing violation" in error_str or "file is being used" in error_str):
            return (f"📁 File Currently Open\n\n"
                   f"The file '{filename}' is currently open in Excel or another program.\n\n"
                   f"💡 Solution: Close the file in Excel and try again.")
        
        # File not found errors
        elif "no such file" in error_str or "file not found" in error_str:
            return (f"📄 File Not Found\n\n"
                   f"The file '{filename}' could not be found at the specified location.\n\n"
                   f"💡 Solution: Check that the file still exists and hasn't been moved or deleted.")
        
        # Password protected files
        elif "password" in error_str or "encrypted" in error_str:
            return (f"🔒 Password Protected File\n\n"
                   f"The file '{filename}' is password protected and cannot be opened.\n\n"
                   f"💡 Solution: Remove the password protection from the file or provide the password.")
        
        # Corrupted file errors
        elif ("badzipfile" in error_str or "zipfile" in error_str or 
              "corrupt" in error_str or "invalid" in error_str):
            return (f"❌ Corrupted File\n\n"
                   f"The file '{filename}' appears to be corrupted or is not a valid Excel file.\n\n"
                   f"💡 Solution: Try opening the file in Excel to repair it, or use a backup copy.")
        
        # Memory errors
        elif "memory" in error_str or "out of memory" in error_str:
            return (f"💾 File Too Large\n\n"
                   f"The file '{filename}' is too large to process with available memory.\n\n"
                   f"💡 Solution: Close other applications to free up memory, or try processing the file separately.")
        
        # Encoding/format errors
        elif ("encoding" in error_str or "decode" in error_str or 
              "utf" in error_str or "codec" in error_str):
            return (f"📝 File Encoding Issue\n\n"
                   f"The file '{filename}' has text encoding issues that prevent it from being read.\n\n"
                   f"💡 Solution: Try saving the file with UTF-8 encoding or as a new Excel file.")
        
        # Network/path errors
        elif "network" in error_str or "path" in error_str or "unc" in error_str:
            return (f"🌐 Network Path Issue\n\n"
                   f"Cannot access '{filename}' over the network connection.\n\n"
                   f"💡 Solution: Check your network connection and ensure the network path is accessible.")
        
        # Merged cell errors
        elif ("mergedcell" in error_str or "attribute 'value' is read-only" in error_str or 
              "read-only" in error_str):
            return (f"🔗 Merged Cells Detected\n\n"
                   f"The file '{filename}' contains merged cells that interfere with data processing.\n\n"
                   f"💡 Solution: Open the file in Excel, select all cells (Ctrl+A), "
                   f"then click 'Merge & Center' to unmerge all cells. Save and try again.")
        
        # Generic file error with helpful context
        else:
            return (f"⚠️ File Processing Error\n\n"
                   f"Unable to process the file '{filename}'.\n\n"
                   f"Technical details: {str(error)}\n\n"
                   f"💡 Common solutions:\n"
                   f"• Ensure the file is not open in Excel\n"
                   f"• Check that the file is not corrupted\n"
                   f"• Verify you have read permissions to the file\n"
                   f"• Try copying the file to a local folder")

    def _get_file_access_error_message(self, filepath: str, error: Exception) -> str:
        """Get user-friendly error message for file access errors."""
        error_str = str(error).lower()
        filename = os.path.basename(filepath)
        
        if ("permission denied" in error_str or "access denied" in error_str):
            return (f"🔐 Access Denied\n\n"
                   f"Cannot access file information for '{filename}'.\n\n"
                   f"💡 Solution: Check that you have read permissions to the file and folder.")
        elif "no such file" in error_str or "file not found" in error_str:
            return (f"📄 File Not Found\n\n"
                   f"The file '{filename}' does not exist at the specified location.")
        else:
            return f"Unable to access file '{filename}': {str(error)}"


# Global instance for easy access
file_processor = FileProcessor()
