#!/usr/bin/env python3
"""
Performance test script for Excel Consolidator
Tests the optimized file processing with sample data
"""

import time
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_performance():
    """Test the performance improvements"""
    print("🚀 Starting Excel Consolidator Performance Test")
    print("=" * 50)
    
    # Check if we have test files
    data_folder = Path("DATA Requirements/New folder")
    if not data_folder.exists():
        print("❌ No test data folder found. Please ensure DATA Requirements/New folder exists.")
        return
    
    # Count files
    excel_files = list(data_folder.glob("*.xlsx"))
    print(f"📁 Found {len(excel_files)} Excel files to process")
    
    if len(excel_files) == 0:
        print("❌ No Excel files found in test folder")
        return
    
    # Import and test the main processor
    try:
        from core.main import ConsolidationWorker
        from PyQt5.QtCore import QCoreApplication
        import sys
        
        # Create Qt application
        app = QCoreApplication(sys.argv)
        
        # Test files
        template_file = os.path.abspath("Q3-2025-Data-Requirements-SchoolID_SchoolName.xlsx")
        source_folder = str(data_folder.absolute())
        output_folder = "."
        
        print(f"📋 Template: {template_file}")
        print(f"📁 Source: {source_folder}")
        print(f"💾 Output: {output_folder}")
        print()
        
        # Create worker instance
        worker = ConsolidationWorker(
            template_path=template_file,
            excel_folder=source_folder,
            save_folder=output_folder
        )
        
        # Measure processing time
        start_time = time.time()
        
        # Run the consolidation
        worker.run()
        
        end_time = time.time()
        processing_time = end_time - start_time
        result = True  # Assume success if no exception
        
        print()
        print("=" * 50)
        print("📊 PERFORMANCE RESULTS")
        print("=" * 50)
        print(f"⏱️  Total Processing Time: {processing_time:.2f} seconds")
        print(f"📁 Files Processed: {len(excel_files)}")
        print(f"⚡ Average Time per File: {processing_time/len(excel_files):.2f} seconds")
        print(f"🎯 Result: {'✅ SUCCESS' if result else '❌ FAILED'}")
        
        # Performance benchmarks
        if processing_time < 30:  # Less than 30 seconds for 2 files
            print("🚀 EXCELLENT: Processing time is very fast!")
        elif processing_time < 60:  # Less than 1 minute
            print("✅ GOOD: Processing time is acceptable")
        elif processing_time < 120:  # Less than 2 minutes
            print("⚠️  SLOW: Processing time needs improvement")
        else:
            print("❌ CRITICAL: Processing time is too slow!")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_performance()
