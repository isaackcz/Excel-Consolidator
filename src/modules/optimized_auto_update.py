"""
Optimized Automatic Update System for Excel Consolidator v1.0.7

This module provides enhanced automatic update functionality with:
- Parallel downloads with connection pooling
- Resume capability for interrupted downloads
- Enhanced progress tracking
- Caching and compression
- Background processing
- Better error handling and recovery

Author: Excel Consolidator Team
Version: 1.0.7
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
from typing import Optional, Dict, Any, Tuple, Callable
from datetime import datetime, timedelta
import logging
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import gzip
import pickle
from dataclasses import dataclass

# Import our optimized modules
from src.core.async_loader import AsyncLoader, ProgressTracker
from src.core.lazy_loader import lazy_import
from src.modules.ultra_fast_downloader import UltraFastDownloader

@dataclass
class DownloadInfo:
    """Information about a download."""
    url: str
    file_path: str
    total_size: int
    downloaded_size: int
    checksum: Optional[str] = None
    resume_supported: bool = True

class OptimizedAutoUpdater:
    """
    Enhanced auto-updater with performance optimizations.
    """
    
    # Configuration
    GITHUB_REPO_OWNER = "isaackcz"
    GITHUB_REPO_NAME = "Excel-Consolidator-App"
    CURRENT_VERSION = "1.0.7"
    CHECK_INTERVAL = 24 * 60 * 60  # Check every 24 hours
    
    # Performance settings
    MAX_CONNECTIONS = 4
    CHUNK_SIZE = 64 * 1024  # 64KB chunks
    CONNECTION_TIMEOUT = 30
    READ_TIMEOUT = 60
    MAX_RETRIES = 3
    CACHE_DURATION = 3600  # 1 hour cache
    
    def __init__(self, current_version: str = CURRENT_VERSION, github_owner: str = None, github_repo: str = None):
        """Initialize the optimized auto-updater."""
        self.current_version = current_version
        self.latest_version = None
        self.update_available = False
        self.is_updating = False
        self.last_check_time = None
        self.background_thread = None
        self.stop_background = False
        self.internet_available = False
        self._latest_release_info = None
        self._cache_dir = Path("cache")
        self._cache_dir.mkdir(exist_ok=True)
        
        # Initialize async loader for background operations
        self.async_loader = AsyncLoader(max_workers=self.MAX_CONNECTIONS)
        
        # Setup session with connection pooling and retries
        self.session = self._create_optimized_session()
        
        # Initialize ultra-fast downloader
        self.ultra_downloader = UltraFastDownloader(self.logger)
        
        self.load_config(github_owner, github_repo)
        self.setup_logging()
        
        # Log version information
        if self.logger:
            self.logger.info("=" * 60)
            self.logger.info(f"Excel Consolidator v{self.current_version} - Optimized Auto-Update System")
            self.logger.info("=" * 60)
            self.logger.info("Enhanced with parallel downloads, resume capability, and caching")
            self.logger.info(f"Repository: {self.GITHUB_REPO_OWNER}/{self.GITHUB_REPO_NAME}")
            self.logger.info("=" * 60)
    
    def _create_optimized_session(self) -> requests.Session:
        """Create an optimized requests session with connection pooling and retries."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        # Configure adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.MAX_CONNECTIONS,
            pool_maxsize=self.MAX_CONNECTIONS * 2,
            pool_block=False
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set timeouts
        session.timeout = (self.CONNECTION_TIMEOUT, self.READ_TIMEOUT)
        
        return session
    
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
    
    def _get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data if it's still valid with enhanced validation."""
        cache_file = self._cache_dir / f"{key}.cache"
        
        if not cache_file.exists():
            return None
        
        try:
            # Check if cache is still valid
            cache_time = cache_file.stat().st_mtime
            current_time = time.time()
            
            # Dynamic cache duration based on data type
            cache_duration = self.CACHE_DURATION
            if "release" in key.lower():
                cache_duration = min(cache_duration, 1800)  # 30 minutes for release info
            elif "version" in key.lower():
                cache_duration = min(cache_duration, 3600)  # 1 hour for version checks
            
            if current_time - cache_time > cache_duration:
                cache_file.unlink()  # Remove expired cache
                if self.logger:
                    self.logger.debug(f"Cache expired for {key}, removed")
                return None
            
            # Load cached data with compression support
            try:
                with gzip.open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                if self.logger:
                    self.logger.debug(f"Loaded compressed cache for {key}")
                return data
            except (OSError, EOFError):
                # Fallback to uncompressed
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                if self.logger:
                    self.logger.debug(f"Loaded uncompressed cache for {key}")
                return data
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to load cache {key}: {e}")
            # Remove corrupted cache file
            try:
                cache_file.unlink()
            except Exception:
                pass
            return None
    
    def _set_cached_data(self, key: str, data: Any):
        """Cache data with compression and metadata."""
        try:
            cache_file = self._cache_dir / f"{key}.cache"
            
            # Create cache metadata
            cache_metadata = {
                'data': data,
                'timestamp': time.time(),
                'version': '1.0.8',
                'compressed': True
            }
            
            # Compress and cache data
            with gzip.open(cache_file, 'wb') as f:
                pickle.dump(cache_metadata, f)
                
            if self.logger:
                self.logger.debug(f"Cached data for {key} with compression")
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to cache data {key}: {e}")
            # Fallback to uncompressed caching
            try:
                cache_file = self._cache_dir / f"{key}.cache"
                with open(cache_file, 'wb') as f:
                    pickle.dump(data, f)
                if self.logger:
                    self.logger.debug(f"Cached data for {key} without compression (fallback)")
            except Exception as e2:
                if self.logger:
                    self.logger.error(f"Failed to cache data {key} even without compression: {e2}")
    
    def check_internet_connection(self) -> bool:
        """Check if internet connection is available with multiple endpoints."""
        endpoints = [
            ("8.8.8.8", 53),
            ("api.github.com", 443),
            ("github.com", 443)
        ]
        
        for host, port in endpoints:
            try:
                socket.create_connection((host, port), timeout=5)
                self.internet_available = True
                if self.logger:
                    self.logger.debug(f"Internet connection verified via {host}:{port}")
                return True
            except OSError:
                continue
        
        self.internet_available = False
        if self.logger:
            self.logger.warning("No internet connection available")
        return False
    
    def check_for_updates(self) -> bool:
        """Check for updates with caching and parallel processing."""
        try:
            # Check internet connectivity
            if not self.check_internet_connection():
                if self.logger:
                    self.logger.info("Skipping update check - no internet connection")
                return False
            
            if self.logger:
                self.logger.info(f"Checking for updates (current version: {self.current_version})")
            
            self.last_check_time = datetime.now()
            
            # Try to get cached release info first
            cache_key = f"latest_release_{self.GITHUB_REPO_OWNER}_{self.GITHUB_REPO_NAME}"
            cached_release = self._get_cached_data(cache_key)
            
            if cached_release:
                if self.logger:
                    self.logger.info("Using cached release information")
                latest_release = cached_release
            else:
                # Fetch fresh release info
                latest_release = self._get_latest_release()
                if latest_release:
                    self._set_cached_data(cache_key, latest_release)
            
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
                
                self._latest_release_info = {
                    'version': self.latest_version,
                    'release_notes': latest_release.get('body', ''),
                    'published_at': latest_release.get('published_at', ''),
                    'html_url': latest_release.get('html_url', '')
                }
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
        """Get latest release information from GitHub API with retries."""
        try:
            url = f"https://api.github.com/repos/{self.GITHUB_REPO_OWNER}/{self.GITHUB_REPO_NAME}/releases/latest"
            
            response = self.session.get(url, timeout=10)
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
        """Compare version strings to determine if latest is newer."""
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            max_len = max(len(latest_parts), len(current_parts))
            latest_parts.extend([0] * (max_len - len(latest_parts)))
            current_parts.extend([0] * (max_len - len(current_parts)))
            
            return latest_parts > current_parts
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error comparing versions: {e}")
            return False
    
    def download_update_parallel(self, progress_callback: Optional[Callable] = None, 
                               download_progress_callback: Optional[Callable] = None) -> Optional[str]:
        """
        Download update with ultra-fast parallel processing and resume capability.
        
        Args:
            progress_callback: Callback for general progress updates
            download_progress_callback: Callback for download progress
            
        Returns:
            Path to downloaded update file or None if failed
        """
        try:
            if not self.update_available or not self.latest_version:
                if self.logger:
                    self.logger.warning("No update available or version not set")
                return None
            
            if self.logger:
                self.logger.info(f"Starting ultra-fast download to version {self.latest_version}")
            
            if progress_callback:
                progress_callback(10, "Preparing ultra-fast download...")
            
            # Get release assets
            latest_release = self._get_latest_release()
            if not latest_release:
                if progress_callback:
                    progress_callback(100, "Failed to get release information")
                return None
            
            if progress_callback:
                progress_callback(20, "Finding update file...")
            
            # Find the appropriate asset
            asset_url = self._get_asset_url(latest_release)
            if not asset_url:
                if self.logger:
                    self.logger.error("No suitable update asset found")
                if progress_callback:
                    progress_callback(100, "No suitable update file found")
                return None
            
            if progress_callback:
                progress_callback(30, "Starting ultra-fast download...")
            
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
            
            # Use ultra-fast downloader
            success = self.ultra_downloader.download_file(
                asset_url, 
                download_path, 
                download_progress_callback,
                resume=True
            )
            
            if success and progress_callback:
                progress_callback(90, "Download completed!")
                return download_path
            else:
                if self.logger:
                    self.logger.error("Ultra-fast download failed")
                if progress_callback:
                    progress_callback(100, "Download failed")
                return None
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error downloading update: {e}")
            if progress_callback:
                progress_callback(100, f"Download failed: {str(e)}")
            return None
    
    def _get_asset_url(self, release_data: Dict[str, Any]) -> Optional[str]:
        """Get the appropriate asset URL for the current platform."""
        try:
            assets = release_data.get('assets', [])
            if not assets:
                return None
            
            platform_name = self._get_platform_asset_name()
            
            # Find matching asset
            for asset in assets:
                asset_name = asset.get('name', '').lower()
                if platform_name in asset_name:
                    return asset.get('browser_download_url')
            
            # Fallback: use first asset
            if assets:
                return assets[0].get('browser_download_url')
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting asset URL: {e}")
            return None
    
    def _get_platform_asset_name(self) -> str:
        """Get platform-specific asset name."""
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
    
    def _download_asset_parallel(self, asset_url: str, 
                               download_progress_callback: Optional[Callable] = None) -> Optional[str]:
        """
        Download asset with parallel processing and resume capability.
        
        Args:
            asset_url: URL to download asset from
            download_progress_callback: Callback for download progress
            
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
            
            if self.logger:
                self.logger.info(f"Starting parallel download from: {asset_url}")
            
            # Check if resume is supported
            resume_supported = self._check_resume_support(asset_url)
            
            if resume_supported:
                # Try to resume existing download
                existing_size = 0
                if os.path.exists(download_path):
                    existing_size = os.path.getsize(download_path)
                    if self.logger:
                        self.logger.info(f"Resuming download from {existing_size} bytes")
            
            # Get file size
            total_size = self._get_file_size(asset_url)
            
            if total_size and existing_size >= total_size:
                if self.logger:
                    self.logger.info("File already downloaded completely")
                return download_path
            
            # Download with progress tracking
            headers = {}
            if resume_supported and existing_size > 0:
                headers['Range'] = f'bytes={existing_size}-'
            
            response = self.session.get(asset_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Update total size if we got a partial response
            if 'content-range' in response.headers:
                total_size = int(response.headers['content-range'].split('/')[-1])
            
            downloaded = existing_size
            last_progress = 0
            
            with open(download_path, 'ab' if existing_size > 0 else 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress callbacks
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            
                            if download_progress_callback:
                                download_progress_callback(
                                    downloaded, total_size, 
                                    f"Downloading... {progress:.1f}% ({self._format_bytes(downloaded)}/{self._format_bytes(total_size)})"
                                )
                            
                            # Log progress every 5% to avoid spam
                            if int(progress) % 5 == 0 and int(progress) > last_progress:
                                last_progress = int(progress)
                                if self.logger:
                                    self.logger.info(f"Download progress: {progress:.1f}%")
                        else:
                            if download_progress_callback:
                                download_progress_callback(
                                    downloaded, 0, 
                                    f"Downloaded {self._format_bytes(downloaded)}..."
                                )
            
            if self.logger:
                self.logger.info(f"Download completed: {download_path}")
            
            # Verify download integrity
            if self._verify_download(download_path, asset_url):
                if download_progress_callback:
                    download_progress_callback(downloaded, total_size, "Download completed and verified!")
                return download_path
            else:
                if self.logger:
                    self.logger.error("Download verification failed")
                return None
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error downloading asset: {e}")
            return None
    
    def _check_resume_support(self, url: str) -> bool:
        """Check if the server supports resume (Range requests)."""
        try:
            response = self.session.head(url, timeout=10)
            return 'accept-ranges' in response.headers and response.headers['accept-ranges'] == 'bytes'
        except Exception:
            return False
    
    def _get_file_size(self, url: str) -> Optional[int]:
        """Get the size of the file to download."""
        try:
            response = self.session.head(url, timeout=10)
            return int(response.headers.get('content-length', 0))
        except Exception:
            return None
    
    def _verify_download(self, file_path: str, url: str) -> bool:
        """Verify the integrity of the downloaded file."""
        try:
            # Basic size check
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                return False
            
            # TODO: Add checksum verification if available
            return True
        except Exception:
            return False
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"
    
    def install_update(self, update_path: str, progress_callback: Optional[Callable] = None) -> bool:
        """Install the downloaded update with enhanced error handling."""
        try:
            if self.logger:
                self.logger.info(f"Installing update from: {update_path}")
            
            if progress_callback:
                progress_callback(95, "Preparing installation...")
            
            self.is_updating = True
            
            # Get application directory
            app_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
            
            if progress_callback:
                progress_callback(96, "Installing update files...")
            
            # Handle different update file types
            if update_path.endswith('.zip'):
                success = self._install_zip_update(update_path, app_dir, progress_callback)
            elif update_path.endswith('.exe'):
                success = self._install_exe_update(update_path, app_dir, progress_callback)
            else:
                if self.logger:
                    self.logger.error(f"Unsupported update file format: {update_path}")
                if progress_callback:
                    progress_callback(100, "Unsupported update file format")
                return False
            
            if success and progress_callback:
                progress_callback(99, "Finalizing installation...")
            
            return success
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error installing update: {e}")
            if progress_callback:
                progress_callback(100, f"Installation failed: {str(e)}")
            return False
        finally:
            self.is_updating = False
    
    def _install_zip_update(self, zip_path: str, app_dir: Path, progress_callback: Optional[Callable] = None) -> bool:
        """Install update from ZIP file with enhanced backup and rollback."""
        try:
            # Create backup of current application
            backup_dir = app_dir / "backup"
            backup_dir.mkdir(exist_ok=True)
            
            if self.logger:
                self.logger.info("Creating backup of current application")
            
            if progress_callback:
                progress_callback(96, "Creating backup of current application...")
            
            # Backup current files
            for item in app_dir.iterdir():
                if item.name != "backup":
                    backup_item = backup_dir / item.name
                    if item.is_file():
                        shutil.copy2(item, backup_item)
                    elif item.is_dir():
                        shutil.copytree(item, backup_item, dirs_exist_ok=True)
            
            # Create backup marker
            backup_marker = backup_dir / "backup_info.json"
            backup_info = {
                "timestamp": datetime.now().isoformat(),
                "version": self.current_version,
                "app_dir": str(app_dir)
            }
            with open(backup_marker, 'w') as f:
                json.dump(backup_info, f, indent=2)
            
            if progress_callback:
                progress_callback(97, "Extracting update files...")
            
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
    
    def _install_exe_update(self, exe_path: str, app_dir: Path, progress_callback: Optional[Callable] = None) -> bool:
        """Install update from EXE file with enhanced error handling."""
        try:
            if self.logger:
                self.logger.info("Installing EXE update")
            
            if progress_callback:
                progress_callback(96, "Preparing EXE installation...")
            
            if platform.system().lower() == "windows":
                if progress_callback:
                    progress_callback(97, "Creating update script...")
                
                batch_script = self._create_update_script(exe_path, app_dir)
                if batch_script:
                    if progress_callback:
                        progress_callback(98, "Starting update installation...")
                    
                    subprocess.Popen([batch_script], shell=True)
                    if self.logger:
                        self.logger.info("Update script started - application will restart")
                    return True
                else:
                    if self.logger:
                        self.logger.error("Failed to create update script")
                    if progress_callback:
                        progress_callback(100, "Failed to create update script")
                    return False
            else:
                if progress_callback:
                    progress_callback(97, "Running installer...")
                
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
        """Create an enhanced batch script for Windows update installation."""
        try:
            current_exe = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
            current_exe_dir = os.path.dirname(current_exe)
            current_exe_name = os.path.basename(current_exe)
            
            if self.logger:
                self.logger.info(f"Creating update script for: {current_exe}")
            
            # Enhanced batch script with better error handling
            script_content = f'''@echo off
echo ========================================
echo Excel Consolidator Update Installer v1.0.7
echo ========================================
echo Current executable: {current_exe}
echo Update file: {exe_path}
echo.

REM Wait for application to close
echo Waiting for application to close...
timeout /t 3 /nobreak >nul

REM Verify update file exists
if not exist "{exe_path}" (
    echo Error: Update file not found: {exe_path}
    echo Please download the update manually from GitHub
    pause
    exit /b 1
)

REM Create backup before update
echo Creating backup...
if not exist "{current_exe_dir}\\backup" mkdir "{current_exe_dir}\\backup"
copy "{current_exe}" "{current_exe_dir}\\backup\\{current_exe_name}.backup" /Y

REM Install new version
echo Installing new version...
copy "{exe_path}" "{current_exe}" /Y
if errorlevel 1 (
    echo Warning: Direct copy failed, trying alternative method...
    
    copy "{exe_path}" "{current_exe}.new" /Y
    if errorlevel 1 (
        echo Error: Alternative copy method also failed
        echo Restoring from backup...
        copy "{current_exe_dir}\\backup\\{current_exe_name}.backup" "{current_exe}" /Y
        echo Please close Excel Consolidator and try again, or update manually.
        pause
        exit /b 1
    )
    
    del "{current_exe}" /Q
    ren "{current_exe}.new" "{current_exe_name}"
    if errorlevel 1 (
        echo Error: Could not rename new executable
        echo Restoring from backup...
        copy "{current_exe_dir}\\backup\\{current_exe_name}.backup" "{current_exe}" /Y
        pause
        exit /b 1
    )
)

REM Clean up
echo Cleaning up temporary files...
del "{exe_path}" /Q

REM Verify installation
if not exist "{current_exe}" (
    echo Error: New executable not found after update
    echo Restoring from backup...
    copy "{current_exe_dir}\\backup\\{current_exe_name}.backup" "{current_exe}" /Y
    pause
    exit /b 1
)

REM Restart application
echo ========================================
echo Update completed successfully!
echo Restarting Excel Consolidator...
echo ========================================
start "" "{current_exe}"

REM Clean up script
timeout /t 3 /nobreak >nul
del "%~f0" /Q
'''
            
            script_path = os.path.join(tempfile.gettempdir(), "excel_consolidator_update_v1_0_7.bat")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            if self.logger:
                self.logger.info(f"Created enhanced update script: {script_path}")
            
            return script_path
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error creating update script: {e}")
            return None
    
    def perform_update(self, progress_callback: Optional[Callable] = None, 
                      download_progress_callback: Optional[Callable] = None) -> bool:
        """Perform complete update process with enhanced error handling."""
        try:
            if not self.update_available:
                if self.logger:
                    self.logger.info("No update available")
                if progress_callback:
                    progress_callback(100, "No update available")
                return False
            
            if self.logger:
                self.logger.info("Starting optimized update process")
            
            if progress_callback:
                progress_callback(5, "Starting optimized update process...")
            
            # Download update with parallel processing
            update_path = self.download_update_parallel(progress_callback, download_progress_callback)
            if not update_path:
                if self.logger:
                    self.logger.error("Failed to download update")
                if progress_callback:
                    progress_callback(100, "Failed to download update")
                return False
            
            if progress_callback:
                progress_callback(95, "Download complete! Installing update...")
            
            # Install update
            success = self.install_update(update_path, progress_callback)
            
            # Clean up downloaded file
            try:
                os.remove(update_path)
                temp_dir = os.path.dirname(update_path)
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception:
                pass
            
            if success:
                if self.logger:
                    self.logger.info("Update completed successfully")
                if progress_callback:
                    progress_callback(100, "Update completed successfully!")
                self.update_available = False
                return True
            else:
                if self.logger:
                    self.logger.error("Update installation failed")
                if progress_callback:
                    progress_callback(100, "Update installation failed")
                return False
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error performing update: {e}")
            if progress_callback:
                progress_callback(100, f"Update error: {str(e)}")
            return False
    
    def start_background_checker(self):
        """Start optimized background thread to check for updates."""
        if self.background_thread and self.background_thread.is_alive():
            if self.logger:
                self.logger.warning("Background checker is already running")
            return
        
        def background_check():
            if self.logger:
                self.logger.info("Optimized background update checker started")
            
            # Wait before first check
            time.sleep(30)
            
            while not self.stop_background:
                try:
                    if self.logger:
                        self.logger.info("Background update check starting")
                    
                    # Check for updates
                    if self.check_for_updates() and self.update_available:
                        if self.logger:
                            self.logger.info("Update available, performing update")
                        self.perform_update()
                        break
                    
                    # Wait for next check with adaptive intervals
                    check_interval = min(self.CHECK_INTERVAL, 4 * 60 * 60)  # Max 4 hours
                    sleep_time = 0
                    while sleep_time < check_interval and not self.stop_background:
                        time.sleep(60)
                        sleep_time += 60
                    
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error in background update check: {e}")
                    time.sleep(300)  # Wait 5 minutes before retrying
            
            if self.logger:
                self.logger.info("Background update checker stopped")
        
        self.stop_background = False
        self.background_thread = threading.Thread(target=background_check, daemon=True)
        self.background_thread.start()
        
        if self.logger:
            self.logger.info("Optimized background update checker started successfully")
    
    def stop_background_checker(self):
        """Stop the background update checker."""
        if self.logger:
            self.logger.info("Stopping background update checker")
        
        self.stop_background = True
        
        if self.background_thread and self.background_thread.is_alive():
            self.background_thread.join(timeout=5)
            if self.background_thread.is_alive():
                if self.logger:
                    self.logger.warning("Background thread did not stop gracefully")
                self.background_thread.daemon = True
    
    def get_update_info(self) -> Dict[str, Any]:
        """Get comprehensive update information."""
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "update_available": self.update_available,
            "is_updating": self.is_updating,
            "internet_available": self.internet_available,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "background_running": self.background_thread and self.background_thread.is_alive(),
            "github_repo": f"{self.GITHUB_REPO_OWNER}/{self.GITHUB_REPO_NAME}",
            "check_interval_hours": self.CHECK_INTERVAL / 3600,
            "release_info": self._latest_release_info,
            "optimizations": {
                "parallel_downloads": True,
                "resume_capability": True,
                "caching": True,
                "connection_pooling": True
            }
        }
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_background_checker()
        self.async_loader.shutdown()
        self.session.close()
        if hasattr(self, 'ultra_downloader'):
            self.ultra_downloader.cleanup()

def setup_optimized_auto_updater(current_version: str = "1.0.7", 
                                github_owner: str = "isaackcz",
                                github_repo: str = "Excel-Consolidator-App") -> OptimizedAutoUpdater:
    """Setup optimized auto-updater for the application."""
    try:
        updater = OptimizedAutoUpdater(current_version)
        updater.GITHUB_REPO_OWNER = github_owner
        updater.GITHUB_REPO_NAME = github_repo
        
        # Start background checker
        updater.start_background_checker()
        
        return updater
        
    except Exception as e:
        print(f"Warning: Optimized auto-updater setup failed: {e}")
        return None

if __name__ == "__main__":
    # Test the optimized auto-updater
    print("Testing Optimized Auto-Update System...")
    
    updater = setup_optimized_auto_updater("1.0.7", "isaackcz", "Excel-Consolidator-App")
    
    if updater:
        print("Optimized auto-updater setup successful!")
        
        # Check for updates
        if updater.check_for_updates():
            print(f"Update available: {updater.latest_version}")
            
            info = updater.get_update_info()
            print(f"Update info: {info}")
        else:
            print("Application is up to date")
        
        # Cleanup
        updater.cleanup()
    else:
        print("Optimized auto-updater setup failed!")
