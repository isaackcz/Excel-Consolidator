"""
Asynchronous Loading Module for Excel Consolidator

This module provides asynchronous loading capabilities to improve application
responsiveness during startup and heavy operations.
"""

import asyncio
import threading
import time
from typing import Any, Callable, Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, Future
from functools import wraps
import queue
import logging

class AsyncLoader:
    """
    Asynchronous loader that can execute operations in background threads
    while keeping the UI responsive.
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures: Dict[str, Future] = {}
        self.results: Dict[str, Any] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger(__name__)
    
    def submit_task(self, task_id: str, func: Callable, *args, **kwargs) -> Future:
        """
        Submit a task to be executed asynchronously.
        
        Args:
            task_id: Unique identifier for the task
            func: Function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Future object representing the task
        """
        future = self.executor.submit(func, *args, **kwargs)
        self.futures[task_id] = future
        
        # Add callback to handle completion
        future.add_done_callback(lambda f: self._task_completed(task_id, f))
        
        return future
    
    def _task_completed(self, task_id: str, future: Future):
        """Handle task completion."""
        try:
            result = future.result()
            self.results[task_id] = result
            
            # Execute callbacks
            if task_id in self.callbacks:
                for callback in self.callbacks[task_id]:
                    try:
                        callback(result)
                    except Exception as e:
                        self.logger.error(f"Callback execution failed for task {task_id}: {self._get_callback_error_message(e)}")
                
                # Clean up callbacks
                del self.callbacks[task_id]
            
            # Clean up future
            if task_id in self.futures:
                del self.futures[task_id]
                
        except Exception as e:
            self.logger.error(f"Task {task_id} failed: {self._get_task_error_message(task_id, e)}")
            self.results[task_id] = None
    
    def add_callback(self, task_id: str, callback: Callable):
        """
        Add a callback to be executed when a task completes.
        
        Args:
            task_id: Task identifier
            callback: Function to call with the result
        """
        if task_id not in self.callbacks:
            self.callbacks[task_id] = []
        self.callbacks[task_id].append(callback)
    
    def get_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """
        Get the result of a completed task.
        
        Args:
            task_id: Task identifier
            timeout: Maximum time to wait for completion
            
        Returns:
            Task result or None if not completed
        """
        if task_id in self.results:
            return self.results[task_id]
        
        if task_id in self.futures:
            try:
                result = self.futures[task_id].result(timeout=timeout)
                self.results[task_id] = result
                return result
            except Exception as e:
                self.logger.error(f"Error getting result for task {task_id}: {self._get_result_error_message(task_id, e)}")
                return None
        
        return None
    
    def is_completed(self, task_id: str) -> bool:
        """Check if a task is completed."""
        return task_id in self.results or (task_id in self.futures and self.futures[task_id].done())
    
    def wait_for_all(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all pending tasks to complete.
        
        Args:
            timeout: Maximum time to wait
            
        Returns:
            True if all tasks completed, False if timeout
        """
        start_time = time.time()
        
        while self.futures:
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            # Check completed futures
            completed = []
            for task_id, future in self.futures.items():
                if future.done():
                    completed.append(task_id)
            
            # Remove completed futures
            for task_id in completed:
                del self.futures[task_id]
            
            time.sleep(0.1)  # Small delay to prevent busy waiting
        
        return True
    
    def shutdown(self, wait: bool = True):
        """Shutdown the executor."""
        self.executor.shutdown(wait=wait)
    
    def _get_callback_error_message(self, error: Exception) -> str:
        """Get user-friendly error message for callback execution errors."""
        error_str = str(error).lower()
        if "permission denied" in error_str or "access denied" in error_str:
            return "Callback failed due to permission issues. Check file access permissions."
        elif "memory" in error_str or "out of memory" in error_str:
            return "Callback failed due to insufficient memory. Close other applications and try again."
        else:
            return f"Callback execution error: {str(error)}"
    
    def _get_task_error_message(self, task_id: str, error: Exception) -> str:
        """Get user-friendly error message for task execution errors."""
        error_str = str(error).lower()
        if "timeout" in error_str:
            return f"Task '{task_id}' timed out. The operation took longer than expected."
        elif "cancelled" in error_str:
            return f"Task '{task_id}' was cancelled before completion."
        elif "permission denied" in error_str or "access denied" in error_str:
            return f"Task '{task_id}' failed due to permission issues. Check file access permissions."
        elif "memory" in error_str or "out of memory" in error_str:
            return f"Task '{task_id}' failed due to insufficient memory. Close other applications and try again."
        else:
            return f"Task '{task_id}' execution error: {str(error)}"
    
    def _get_result_error_message(self, task_id: str, error: Exception) -> str:
        """Get user-friendly error message for result retrieval errors."""
        error_str = str(error).lower()
        if "timeout" in error_str:
            return f"Timeout waiting for task '{task_id}' to complete. The operation is taking longer than expected."
        elif "cancelled" in error_str:
            return f"Task '{task_id}' was cancelled and no result is available."
        else:
            return f"Error retrieving result for task '{task_id}': {str(error)}"

# Global async loader instance
async_loader = AsyncLoader()

def async_task(task_id: str = None):
    """
    Decorator to make a function execute asynchronously.
    
    Args:
        task_id: Optional task identifier (defaults to function name)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if task_id is None:
                current_task_id = f"{func.__name__}_{int(time.time())}"
            else:
                current_task_id = task_id
            
            return async_loader.submit_task(current_task_id, func, *args, **kwargs)
        
        return wrapper
    return decorator

class ProgressTracker:
    """
    Tracks progress of asynchronous operations.
    """
    
    def __init__(self, total_steps: int = 100):
        self.total_steps = total_steps
        self.current_step = 0
        self.message = ""
        self.callbacks: List[Callable] = []
        self._lock = threading.Lock()
    
    def update(self, step: int, message: str = ""):
        """
        Update progress.
        
        Args:
            step: Current step (0 to total_steps)
            message: Optional progress message
        """
        with self._lock:
            self.current_step = min(step, self.total_steps)
            self.message = message
            
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    callback(self.current_step, self.total_steps, self.message)
                except Exception:
                    pass
    
    def increment(self, message: str = ""):
        """Increment progress by 1."""
        self.update(self.current_step + 1, message)
    
    def set_message(self, message: str):
        """Set progress message without changing step."""
        with self._lock:
            self.message = message
            
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    callback(self.current_step, self.total_steps, self.message)
                except Exception:
                    pass
    
    def add_callback(self, callback: Callable):
        """Add a progress callback."""
        self.callbacks.append(callback)
    
    def get_progress(self) -> tuple:
        """Get current progress as (current, total, message)."""
        with self._lock:
            return self.current_step, self.total_steps, self.message
    
    def get_percentage(self) -> float:
        """Get progress as percentage."""
        with self._lock:
            return (self.current_step / self.total_steps) * 100 if self.total_steps > 0 else 0

class AsyncFileProcessor:
    """
    Asynchronous file processor for handling large files without blocking the UI.
    Uses the centralized FileProcessor to avoid code duplication.
    """
    
    def __init__(self):
        self.loader = AsyncLoader(max_workers=2)  # Limit file processing threads
        # Use centralized file processor
        from src.utils.file_processor import file_processor as fp
        self.file_processor = fp
    
    def process_files_async(self, file_paths: List[str], processor_func: Callable, 
                          progress_callback: Optional[Callable] = None) -> Future:
        """
        Process multiple files asynchronously.
        
        Args:
            file_paths: List of file paths to process
            processor_func: Function to process each file
            progress_callback: Optional callback for progress updates
            
        Returns:
            Future object representing the processing task
        """
        def process_all_files():
            results = []
            total_files = len(file_paths)
            
            for i, file_path in enumerate(file_paths):
                try:
                    # Validate file before processing
                    if not self.file_processor.validate_file(file_path):
                        results.append(None)
                        continue
                    
                    result = processor_func(file_path)
                    results.append(result)
                    
                    if progress_callback:
                        progress = int((i + 1) / total_files * 100)
                        progress_callback(progress, f"Processed {i + 1}/{total_files} files")
                        
                except Exception as e:
                    results.append(None)
                    if progress_callback:
                        progress_callback(100, f"Error processing {file_path}: {e}")
            
            return results
        
        return self.loader.submit_task("file_processing", process_all_files)
    
    def shutdown(self):
        """Shutdown the file processor."""
        self.loader.shutdown()

# Global file processor instance
async_file_processor = AsyncFileProcessor()

def measure_execution_time(func: Callable) -> Callable:
    """
    Decorator to measure execution time of a function.
    
    Args:
        func: Function to measure
        
    Returns:
        Wrapped function that logs execution time
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        logger = logging.getLogger(__name__)
        logger.info(f"{func.__name__} executed in {execution_time:.3f} seconds")
        
        return result
    
    return wrapper

if __name__ == "__main__":
    # Test the async loader
    import logging
    logging.basicConfig(level=logging.INFO)
    
    def test_task(duration: float):
        """Test task that takes some time."""
        time.sleep(duration)
        return f"Task completed after {duration} seconds"
    
    # Submit some test tasks
    future1 = async_loader.submit_task("task1", test_task, 1.0)
    future2 = async_loader.submit_task("task2", test_task, 2.0)
    
    print("Tasks submitted, waiting for completion...")
    
    # Wait for all tasks
    async_loader.wait_for_all()
    
    print("All tasks completed!")
    print(f"Task 1 result: {async_loader.get_result('task1')}")
    print(f"Task 2 result: {async_loader.get_result('task2')}")
    
    # Cleanup
    async_loader.shutdown()
