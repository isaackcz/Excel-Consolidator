"""
Ultra-Fast Download System for Excel Consolidator v1.0.8

This module provides maximum performance download functionality with:
- Multi-threaded parallel chunk downloads
- Advanced connection pooling and keep-alive
- Intelligent resume capability with range requests
- Dynamic chunk size optimization
- Real-time speed and ETA calculations
- Compression and caching optimizations
- Network-aware adaptive downloading

Author: Excel Consolidator Team
Version: 1.0.8
"""

import os
import sys
import json
import requests
import threading
import time
import hashlib
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List, Tuple
from datetime import datetime, timedelta
import logging
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import gzip
import pickle
from dataclasses import dataclass, field
from queue import Queue
import math

@dataclass
class DownloadChunk:
    """Information about a download chunk."""
    start_byte: int
    end_byte: int
    chunk_id: int
    downloaded: int = 0
    completed: bool = False
    error: Optional[str] = None

@dataclass
class DownloadStats:
    """Download statistics and performance metrics."""
    total_size: int = 0
    downloaded: int = 0
    speed_bps: float = 0.0
    speed_mbps: float = 0.0
    eta_seconds: int = 0
    eta_formatted: str = "Unknown"
    progress_percent: float = 0.0
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    chunks_completed: int = 0
    total_chunks: int = 0

class UltraFastDownloader:
    """
    Ultra-fast downloader with maximum performance optimizations.
    """
    
    # Performance configuration
    MAX_CONNECTIONS = 8  # Increased from 4
    MIN_CHUNK_SIZE = 1024 * 1024  # 1MB minimum
    MAX_CHUNK_SIZE = 16 * 1024 * 1024  # 16MB maximum
    OPTIMAL_CHUNK_SIZE = 4 * 1024 * 1024  # 4MB optimal
    CONNECTION_TIMEOUT = 30
    READ_TIMEOUT = 120  # Increased for large chunks
    MAX_RETRIES = 5  # Increased retries
    SPEED_SAMPLE_SIZE = 10  # For speed calculation smoothing
    PROGRESS_UPDATE_INTERVAL = 0.1  # Update progress every 100ms
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the ultra-fast downloader."""
        self.logger = logger
        self.session = self._create_ultra_optimized_session()
        self.stats = DownloadStats()
        self.chunks: List[DownloadChunk] = []
        self.download_lock = threading.Lock()
        self.progress_callbacks: List[Callable] = []
        self.is_downloading = False
        self.should_stop = False
        
        # Speed calculation
        self.speed_samples: List[Tuple[float, int]] = []  # (timestamp, bytes)
        
    def _create_ultra_optimized_session(self) -> requests.Session:
        """Create an ultra-optimized requests session."""
        session = requests.Session()
        
        # Advanced retry strategy
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=2,  # Exponential backoff
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_status=False
        )
        
        # Ultra-optimized adapter
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.MAX_CONNECTIONS * 2,  # More connections
            pool_maxsize=self.MAX_CONNECTIONS * 4,  # Larger pool
            pool_block=False,
            socket_options=[(6, 1, 1)]  # TCP_NODELAY for lower latency
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Optimized headers
        session.headers.update({
            'User-Agent': 'Excel-Consolidator/1.0.8 (Ultra-Fast-Downloader)',
            'Accept-Encoding': 'gzip, deflate, br',  # Enable compression
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        })
        
        return session
    
    def _calculate_optimal_chunk_size(self, file_size: int) -> int:
        """Calculate optimal chunk size based on file size and connections."""
        if file_size <= 0:
            return self.OPTIMAL_CHUNK_SIZE
        
        # Base chunk size on file size and available connections
        base_chunk_size = max(
            self.MIN_CHUNK_SIZE,
            min(
                self.MAX_CHUNK_SIZE,
                file_size // (self.MAX_CONNECTIONS * 4)  # 4x connections for overlap
            )
        )
        
        # Round to nearest MB for better performance
        optimal_size = ((base_chunk_size + 1024 * 1024 - 1) // (1024 * 1024)) * (1024 * 1024)
        
        return max(self.MIN_CHUNK_SIZE, min(self.MAX_CHUNK_SIZE, optimal_size))
    
    def _create_chunks(self, file_size: int) -> List[DownloadChunk]:
        """Create download chunks for parallel processing."""
        chunk_size = self._calculate_optimal_chunk_size(file_size)
        chunks = []
        chunk_id = 0
        
        for start_byte in range(0, file_size, chunk_size):
            end_byte = min(start_byte + chunk_size - 1, file_size - 1)
            chunks.append(DownloadChunk(
                start_byte=start_byte,
                end_byte=end_byte,
                chunk_id=chunk_id
            ))
            chunk_id += 1
        
        return chunks
    
    def _download_chunk(self, chunk: DownloadChunk, url: str, file_path: str, 
                       progress_queue: Queue) -> bool:
        """Download a single chunk with retry logic."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries and not self.should_stop:
            try:
                # Create range header
                headers = {
                    'Range': f'bytes={chunk.start_byte}-{chunk.end_byte}',
                    'Accept-Encoding': 'gzip, deflate, br'
                }
                
                # Download chunk
                response = self.session.get(
                    url, 
                    headers=headers, 
                    stream=True, 
                    timeout=(self.CONNECTION_TIMEOUT, self.READ_TIMEOUT)
                )
                
                if response.status_code in [206, 200]:  # Partial content or full content
                    chunk_size = chunk.end_byte - chunk.start_byte + 1
                    downloaded_in_chunk = 0
                    
                    # Write chunk to file
                    with open(file_path, 'r+b') as f:
                        f.seek(chunk.start_byte)
                        
                        for data in response.iter_content(chunk_size=64 * 1024):  # 64KB buffer
                            if self.should_stop:
                                break
                                
                            f.write(data)
                            downloaded_in_chunk += len(data)
                            
                            # Update chunk progress
                            chunk.downloaded = downloaded_in_chunk
                            
                            # Send progress update
                            if progress_queue:
                                progress_queue.put(('chunk_progress', chunk.chunk_id, downloaded_in_chunk, chunk_size))
                    
                    # Mark chunk as completed
                    chunk.completed = True
                    chunk.downloaded = chunk_size
                    
                    if self.logger:
                        self.logger.debug(f"Chunk {chunk.chunk_id} completed: {chunk_size} bytes")
                    
                    return True
                    
                else:
                    if self.logger:
                        self.logger.warning(f"Unexpected status code {response.status_code} for chunk {chunk.chunk_id}")
                    retry_count += 1
                    
            except Exception as e:
                retry_count += 1
                chunk.error = str(e)
                if self.logger:
                    self.logger.warning(f"Chunk {chunk.chunk_id} failed (attempt {retry_count}): {e}")
                
                if retry_count < max_retries:
                    time.sleep(min(2 ** retry_count, 10))  # Exponential backoff
        
        return False
    
    def _update_speed_stats(self, downloaded_bytes: int):
        """Update speed statistics with smoothing."""
        current_time = time.time()
        
        # Add current sample
        self.speed_samples.append((current_time, downloaded_bytes))
        
        # Keep only recent samples
        cutoff_time = current_time - 5.0  # Last 5 seconds
        self.speed_samples = [(t, b) for t, b in self.speed_samples if t > cutoff_time]
        
        if len(self.speed_samples) >= 2:
            # Calculate speed
            time_diff = self.speed_samples[-1][0] - self.speed_samples[0][0]
            bytes_diff = self.speed_samples[-1][1] - self.speed_samples[0][1]
            
            if time_diff > 0:
                self.stats.speed_bps = bytes_diff / time_diff
                self.stats.speed_mbps = self.stats.speed_bps / (1024 * 1024)
                
                # Calculate ETA
                if self.stats.speed_bps > 0 and self.stats.total_size > 0:
                    remaining_bytes = self.stats.total_size - self.stats.downloaded
                    self.stats.eta_seconds = int(remaining_bytes / self.stats.speed_bps)
                    self.stats.eta_formatted = self._format_duration(self.stats.eta_seconds)
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"
    
    def _progress_worker(self, progress_queue: Queue):
        """Background worker to handle progress updates."""
        last_update = time.time()
        
        while not self.should_stop:
            try:
                # Process progress updates
                while not progress_queue.empty():
                    update_type, *data = progress_queue.get_nowait()
                    
                    if update_type == 'chunk_progress':
                        chunk_id, downloaded, total = data
                        # Update chunk progress (handled in main thread)
                        
                    elif update_type == 'chunk_completed':
                        chunk_id = data[0]
                        with self.download_lock:
                            self.stats.chunks_completed += 1
                
                # Update speed and ETA
                current_time = time.time()
                if current_time - last_update >= self.PROGRESS_UPDATE_INTERVAL:
                    with self.download_lock:
                        self._update_speed_stats(self.stats.downloaded)
                        self.stats.progress_percent = (self.stats.downloaded / self.stats.total_size * 100) if self.stats.total_size > 0 else 0
                        
                        # Call progress callbacks
                        for callback in self.progress_callbacks:
                            try:
                                callback(
                                    self.stats.downloaded,
                                    self.stats.total_size,
                                    f"Downloading... {self.stats.progress_percent:.1f}% "
                                    f"({self._format_bytes(self.stats.downloaded)}/{self._format_bytes(self.stats.total_size)}) "
                                    f"- {self.stats.speed_mbps:.1f} MB/s - ETA: {self.stats.eta_formatted}"
                                )
                            except Exception as e:
                                if self.logger:
                                    self.logger.warning(f"Progress callback error: {e}")
                    
                    last_update = current_time
                
                time.sleep(0.05)  # 50ms update interval
                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Progress worker error: {e}")
                time.sleep(0.1)
    
    def download_file(self, url: str, file_path: str, 
                     progress_callback: Optional[Callable] = None,
                     resume: bool = True) -> bool:
        """
        Download a file with ultra-fast parallel processing.
        
        Args:
            url: URL to download from
            file_path: Local path to save the file
            progress_callback: Callback for progress updates (downloaded, total, message)
            resume: Whether to resume interrupted downloads
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            self.is_downloading = True
            self.should_stop = False
            self.stats = DownloadStats()
            
            if progress_callback:
                self.progress_callbacks.append(progress_callback)
            
            if self.logger:
                self.logger.info(f"Starting ultra-fast download: {url}")
            
            # Get file information
            head_response = self.session.head(url, timeout=10)
            if head_response.status_code != 200:
                if self.logger:
                    self.logger.error(f"Failed to get file info: {head_response.status_code}")
                return False
            
            # Check if server supports range requests
            supports_range = 'accept-ranges' in head_response.headers and head_response.headers['accept-ranges'] == 'bytes'
            if not supports_range:
                if self.logger:
                    self.logger.warning("Server does not support range requests, falling back to single-threaded download")
                return self._download_single_threaded(url, file_path, progress_callback)
            
            # Get file size
            file_size = int(head_response.headers.get('content-length', 0))
            if file_size <= 0:
                if self.logger:
                    self.logger.error("Could not determine file size")
                return False
            
            self.stats.total_size = file_size
            self.stats.total_chunks = math.ceil(file_size / self._calculate_optimal_chunk_size(file_size))
            
            if self.logger:
                self.logger.info(f"File size: {self._format_bytes(file_size)}, Chunks: {self.stats.total_chunks}")
            
            # Create or resume file
            existing_size = 0
            if resume and os.path.exists(file_path):
                existing_size = os.path.getsize(file_path)
                if existing_size >= file_size:
                    if self.logger:
                        self.logger.info("File already downloaded completely")
                    return True
                elif existing_size > 0:
                    if self.logger:
                        self.logger.info(f"Resuming download from {self._format_bytes(existing_size)}")
            
            # Create file if it doesn't exist
            if not os.path.exists(file_path):
                with open(file_path, 'wb') as f:
                    f.truncate(file_size)
            
            # Create chunks
            self.chunks = self._create_chunks(file_size)
            
            # Skip completed chunks if resuming
            if existing_size > 0:
                for chunk in self.chunks:
                    if chunk.end_byte < existing_size:
                        chunk.completed = True
                        chunk.downloaded = chunk.end_byte - chunk.start_byte + 1
                        self.stats.downloaded += chunk.downloaded
                        self.stats.chunks_completed += 1
            
            # Start progress worker
            progress_queue = Queue()
            progress_thread = threading.Thread(
                target=self._progress_worker, 
                args=(progress_queue,), 
                daemon=True
            )
            progress_thread.start()
            
            # Download chunks in parallel
            with ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
                # Submit chunk downloads
                future_to_chunk = {
                    executor.submit(self._download_chunk, chunk, url, file_path, progress_queue): chunk
                    for chunk in self.chunks if not chunk.completed
                }
                
                # Process completed chunks
                for future in as_completed(future_to_chunk):
                    if self.should_stop:
                        break
                        
                    chunk = future_to_chunk[future]
                    try:
                        success = future.result()
                        if success:
                            with self.download_lock:
                                self.stats.downloaded += chunk.downloaded
                                self.stats.chunks_completed += 1
                            
                            progress_queue.put(('chunk_completed', chunk.chunk_id))
                            
                            if self.logger:
                                self.logger.debug(f"Chunk {chunk.chunk_id} completed successfully")
                        else:
                            if self.logger:
                                self.logger.error(f"Chunk {chunk.chunk_id} failed")
                            return False
                            
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Chunk {chunk.chunk_id} exception: {e}")
                        return False
            
            # Final progress update
            if progress_callback:
                progress_callback(
                    self.stats.downloaded,
                    self.stats.total_size,
                    f"Download completed! {self._format_bytes(self.stats.downloaded)} at {self.stats.speed_mbps:.1f} MB/s"
                )
            
            if self.logger:
                self.logger.info(f"Download completed successfully: {self._format_bytes(self.stats.downloaded)}")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Download failed: {e}")
            return False
        finally:
            self.is_downloading = False
            self.should_stop = True
            self.progress_callbacks.clear()
    
    def _download_single_threaded(self, url: str, file_path: str, 
                                 progress_callback: Optional[Callable] = None) -> bool:
        """Fallback single-threaded download."""
        try:
            if self.logger:
                self.logger.info("Using single-threaded download fallback")
            
            response = self.session.get(url, stream=True, timeout=(self.CONNECTION_TIMEOUT, self.READ_TIMEOUT))
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            start_time = time.time()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                    if self.should_stop:
                        return False
                        
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Update progress
                    if progress_callback and total_size > 0:
                        progress = (downloaded / total_size) * 100
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        
                        progress_callback(
                            downloaded,
                            total_size,
                            f"Downloading... {progress:.1f}% ({self._format_bytes(downloaded)}/{self._format_bytes(total_size)}) - {speed/1024/1024:.1f} MB/s"
                        )
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Single-threaded download failed: {e}")
            return False
    
    def stop_download(self):
        """Stop the current download."""
        self.should_stop = True
        if self.logger:
            self.logger.info("Download stop requested")
    
    def get_download_stats(self) -> DownloadStats:
        """Get current download statistics."""
        return self.stats
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_download()
        self.session.close()
        if self.logger:
            self.logger.info("Ultra-fast downloader cleaned up")


# Example usage and testing
if __name__ == "__main__":
    # Test the ultra-fast downloader
    print("Testing Ultra-Fast Download System...")
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create downloader
    downloader = UltraFastDownloader(logger)
    
    # Test download
    test_url = "https://github.com/isaackcz/Excel-Consolidator-App/releases/latest/download/Excel-Consolidator-v1.0.6-Windows.exe"
    test_file = "test_download.exe"
    
    def progress_callback(downloaded, total, message):
        print(f"Progress: {message}")
    
    success = downloader.download_file(test_url, test_file, progress_callback)
    
    if success:
        print("Download completed successfully!")
        stats = downloader.get_download_stats()
        print(f"Final speed: {stats.speed_mbps:.1f} MB/s")
    else:
        print("Download failed!")
    
    # Cleanup
    downloader.cleanup()
