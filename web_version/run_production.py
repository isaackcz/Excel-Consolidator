"""
Production server runner using Waitress (cross-platform)
Install: pip install waitress
"""
from waitress import serve
from app import app

if __name__ == '__main__':
    print("=" * 60)
    print("Excel Consolidator Web Server - Production Mode")
    print("=" * 60)
    print("Server starting at: http://0.0.0.0:8080")
    print("Threads: 4")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    serve(app, host='0.0.0.0', port=8080, threads=4)
