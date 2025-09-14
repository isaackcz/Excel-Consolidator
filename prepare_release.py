#!/usr/bin/env python3
"""
Release Preparation Script for Excel Consolidator

This script prepares the project for GitHub release by:
1. Building the executable
2. Creating release assets
3. Generating release notes
4. Preparing for GitHub release
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

def get_version():
    """Get current version from version.py"""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'core'))
        from version import APP_VERSION
        return APP_VERSION
    except ImportError:
        return "1.0.1"

def build_executable():
    """Build the executable using PyInstaller"""
    print("🔨 Building executable...")
    try:
        result = subprocess.run([
            "pyinstaller", 
            "Excel Consolidate.spec"
        ], capture_output=True, text=True, check=True)
        
        print("✅ Build completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def create_release_directory():
    """Create release directory with assets"""
    version = get_version()
    release_dir = Path(f"release-v{version}")
    
    print(f"📁 Creating release directory: {release_dir}")
    
    # Create release directory
    release_dir.mkdir(exist_ok=True)
    
    # Copy executable
    exe_source = Path("dist/Excel Consolidate.exe")
    if exe_source.exists():
        exe_dest = release_dir / f"Excel-Consolidator-v{version}-Windows.exe"
        shutil.copy2(exe_source, exe_dest)
        print(f"✅ Copied executable: {exe_dest}")
    else:
        print("❌ Executable not found!")
        return False
    
    # Create README for release
    readme_content = f"""# Excel Consolidator v{version}

## What's New in v{version}

- ✅ **Enhanced Auto-Update System**: Automatic background updates with internet connectivity detection
- ✅ **Improved Error Handling**: Better error reporting and recovery mechanisms
- ✅ **Silent Updates**: Updates happen in the background without user interruption
- ✅ **Rollback Protection**: Automatic backup and rollback capabilities
- ✅ **Cross-Platform Support**: Enhanced compatibility across different systems

## Installation

1. Download `Excel-Consolidator-v{version}-Windows.exe`
2. Run the executable (no installation required)
3. The application will automatically check for updates when you start it

## Features

- **Template-driven consolidation**: Use your formatted Excel template as the output structure
- **Automatic summation**: Sums numeric values across multiple Excel files
- **Format preservation**: Keeps all formatting, borders, fonts, and styles
- **Interactive verification**: Hover over consolidated cells to see file contributions
- **Background updates**: Automatically stays up-to-date with the latest features

## Auto-Update System

This version includes a sophisticated auto-update system that:
- Checks for updates every 24 hours when internet is available
- Downloads and installs updates silently in the background
- Creates automatic backups before updating
- Provides rollback functionality if needed
- Works completely transparently to the user

## Support

For issues or feature requests, please visit the GitHub repository:
https://github.com/isaackcz/Excel-Consolidator

## Changelog

### v{version} ({datetime.now().strftime('%Y-%m-%d')})
- Enhanced auto-update system with internet connectivity detection
- Improved error handling and logging
- Added rollback mechanism for failed updates
- Better background update processing
- Enhanced Windows executable update handling

### v1.0.0 (Initial Release)
- Initial release with core consolidation functionality
- Template-driven output system
- Advanced settings and configuration options
- Error reporting system
- Basic auto-update framework

---
© 2025 Excel Consolidator Team. All rights reserved.
"""
    
    readme_path = release_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"✅ Created release README: {readme_path}")
    
    return release_dir

def create_release_notes():
    """Create GitHub release notes"""
    version = get_version()
    
    release_notes = f"""## Excel Consolidator v{version}

### 🚀 New Features & Improvements

#### Enhanced Auto-Update System
- **Internet-aware updates**: Only checks for updates when internet connection is available
- **Silent background updates**: Updates happen completely in the background without user interruption
- **Automatic rollback**: Creates backups and provides rollback functionality if updates fail
- **Smart update intervals**: Checks every 24 hours with intelligent retry mechanisms

#### Improved Stability
- **Better error handling**: Enhanced error reporting and recovery mechanisms
- **Robust update process**: Improved Windows executable update handling
- **Comprehensive logging**: Detailed logging for debugging and monitoring
- **Thread-safe operations**: Better background thread management

#### User Experience
- **Seamless operation**: Users continue working while updates happen in background
- **No user interaction required**: Completely automated update process
- **Reliable delivery**: Ensures users always have the latest features and bug fixes

### 🔧 Technical Improvements
- Enhanced internet connectivity detection
- Improved GitHub API integration
- Better file handling and backup mechanisms
- Optimized update download and installation process
- Enhanced cross-platform compatibility

### 📋 Installation
1. Download the executable below
2. Run the application (no installation required)
3. The auto-update system will keep your application current automatically

### 🔄 Auto-Update Information
- **Check Frequency**: Every 24 hours when internet is available
- **Update Process**: Completely silent and automatic
- **Backup**: Automatic backup creation before updates
- **Rollback**: Available if updates fail
- **Repository**: [isaackcz/Excel-Consolidator](https://github.com/isaackcz/Excel-Consolidator)

---
**Note**: This release includes significant improvements to the auto-update system. Once you run this version, it will automatically keep itself updated with future releases."""
    
    notes_path = Path("RELEASE_NOTES.md")
    with open(notes_path, 'w', encoding='utf-8') as f:
        f.write(release_notes)
    
    print(f"✅ Created release notes: {notes_path}")
    return notes_path

def main():
    """Main release preparation function"""
    print("=" * 60)
    print("Excel Consolidator - Release Preparation")
    print("=" * 60)
    
    version = get_version()
    print(f"📊 Preparing release v{version}")
    
    # Step 1: Build executable
    if not build_executable():
        print("❌ Build failed. Cannot proceed with release preparation.")
        return False
    
    # Step 2: Create release directory
    release_dir = create_release_directory()
    if not release_dir:
        print("❌ Failed to create release directory.")
        return False
    
    # Step 3: Create release notes
    create_release_notes()
    
    print("\n" + "=" * 60)
    print("🎉 Release Preparation Complete!")
    print("=" * 60)
    print(f"📁 Release directory: {release_dir}")
    print(f"📄 Release notes: RELEASE_NOTES.md")
    print("\n📋 Next Steps:")
    print("1. Review the release directory contents")
    print("2. Test the executable to ensure it works properly")
    print("3. Push changes to GitHub")
    print("4. Create a new release on GitHub:")
    print(f"   - Tag: v{version}")
    print(f"   - Title: Excel Consolidator v{version}")
    print("   - Upload: Excel-Consolidator-v{version}-Windows.exe")
    print("   - Use the release notes from RELEASE_NOTES.md")
    print("\n🔗 GitHub Release URL:")
    print("https://github.com/isaackcz/Excel-Consolidator/releases/new")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Release preparation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error during release preparation: {e}")
        sys.exit(1)
