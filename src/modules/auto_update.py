"""
Automatic Update System for Excel Consolidator

This module provides automatic update functionality that:
- Checks for new versions from GitHub releases
- Downloads and installs updates silently
- Handles update process without user interruption
- Ensures smooth updates without manual re-downloading

Author: Excel Consolidator Team
Version: 1.0.0
"""

import os
import sys
import json
import requests
import subprocess
import shutil
import tempfile
import threading
import time
import hashlib
import zipfile
import socket
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
import platform


class AutoUpdater:
    """
    Handles automatic updates for the Excel Consolidator application.
    """
    
    # Configuration
    GITHUB_REPO_OWNER = "isaackcz"  # GitHub username
    GITHUB_REPO_NAME = "Excel-Consolidator"  # Repository name
    CURRENT_VERSION = "1.0.1"  # Current application version
    CHECK_INTERVAL = 24 * 60 * 60  # Check every 24 hours (in seconds)
    
    def __init__(self, current_version: str = CURRENT_VERSION, github_owner: str = None, github_repo: str = None):
        """
        Initialize the auto-updater.
        
        Args:
            current_version: Current application version
            github_owner: GitHub repository owner (optional, will load from config)
            github_repo: GitHub repository name (optional, will load from config)
        """
        self.current_version = current_version
        self.latest_version = None
        self.update_available = False
        self.is_updating = False
        self.last_check_time = None
        self.background_thread = None
        self.stop_background = False
        self.internet_available = False
        self.load_config(github_owner, github_repo)
        self.setup_logging()
    
    def load_config(self, github_owner: str = None, github_repo: str = None):
        """Load configuration from config.py if available."""
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            from config.config import GITHUB_OWNER, GITHUB_REPO, UPDATE_CHECK_INTERVAL
            self.GITHUB_REPO_OWNER = github_owner or GITHUB_OWNER
            self.GITHUB_REPO_NAME = github_repo or GITHUB_REPO
            self.CHECK_INTERVAL = UPDATE_CHECK_INTERVAL
        except ImportError:
            # Use provided values or defaults if config.py is not available
            self.GITHUB_REPO_OWNER = github_owner or self.GITHUB_REPO_OWNER
            self.GITHUB_REPO_NAME = github_repo or self.GITHUB_REPO_NAME
        
    def setup_logging(self):
        """Setup logging for auto-updater."""
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_dir / "auto_update.log"),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(__name__)
        except Exception:
            self.logger = None
    
    def check_internet_connection(self) -> bool:
        """
        Check if internet connection is available.
        
        Returns:
            True if internet is available, False otherwise
        """
        try:
            # Try to connect to a reliable host
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            self.internet_available = True
            if self.logger:
                self.logger.debug("Internet connection is available")
            return True
        except OSError:
            try:
                # Fallback: try to connect to GitHub
                socket.create_connection(("api.github.com", 443), timeout=5)
                self.internet_available = True
                if self.logger:
                    self.logger.debug("Internet connection is available (GitHub)")
                return True
            except OSError:
                self.internet_available = False
                if self.logger:
                    self.logger.warning("No internet connection available")
                return False
        except Exception as e:
            self.internet_available = False
            if self.logger:
                self.logger.error(f"Error checking internet connection: {e}")
            return False
    
    def check_for_updates(self) -> bool:
        """
        Check if a new version is available.
        
        Returns:
            True if update is available, False otherwise
        """
        try:
            # First check internet connectivity
            if not self.check_internet_connection():
                if self.logger:
                    self.logger.info("Skipping update check - no internet connection")
                return False
            
            if self.logger:
                self.logger.info(f"Checking for updates (current version: {self.current_version})")
            
            self.last_check_time = datetime.now()
            
            # Get latest release info from GitHub
            latest_release = self._get_latest_release()
            if not latest_release:
                if self.logger:
                    self.logger.warning("Could not fetch latest release information")
                return False
            
            self.latest_version = latest_release.get('tag_name', '').lstrip('v')
            
            # Compare versions
            if self._is_newer_version(self.latest_version, self.current_version):
                self.update_available = True
                if self.logger:
                    self.logger.info(f"Update available: {self.current_version} -> {self.latest_version}")
                return True
            else:
                self.update_available = False
                if self.logger:
                    self.logger.info("Application is up to date")
                return False
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error checking for updates: {e}")
            return False
    
    def _get_latest_release(self) -> Optional[Dict[str, Any]]:
        """
        Get latest release information from GitHub API.
        
        Returns:
            Latest release data or None if failed
        """
        try:
            url = f"https://api.github.com/repos/{self.GITHUB_REPO_OWNER}/{self.GITHUB_REPO_NAME}/releases/latest"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            if self.logger:
                self.logger.error(f"Failed to fetch release info: {e}")
            return None
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error fetching release info: {e}")
            return None
    
    def _is_newer_version(self, latest: str, current: str) -> bool:
        """
        Compare version strings to determine if latest is newer.
        
        Args:
            latest: Latest version string
            current: Current version string
            
        Returns:
            True if latest is newer than current
        """
        try:
            # Simple version comparison (assumes semantic versioning)
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            # Pad with zeros if needed
            max_len = max(len(latest_parts), len(current_parts))
            latest_parts.extend([0] * (max_len - len(latest_parts)))
            current_parts.extend([0] * (max_len - len(current_parts)))
            
            return latest_parts > current_parts
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error comparing versions: {e}")
            return False
    
    def download_update(self) -> Optional[str]:
        """
        Download the latest update.
        
        Returns:
            Path to downloaded update file or None if failed
        """
        try:
            if not self.update_available or not self.latest_version:
                if self.logger:
                    self.logger.warning("No update available or version not set")
                return None
            
            if self.logger:
                self.logger.info(f"Downloading update to version {self.latest_version}")
            
            # Get release assets
            latest_release = self._get_latest_release()
            if not latest_release:
                return None
            
            # Find the appropriate asset for the current platform
            asset_url = self._get_asset_url(latest_release)
            if not asset_url:
                if self.logger:
                    self.logger.error("No suitable update asset found for current platform")
                return None
            
            # Download the asset
            download_path = self._download_asset(asset_url)
            return download_path
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error downloading update: {e}")
            return None
    
    def _get_asset_url(self, release_data: Dict[str, Any]) -> Optional[str]:
        """
        Get the appropriate asset URL for the current platform.
        
        Args:
            release_data: Release data from GitHub API
            
        Returns:
            Asset download URL or None if not found
        """
        try:
            assets = release_data.get('assets', [])
            if not assets:
                return None
            
            # Determine platform-specific asset name
            platform_name = self._get_platform_asset_name()
            
            # Find matching asset
            for asset in assets:
                asset_name = asset.get('name', '').lower()
                if platform_name in asset_name:
                    return asset.get('browser_download_url')
            
            # Fallback: use first asset if no platform-specific match
            if assets:
                return assets[0].get('browser_download_url')
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting asset URL: {e}")
            return None
    
    def _get_platform_asset_name(self) -> str:
        """
        Get platform-specific asset name.
        
        Returns:
            Platform identifier string
        """
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "windows":
            if "64" in machine or "x86_64" in machine or "amd64" in machine:
                return "windows-x64"
            else:
                return "windows-x86"
        elif system == "darwin":  # macOS
            if "arm" in machine or "aarch64" in machine:
                return "macos-arm64"
            else:
                return "macos-x64"
        elif system == "linux":
            if "64" in machine or "x86_64" in machine or "amd64" in machine:
                return "linux-x64"
            else:
                return "linux-x86"
        else:
            return "unknown"
    
    def _download_asset(self, asset_url: str) -> Optional[str]:
        """
        Download asset from URL.
        
        Args:
            asset_url: URL to download asset from
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Create temporary directory for download
            temp_dir = tempfile.mkdtemp()
            
            # Determine file extension
            if asset_url.lower().endswith('.zip'):
                filename = "update.zip"
            elif asset_url.lower().endswith('.exe'):
                filename = "update.exe"
            else:
                filename = "update"
            
            download_path = os.path.join(temp_dir, filename)
            
            # Download with progress tracking
            if self.logger:
                self.logger.info(f"Downloading from: {asset_url}")
            
            response = requests.get(asset_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress every 10%
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if int(progress) % 10 == 0 and downloaded > 0:
                                if self.logger:
                                    self.logger.info(f"Download progress: {progress:.1f}%")
            
            if self.logger:
                self.logger.info(f"Download completed: {download_path}")
            
            return download_path
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error downloading asset: {e}")
            return None
    
    def install_update(self, update_path: str) -> bool:
        """
        Install the downloaded update.
        
        Args:
            update_path: Path to the downloaded update file
            
        Returns:
            True if installation successful, False otherwise
        """
        try:
            if self.logger:
                self.logger.info(f"Installing update from: {update_path}")
            
            self.is_updating = True
            
            # Get application directory
            app_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
            
            # Handle different update file types
            if update_path.endswith('.zip'):
                return self._install_zip_update(update_path, app_dir)
            elif update_path.endswith('.exe'):
                return self._install_exe_update(update_path, app_dir)
            else:
                if self.logger:
                    self.logger.error(f"Unsupported update file format: {update_path}")
                return False
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error installing update: {e}")
            return False
        finally:
            self.is_updating = False
    
    def _install_zip_update(self, zip_path: str, app_dir: Path) -> bool:
        """
        Install update from ZIP file.
        
        Args:
            zip_path: Path to ZIP update file
            app_dir: Application directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup of current application
            backup_dir = app_dir / "backup"
            backup_dir.mkdir(exist_ok=True)
            
            if self.logger:
                self.logger.info("Creating backup of current application")
            
            # Backup current files (excluding backup directory itself)
            for item in app_dir.iterdir():
                if item.name != "backup":
                    backup_item = backup_dir / item.name
                    if item.is_file():
                        shutil.copy2(item, backup_item)
                    elif item.is_dir():
                        shutil.copytree(item, backup_item, dirs_exist_ok=True)
            
            # Create a backup marker file
            backup_marker = backup_dir / "backup_info.json"
            backup_info = {
                "timestamp": datetime.now().isoformat(),
                "version": self.current_version,
                "app_dir": str(app_dir)
            }
            with open(backup_marker, 'w') as f:
                json.dump(backup_info, f, indent=2)
            
            # Extract update
            if self.logger:
                self.logger.info("Extracting update files")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(app_dir)
            
            if self.logger:
                self.logger.info("Update installation completed successfully")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error installing ZIP update: {e}")
            return False
    
    def _install_exe_update(self, exe_path: str, app_dir: Path) -> bool:
        """
        Install update from EXE file.
        
        Args:
            exe_path: Path to EXE update file
            app_dir: Application directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.logger:
                self.logger.info("Installing EXE update")
            
            # For Windows executable updates, we need to handle this carefully
            if platform.system().lower() == "windows":
                # Create a batch script to handle the update
                batch_script = self._create_update_script(exe_path, app_dir)
                if batch_script:
                    # Run the batch script which will handle the update
                    subprocess.Popen([batch_script], shell=True)
                    if self.logger:
                        self.logger.info("Update script started - application will restart")
                    return True
                else:
                    if self.logger:
                        self.logger.error("Failed to create update script")
                    return False
            else:
                # For non-Windows systems, just run the installer
                subprocess.run([exe_path], check=True)
                if self.logger:
                    self.logger.info("Update installer completed successfully")
                return True
            
        except subprocess.CalledProcessError as e:
            if self.logger:
                self.logger.error(f"Update installer failed: {e}")
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error installing EXE update: {e}")
            return False
    
    def _create_update_script(self, exe_path: str, app_dir: Path) -> Optional[str]:
        """
        Create a batch script to handle Windows update installation.
        
        Args:
            exe_path: Path to the update EXE
            app_dir: Application directory
            
        Returns:
            Path to created script or None if failed
        """
        try:
            # Create a temporary batch script
            script_content = f'''@echo off
echo Updating Excel Consolidator...

REM Wait a moment for the application to close
timeout /t 3 /nobreak >nul

REM Copy the new executable
copy "{exe_path}" "{app_dir}\\Excel Consolidate.exe" /Y

REM Clean up
del "{exe_path}" /Q

REM Restart the application
start "" "{app_dir}\\Excel Consolidate.exe"

echo Update completed successfully!
'''
            
            # Write script to temp file
            script_path = os.path.join(tempfile.gettempdir(), "excel_consolidator_update.bat")
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            if self.logger:
                self.logger.info(f"Created update script: {script_path}")
            
            return script_path
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error creating update script: {e}")
            return None
    
    def rollback_update(self, app_dir: Path) -> bool:
        """
        Rollback to the previous version using backup.
        
        Args:
            app_dir: Application directory
            
        Returns:
            True if rollback successful, False otherwise
        """
        try:
            backup_dir = app_dir / "backup"
            backup_marker = backup_dir / "backup_info.json"
            
            if not backup_dir.exists() or not backup_marker.exists():
                if self.logger:
                    self.logger.error("No backup found for rollback")
                return False
            
            if self.logger:
                self.logger.info("Starting rollback process")
            
            # Read backup info
            with open(backup_marker, 'r') as f:
                backup_info = json.load(f)
            
            # Restore files from backup
            for backup_item in backup_dir.iterdir():
                if backup_item.name == "backup_info.json":
                    continue
                
                target_item = app_dir / backup_item.name
                
                if backup_item.is_file():
                    shutil.copy2(backup_item, target_item)
                elif backup_item.is_dir():
                    if target_item.exists():
                        shutil.rmtree(target_item)
                    shutil.copytree(backup_item, target_item)
            
            if self.logger:
                self.logger.info(f"Rollback completed to version {backup_info.get('version', 'unknown')}")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during rollback: {e}")
            return False
    
    def perform_update(self) -> bool:
        """
        Perform complete update process.
        
        Returns:
            True if update successful, False otherwise
        """
        try:
            if not self.update_available:
                if self.logger:
                    self.logger.info("No update available")
                return False
            
            if self.logger:
                self.logger.info("Starting update process")
            
            # Download update
            update_path = self.download_update()
            if not update_path:
                if self.logger:
                    self.logger.error("Failed to download update")
                return False
            
            # Install update
            success = self.install_update(update_path)
            
            # Clean up downloaded file
            try:
                os.remove(update_path)
                # Also remove parent temp directory if empty
                temp_dir = os.path.dirname(update_path)
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception:
                pass  # Ignore cleanup errors
            
            if success:
                if self.logger:
                    self.logger.info("Update completed successfully")
                self.update_available = False
                return True
            else:
                if self.logger:
                    self.logger.error("Update installation failed")
                return False
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error performing update: {e}")
            return False
    
    def check_and_update(self) -> bool:
        """
        Check for updates and perform update if available.
        
        Returns:
            True if update was performed, False otherwise
        """
        try:
            # Check for updates
            if not self.check_for_updates():
                return False
            
            # Perform update if available
            if self.update_available:
                return self.perform_update()
            
            return False
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in check_and_update: {e}")
            return False
    
    def start_background_checker(self):
        """
        Start background thread to check for updates periodically.
        """
        if self.background_thread and self.background_thread.is_alive():
            if self.logger:
                self.logger.warning("Background checker is already running")
            return
        
        def background_check():
            if self.logger:
                self.logger.info("Background update checker started")
            
            # Wait a bit before first check to let the app fully start
            time.sleep(30)
            
            while not self.stop_background:
                try:
                    if self.logger:
                        self.logger.info("Background update check starting")
                    
                    # Check for updates and perform update if available
                    update_performed = self.check_and_update()
                    
                    if update_performed:
                        if self.logger:
                            self.logger.info("Update was performed, stopping background checker")
                        break  # Exit the loop after successful update
                    
                    # Wait for next check with shorter intervals for better responsiveness
                    check_interval = min(self.CHECK_INTERVAL, 4 * 60 * 60)  # Max 4 hours
                    sleep_time = 0
                    while sleep_time < check_interval and not self.stop_background:
                        time.sleep(60)  # Check every minute if we should stop
                        sleep_time += 60
                    
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error in background update check: {e}")
                    time.sleep(300)  # Wait 5 minutes before retrying on error
            
            if self.logger:
                self.logger.info("Background update checker stopped")
        
        # Start background thread
        self.stop_background = False
        self.background_thread = threading.Thread(target=background_check, daemon=True)
        self.background_thread.start()
        
        if self.logger:
            self.logger.info("Background update checker started successfully")
    
    def stop_background_checker(self):
        """
        Stop the background update checker.
        """
        if self.logger:
            self.logger.info("Stopping background update checker")
        self.stop_background = True
        
        if self.background_thread and self.background_thread.is_alive():
            self.background_thread.join(timeout=10)  # Wait up to 10 seconds
            if self.background_thread.is_alive():
                if self.logger:
                    self.logger.warning("Background thread did not stop gracefully")
    
    def get_update_info(self) -> Dict[str, Any]:
        """
        Get information about available updates.
        
        Returns:
            Dictionary with update information
        """
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "update_available": self.update_available,
            "is_updating": self.is_updating,
            "internet_available": self.internet_available,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "background_running": self.background_thread and self.background_thread.is_alive(),
            "github_repo": f"{self.GITHUB_REPO_OWNER}/{self.GITHUB_REPO_NAME}",
            "check_interval_hours": self.CHECK_INTERVAL / 3600
        }


def setup_auto_updater(current_version: str = "1.0.0", 
                      github_owner: str = "isaackcz",
                      github_repo: str = "Excel-Consolidator") -> AutoUpdater:
    """
    Setup auto-updater for the application.
    
    Args:
        current_version: Current application version
        github_owner: GitHub repository owner
        github_repo: GitHub repository name
        
    Returns:
        AutoUpdater instance
    """
    try:
        updater = AutoUpdater(current_version)
        updater.GITHUB_REPO_OWNER = github_owner
        updater.GITHUB_REPO_NAME = github_repo
        
        # Start background checker
        updater.start_background_checker()
        
        return updater
        
    except Exception as e:
        print(f"Warning: Auto-updater setup failed: {e}")
        return None


# Example usage and testing
if __name__ == "__main__":
    # Test the auto-updater system
    print("Testing Auto-Update System...")
    
    # Setup auto-updater (replace with actual values)
    updater = setup_auto_updater("1.0.0", "isaackcz", "Excel-Consolidator")
    
    if updater:
        print("Auto-updater setup successful!")
        
        # Check for updates
        if updater.check_for_updates():
            print(f"Update available: {updater.latest_version}")
            
            # Get update info
            info = updater.get_update_info()
            print(f"Update info: {info}")
        else:
            print("Application is up to date")
    else:
        print("Auto-updater setup failed!")
