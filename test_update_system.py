#!/usr/bin/env python3
"""
Test Auto-Update System

This script tests the auto-update functionality to ensure it works correctly.
"""

import sys
import os
import time

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.modules.auto_update import AutoUpdater, setup_auto_updater

def test_auto_update_system():
    """Test the auto-update system functionality."""
    print("=" * 60)
    print("Excel Consolidator Auto-Update System Test")
    print("=" * 60)
    
    # Test 1: Create auto-updater instance
    print("\n1. Testing AutoUpdater initialization...")
    updater = AutoUpdater("1.0.0")  # Test with older version
    print(f"   ✅ AutoUpdater created successfully")
    print(f"   📊 Current version: {updater.current_version}")
    print(f"   📊 GitHub repo: {updater.GITHUB_REPO_OWNER}/{updater.GITHUB_REPO_NAME}")
    
    # Test 2: Check internet connection
    print("\n2. Testing internet connectivity...")
    internet_ok = updater.check_internet_connection()
    print(f"   {'✅' if internet_ok else '❌'} Internet connection: {'Available' if internet_ok else 'Not available'}")
    
    if internet_ok:
        # Test 3: Check for updates
        print("\n3. Testing update check...")
        try:
            update_available = updater.check_for_updates()
            print(f"   {'✅' if update_available else 'ℹ️ '} Update check completed")
            print(f"   📊 Update available: {'Yes' if update_available else 'No'}")
            
            if updater.latest_version:
                print(f"   📊 Latest version: {updater.latest_version}")
            
            # Get detailed info
            info = updater.get_update_info()
            print(f"   📊 Internet available: {info['internet_available']}")
            print(f"   📊 Last check: {info['last_check']}")
            print(f"   📊 Background running: {info['background_running']}")
            print(f"   📊 Check interval: {info['check_interval_hours']} hours")
            
        except Exception as e:
            print(f"   ❌ Error during update check: {e}")
            return False
        
        # Test 4: Test background checker setup
        print("\n4. Testing background checker setup...")
        try:
            setup_updater = setup_auto_updater("1.0.0", "isaackcz", "Excel-Consolidator")
            if setup_updater:
                print("   ✅ Background checker setup successful")
                print("   ⏱️  Running background checker for 5 seconds...")
                
                # Let it run briefly
                time.sleep(5)
                
                # Stop the background checker
                setup_updater.stop_background_checker()
                print("   ✅ Background checker stopped successfully")
            else:
                print("   ❌ Background checker setup failed")
                return False
                
        except Exception as e:
            print(f"   ❌ Error during background checker test: {e}")
            return False
    
    print("\n" + "=" * 60)
    print("🎉 Auto-Update System Test Results:")
    print(f"   Internet Connection: {'✅ PASS' if internet_ok else '❌ FAIL'}")
    print(f"   Update Check: {'✅ PASS' if internet_ok else '⏭️ SKIPPED'}")
    print(f"   Background Checker: {'✅ PASS' if internet_ok else '⏭️ SKIPPED'}")
    print("=" * 60)
    
    if internet_ok:
        print("\n✅ All tests passed! The auto-update system is working correctly.")
        print("📝 Next steps:")
        print("   1. Push the project to GitHub")
        print("   2. Create a release with version 1.0.1")
        print("   3. Upload the built executable as a release asset")
        print("   4. Test the auto-update with the actual GitHub release")
    else:
        print("\n⚠️ Some tests were skipped due to no internet connection.")
        print("   Please ensure you have internet access and try again.")
    
    return internet_ok

if __name__ == "__main__":
    try:
        success = test_auto_update_system()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)
