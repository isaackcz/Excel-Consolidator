#!/usr/bin/env python3
"""
Test script to simulate v1.0.1 trying to update to v1.0.2
"""

import sys
import os
sys.path.append('.')

def test_v1_0_1_to_1_0_2():
    print("🧪 Testing Auto-Update: v1.0.1 -> v1.0.2")
    print("=" * 60)
    
    try:
        from src.modules.auto_update import AutoUpdater
        
        # Simulate running v1.0.1 (with correct repository name)
        updater = AutoUpdater('1.0.1')
        
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
        
        if updater.update_available:
            print("\n🎉 SUCCESS: Auto-update system is working!")
            print(f"✅ v1.0.1 detected v1.0.2 as available update!")
            
            # Get release info
            release_info = updater.get_latest_release_info()
            if release_info:
                print(f"\n📋 Release Information:")
                print(f"  Version: {release_info.get('version')}")
                print(f"  Published: {release_info.get('published_at')}")
                print(f"  URL: {release_info.get('html_url')}")
            
            return True
        else:
            print("\n⚠️  No update detected")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_github_api_directly():
    """Test GitHub API directly"""
    print("\n🔍 Testing GitHub API directly...")
    print("=" * 40)
    
    try:
        import requests
        
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
            
            # Check assets
            assets = data.get('assets', [])
            if assets:
                asset = assets[0]
                print(f"Executable: {asset.get('name', 'No name')}")
                print(f"Size: {asset.get('size', 0) / (1024*1024):.1f} MB")
            
            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ GitHub API Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Excel Consolidator Auto-Update Test")
    print("Testing: v1.0.1 -> v1.0.2")
    print("=" * 60)
    
    # Test 1: GitHub API
    api_ok = test_github_api_directly()
    
    # Test 2: Auto-update system
    auto_update_ok = test_v1_0_1_to_1_0_2()
    
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULTS:")
    print(f"GitHub API: {'✅ PASS' if api_ok else '❌ FAIL'}")
    print(f"Auto-Update Detection: {'✅ PASS' if auto_update_ok else '❌ FAIL'}")
    
    if api_ok and auto_update_ok:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ v1.0.1 will successfully detect v1.0.2 update!")
        print("✅ Auto-update system is working perfectly!")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
    
    print("=" * 60)
