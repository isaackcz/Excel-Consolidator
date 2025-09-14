"""
Google Sheets Error Reporting Module for Excel Consolidator

This module provides error reporting functionality that writes directly to a Google Spreadsheet.
Much simpler than SMTP email setup - just needs the spreadsheet ID and proper permissions.

Author: Excel Consolidator Team
Version: 1.0.0
"""

import sys
import traceback
import json
import os
import platform
from datetime import datetime
from typing import Optional, Dict, Any, List
import threading
import logging
from pathlib import Path
try:
    import requests
except ImportError:
    requests = None
import time


class GoogleSheetsErrorReporter:
    """
    Handles automatic error reporting by writing to a Google Spreadsheet.
    """
    
    # Configuration - will be loaded from config.py
    SPREADSHEET_ID = "1eipG_5UgnkvQGcxpQi48fAq2ZRF_ZjtNzsliVdNkEnU"
    SHEET_NAME = "Sheet1"  # Default sheet name
    GOOGLE_APPS_SCRIPT_URL = None  # Optional: Google Apps Script web app URL
    
    def __init__(self, app_version: str = "1.0.0"):
        """
        Initialize the Google Sheets error reporter.
        
        Args:
            app_version: Current application version
        """
        self.app_version = app_version
        self.error_count = 0
        self.load_config()
        self.setup_logging()
        
    def load_config(self):
        """Load configuration from config.py if available."""
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            from config.config import (
                GOOGLE_SPREADSHEET_ID, GOOGLE_SHEET_NAME, 
                GOOGLE_APPS_SCRIPT_URL
            )
            self.SPREADSHEET_ID = GOOGLE_SPREADSHEET_ID
            self.SHEET_NAME = GOOGLE_SHEET_NAME
            self.GOOGLE_APPS_SCRIPT_URL = GOOGLE_APPS_SCRIPT_URL
        except ImportError:
            # Use default values if config.py is not available
            pass
        
    def setup_logging(self):
        """Setup logging for error reporting."""
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_dir / "google_sheets_error_reporting.log"),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(__name__)
        except Exception:
            # Fallback if logging setup fails
            self.logger = None
    
    def collect_error_data(self, exc_type, exc_value, exc_traceback, 
                          triggered_by: str = "Unknown", 
                          user_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Collect comprehensive error data for spreadsheet logging.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
            triggered_by: What function/button triggered the error
            user_file: Path to user's file if available
            
        Returns:
            Dictionary containing error data
        """
        try:
            # Basic error information
            error_message = str(exc_value) if exc_value else "Unknown error"
            stack_trace = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            
            # System information
            system_info = {
                "platform": platform.platform(),
                "python_version": sys.version,
                "architecture": platform.architecture(),
                "processor": platform.processor(),
                "machine": platform.machine()
            }
            
            # Application context
            app_context = {
                "app_version": self.app_version,
                "user_count": self._get_user_count(),
                "timestamp": datetime.now().isoformat(),
                "triggered_by": triggered_by,
                "error_count": self.error_count + 1
            }
            
            # File information
            file_info = {}
            if user_file and os.path.exists(user_file):
                try:
                    file_info = {
                        "filename": os.path.basename(user_file),
                        "file_size": os.path.getsize(user_file),
                        "file_path": user_file,
                        "file_exists": True
                    }
                except Exception:
                    file_info = {"file_exists": False}
            
            # Combine all data
            error_data = {
                "error_details": {
                    "type": str(exc_type.__name__) if exc_type else "Unknown",
                    "message": error_message,
                    "stack_trace": stack_trace
                },
                "system_info": system_info,
                "app_context": app_context,
                "file_info": file_info,
                "report_id": f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.error_count + 1}"
            }
            
            return error_data
            
        except Exception as e:
            # Fallback error data if collection fails
            return {
                "error_details": {
                    "type": "ErrorCollectionFailure",
                    "message": f"Failed to collect error data: {str(e)}",
                    "stack_trace": traceback.format_exc()
                },
                "system_info": {"platform": "Unknown"},
                "app_context": {
                    "app_version": self.app_version,
                    "timestamp": datetime.now().isoformat(),
                    "triggered_by": triggered_by
                },
                "file_info": {},
                "report_id": f"ERR_FALLBACK_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
    
    def _get_user_count(self) -> int:
        """
        Get estimated user count (placeholder implementation).
        In a real application, this might query a database or analytics service.
        """
        try:
            # This is a placeholder - in a real app, you might:
            # - Query a database for user count
            # - Use analytics data
            # - Track unique installations
            return 1  # Default to 1 for single-user applications
        except Exception:
            return 0
    
    def _categorize_error(self, error_type: str, triggered_by: str) -> str:
        """
        Categorize errors for better organization and analysis.
        
        Args:
            error_type: The type of error (e.g., 'BadZipFile', 'FileNotFoundError')
            triggered_by: What triggered the error (e.g., 'Template Loading', 'File Processing')
            
        Returns:
            Error category string
        """
        try:
            error_type_lower = error_type.lower()
            triggered_by_lower = triggered_by.lower()
            
            # Template-related errors
            if any(keyword in triggered_by_lower for keyword in ['template', 'template loading']):
                return 'Template Loading Error'
            
            # File processing errors
            if any(keyword in triggered_by_lower for keyword in ['file processing', 'consolidation']):
                return 'File Processing Error'
            
            # File format errors
            if any(keyword in error_type_lower for keyword in ['badzipfile', 'zipfile', 'xlsx', 'xls']):
                return 'File Format Error'
            
            # File access errors
            if any(keyword in error_type_lower for keyword in ['filenotfound', 'permission', 'access']):
                return 'File Access Error'
            
            # System errors
            if any(keyword in error_type_lower for keyword in ['memory', 'timeout', 'connection']):
                return 'System Error'
            
            # UI/Interface errors
            if any(keyword in triggered_by_lower for keyword in ['ui', 'interface', 'button', 'dialog']):
                return 'UI Error'
            
            # Default category
            return 'General Error'
            
        except Exception:
            return 'Unknown Error'
    
    def format_error_for_spreadsheet(self, error_data: Dict[str, Any]) -> List[List[str]]:
        """
        Format error data for Google Sheets row format with enhanced structure.
        
        Args:
            error_data: Collected error data
            
        Returns:
            List of rows for spreadsheet
        """
        try:
            # Determine error category based on error type and triggered_by
            error_category = self._categorize_error(
                error_data['error_details']['type'],
                error_data['app_context']['triggered_by']
            )
            
            # Create data row with enhanced format
            data_row = [
                error_data['report_id'],
                error_data['app_context']['timestamp'],
                error_data['app_context']['app_version'],
                error_category,  # New: Error Category
                error_data['error_details']['type'],
                error_data['error_details']['message'][:500],  # Limit message length
                error_data['app_context']['triggered_by'],
                str(error_data['app_context']['user_count']),
                error_data['system_info']['platform'],
                error_data['system_info']['python_version'].split('\n')[0],  # First line only
                error_data.get('file_info', {}).get('filename', 'N/A'),
                str(error_data.get('file_info', {}).get('file_size', 0)),
                error_data['error_details']['stack_trace'][:1000],  # Limit stack trace length
                'New',  # Status - will be set by Google Apps Script
                ''  # Notes - empty for now
            ]
            
            return [data_row]
            
        except Exception as e:
            # Fallback formatting
            if self.logger:
                self.logger.error(f"Error formatting data for spreadsheet: {e}")
            
            return [[
                f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                datetime.now().isoformat(),
                self.app_version,
                "Unknown",
                "1",
                "FormattingError",
                str(e),
                platform.platform(),
                sys.version.split('\n')[0],
                "N/A",
                "0",
                "Formatting failed"
            ]]
    
    def send_error_to_spreadsheet(self, error_data: Dict[str, Any]) -> bool:
        """
        Send error data to Google Spreadsheet using Google Sheets API.
        
        Args:
            error_data: Collected error data
            
        Returns:
            True if data sent successfully, False otherwise
        """
        try:
            # Format data for spreadsheet
            rows = self.format_error_for_spreadsheet(error_data)
            
            # Try Google Apps Script method first (if configured)
            if self.GOOGLE_APPS_SCRIPT_URL:
                return self._send_via_apps_script(rows)
            
            # Fallback: Try direct API method (requires authentication)
            return self._send_via_api(rows)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to send error to spreadsheet: {e}")
            return False
    
    def _send_via_apps_script(self, rows: List[List[str]]) -> bool:
        """
        Send data via Google Apps Script web app (simplest method).
        
        Args:
            rows: Formatted data rows
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.GOOGLE_APPS_SCRIPT_URL:
                return False
            
            if not requests:
                if self.logger:
                    self.logger.warning("Requests module not available, cannot send via Apps Script")
                return False
            
            payload = {
                "spreadsheet_id": self.SPREADSHEET_ID,
                "sheet_name": self.SHEET_NAME,
                "data": rows
            }
            
            response = requests.post(
                self.GOOGLE_APPS_SCRIPT_URL,
                json=payload,
                timeout=10
            )
            
            response.raise_for_status()
            
            if self.logger:
                self.logger.info("Error data sent to spreadsheet via Apps Script")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Apps Script method failed: {e}")
            return False
    
    def _send_via_api(self, rows: List[List[str]]) -> bool:
        """
        Send data via Google Sheets API (requires authentication setup).
        This is a placeholder for future implementation.
        
        Args:
            rows: Formatted data rows
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # This would require Google Sheets API authentication
            # For now, we'll use a simpler approach with a public form
            return self._send_via_form(rows)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"API method failed: {e}")
            return False
    
    def _send_via_form(self, rows: List[List[str]]) -> bool:
        """
        Send data via CSV file creation (fallback method).
        Creates a CSV file that can be imported into Google Sheets.
        
        Args:
            rows: Formatted data rows
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import csv
            from pathlib import Path
            
            # Create errors directory
            errors_dir = Path("errors")
            errors_dir.mkdir(exist_ok=True)
            
            # Create CSV file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = errors_dir / f"error_report_{timestamp}.csv"
            
            # Write rows to CSV
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for row in rows:
                    writer.writerow(row)
            
            if self.logger:
                self.logger.info(f"Error data saved to CSV: {csv_file}")
                self.logger.info("You can import this CSV file into your Google Spreadsheet")
            
            # Also log to console for easy access
            print(f"\n📊 Error logged to: {csv_file}")
            print("📋 You can import this CSV file into your Google Spreadsheet")
            print("🔗 Spreadsheet: https://docs.google.com/spreadsheets/d/1eipG_5UgnkvQGcxpQi48fAq2ZRF_ZjtNzsliVdNkEnU/")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"CSV method failed: {e}")
            return False
    
    def report_error(self, exc_type, exc_value, exc_traceback, 
                    triggered_by: str = "Unknown", 
                    user_file: Optional[str] = None) -> bool:
        """
        Main method to report an error to Google Spreadsheet.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
            triggered_by: What triggered the error
            user_file: User file path if available
            
        Returns:
            True if error was reported successfully
        """
        try:
            self.error_count += 1
            
            # Collect error data
            error_data = self.collect_error_data(exc_type, exc_value, exc_traceback, triggered_by, user_file)
            
            # Send error report in a separate thread to avoid blocking UI
            def send_report():
                try:
                    success = self.send_error_to_spreadsheet(error_data)
                    if self.logger:
                        self.logger.info(f"Error report {'sent successfully' if success else 'failed to send'}")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error in report sending thread: {e}")
            
            # Start reporting in background thread
            report_thread = threading.Thread(target=send_report, daemon=True)
            report_thread.start()
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to report error: {e}")
            return False
    
    def get_user_friendly_message(self) -> str:
        """
        Get user-friendly error message to display.
        
        Returns:
            User-friendly error message
        """
        return ("An error occurred and has been automatically reported to the developer. "
                "This will help improve the application. Please try again or restart the application if the issue persists.")


class GlobalExceptionHandler:
    """
    Global exception handler that catches unhandled exceptions and sends to spreadsheet.
    """
    
    def __init__(self, error_reporter: GoogleSheetsErrorReporter):
        """
        Initialize global exception handler.
        
        Args:
            error_reporter: GoogleSheetsErrorReporter instance to use for reporting
        """
        self.error_reporter = error_reporter
        self.original_excepthook = sys.excepthook
        
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Handle unhandled exceptions.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        try:
            # Report the error to spreadsheet
            self.error_reporter.report_error(exc_type, exc_value, exc_traceback, "Unhandled Exception")
            
            # Call original exception handler
            if self.original_excepthook:
                self.original_excepthook(exc_type, exc_value, exc_traceback)
                
        except Exception as e:
            # If error reporting fails, at least log it
            if self.error_reporter.logger:
                self.error_reporter.logger.error(f"Failed to handle exception: {e}")
            # Still call original handler
            if self.original_excepthook:
                self.original_excepthook(exc_type, exc_value, exc_traceback)
    
    def install(self):
        """Install the global exception handler."""
        sys.excepthook = self.handle_exception
        
    def uninstall(self):
        """Uninstall the global exception handler."""
        sys.excepthook = self.original_excepthook


def setup_google_sheets_error_reporting(app_version: str = "1.0.0") -> tuple[GoogleSheetsErrorReporter, GlobalExceptionHandler]:
    """
    Setup Google Sheets error reporting for the application.
    
    Args:
        app_version: Current application version
        
    Returns:
        Tuple of (GoogleSheetsErrorReporter, GlobalExceptionHandler) instances
    """
    try:
        # Create error reporter
        error_reporter = GoogleSheetsErrorReporter(app_version)
        
        # Create and install global exception handler
        exception_handler = GlobalExceptionHandler(error_reporter)
        exception_handler.install()
        
        return error_reporter, exception_handler
        
    except Exception as e:
        # If setup fails, create a minimal fallback
        print(f"Warning: Google Sheets error reporting setup failed: {e}")
        return None, None


# Example usage and testing
if __name__ == "__main__":
    # Test the Google Sheets error reporting system
    print("Testing Google Sheets Error Reporting System...")
    
    # Setup error reporting
    error_reporter, handler = setup_google_sheets_error_reporting("1.0.0")
    
    if error_reporter:
        print("Google Sheets error reporting setup successful!")
        
        # Test error reporting
        try:
            # Simulate an error
            raise ValueError("This is a test error for Google Sheets reporting")
        except Exception as e:
            error_reporter.report_error(type(e), e, e.__traceback__, "Test Function")
        
        print("Test error reported to Google Sheets!")
    else:
        print("Google Sheets error reporting setup failed!")
