#!/usr/bin/env python3
"""
Test script for Auto-Update System
"""

import sys
import os
sys.path.append('.')

def test_auto_update():
    print("🔍 Testing Auto-Update System")
    print("=" * 50)
    
    try:
        from src.modules.auto_update import AutoUpdater
        
        # Test with older version to simulate update available
        updater = AutoUpdater('1.0.0')  # Simulate older version
        
        print(f"Current version: {updater.current_version}")
        print(f"Repository: {updater.GITHUB_REPO_OWNER}/{updater.GITHUB_REPO_NAME}")
        
        # Test internet connection
        print("\n🌐 Testing internet connection...")
        internet_ok = updater.check_internet_connection()
        print(f"Internet available: {internet_ok}")
        
        if not internet_ok:
            print("❌ No internet connection - cannot test update check")
            return False
        
        # Test update check
        print("\n🔍 Checking for updates...")
        update_available = updater.check_for_updates()
        print(f"Update check completed: {update_available}")
        print(f"Update available: {updater.update_available}")
        print(f"Latest version: {updater.latest_version}")
        
        # Get detailed info
        info = updater.get_update_info()
        print(f"\n📊 Update Info:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        if updater.update_available:
            print("\n✅ SUCCESS: Auto-update system is working!")
            print("✅ Update detected from GitHub release")
            return True
        else:
            print("\n⚠️  No update detected")
            print("This could mean:")
            print("  - Current version is already latest")
            print("  - GitHub release not found")
            print("  - Repository name mismatch")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_github_api():
    """Test GitHub API directly"""
    print("\n🔍 Testing GitHub API directly...")
    print("=" * 50)
    
    try:
        import requests
        
        # Test GitHub API
        url = "https://api.github.com/repos/isaackcz/Excel-Consolidator-App/releases/latest"
        print(f"Testing URL: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GitHub API working!")
            print(f"Latest release: {data.get('tag_name', 'No tag')}")
            print(f"Release name: {data.get('name', 'No name')}")
            print(f"Published: {data.get('published_at', 'No date')}")
            return True
        elif response.status_code == 404:
            print("❌ Repository or release not found")
            print("Check if GitHub release was created properly")
            return False
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ GitHub API Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Auto-Update System Test Suite")
    print("=" * 60)
    
    # Test 1: GitHub API
    api_ok = test_github_api()
    
    # Test 2: Auto-update system
    auto_update_ok = test_auto_update()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"GitHub API: {'✅ PASS' if api_ok else '❌ FAIL'}")
    print(f"Auto-Update: {'✅ PASS' if auto_update_ok else '❌ FAIL'}")
    
    if api_ok and auto_update_ok:
        print("\n🎉 ALL TESTS PASSED! Auto-update system is working!")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    print("=" * 60)
