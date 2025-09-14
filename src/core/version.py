"""
Version configuration for Excel Consolidator

This module contains version information and configuration constants
for the application.
"""

# Application Version Information
APP_VERSION = "1.0.1"
APP_NAME = "Excel Consolidator"
APP_DESCRIPTION = "Advanced Excel file consolidation tool"

# Import configuration from config.py
try:
    from config import (
        GITHUB_OWNER, GITHUB_REPO, ERROR_REPORT_EMAIL, ERROR_REPORT_SENDER,
        UPDATE_CHECK_INTERVAL, AUTO_UPDATE_ENABLED, ERROR_REPORTING_ENABLED,
        APP_NAME, APP_VERSION, APP_DESCRIPTION
    )
except ImportError:
    # Fallback values if config.py is not available
    GITHUB_OWNER = "your_username"
    GITHUB_REPO = "excel-consolidator"
    ERROR_REPORT_EMAIL = "isaacrita.02@gmail.com"
    ERROR_REPORT_SENDER = "isaacrita.02@gmail.com"
    UPDATE_CHECK_INTERVAL = 24 * 60 * 60
    AUTO_UPDATE_ENABLED = True
    ERROR_REPORTING_ENABLED = True
    APP_NAME = "Excel Consolidator"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "Advanced Excel file consolidation tool"

# Application Metadata
BUILD_DATE = "2024-01-01"
BUILD_NUMBER = "1"
DEVELOPER = "Excel Consolidator Team"

def get_version_info():
    """
    Get comprehensive version information.
    
    Returns:
        Dictionary containing version information
    """
    return {
        "version": APP_VERSION,
        "name": APP_NAME,
        "description": APP_DESCRIPTION,
        "build_date": BUILD_DATE,
        "build_number": BUILD_NUMBER,
        "developer": DEVELOPER,
        "github_owner": GITHUB_OWNER,
        "github_repo": GITHUB_REPO
    }

def get_version_string():
    """
    Get formatted version string.
    
    Returns:
        Formatted version string
    """
    return f"{APP_NAME} v{APP_VERSION} (Build {BUILD_NUMBER})"

if __name__ == "__main__":
    # Display version information
    print(get_version_string())
    print("\nVersion Details:")
    for key, value in get_version_info().items():
        print(f"  {key}: {value}")
