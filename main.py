#!/usr/bin/env python3
"""
Excel Consolidator - Main Entry Point

This is the main entry point for the Excel Consolidator application.
It imports and runs the main application from the src.core module.
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the main application
if __name__ == "__main__":
    try:
        from src.core.main import main
        main()
    except ImportError as e:
        print(f"Error importing main application: {e}")
        print("Please ensure all dependencies are installed:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)
