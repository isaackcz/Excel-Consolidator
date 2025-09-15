"""
Lazy Loading Module for Excel Consolidator

This module provides lazy loading functionality to improve application startup time
by deferring heavy imports until they are actually needed.
"""

import sys
import importlib
from typing import Any, Dict, Optional
import threading
from functools import wraps

class LazyLoader:
    """
    A lazy loader that defers module imports until they are actually accessed.
    This significantly improves startup time by avoiding heavy imports at application start.
    """
    
    def __init__(self):
        self._modules: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def __getattr__(self, name: str) -> Any:
        """Dynamically load modules when accessed."""
        with self._lock:
            if name not in self._modules:
                self._modules[name] = self._load_module(name)
            return self._modules[name]
    
    def _load_module(self, name: str) -> Any:
        """Load a module by name."""
        try:
            return importlib.import_module(name)
        except ImportError as e:
            raise ImportError(f"Failed to load module '{name}': {e}")
    
    def preload(self, *module_names: str) -> None:
        """Preload specified modules in background."""
        def preload_worker():
            for module_name in module_names:
                try:
                    with self._lock:
                        if module_name not in self._modules:
                            self._modules[module_name] = self._load_module(module_name)
                except ImportError:
                    pass  # Silently ignore import errors during preloading
        
        thread = threading.Thread(target=preload_worker, daemon=True)
        thread.start()

# Global lazy loader instance
lazy = LazyLoader()

def lazy_import(module_name: str):
    """
    Decorator to make a function use lazy imports.
    
    Args:
        module_name: Name of the module to import lazily
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            module = getattr(lazy, module_name)
            return func(module, *args, **kwargs)
        return wrapper
    return decorator

# Predefined lazy loaders for common heavy modules
class PandasLoader:
    """Lazy loader for pandas operations."""
    
    def __init__(self):
        self._pandas = None
        self._numpy = None
    
    @property
    def pandas(self):
        if self._pandas is None:
            self._pandas = importlib.import_module('pandas')
        return self._pandas
    
    @property
    def numpy(self):
        if self._numpy is None:
            self._numpy = importlib.import_module('numpy')
        return self._numpy

class ExcelLoader:
    """Lazy loader for Excel processing modules."""
    
    def __init__(self):
        self._openpyxl = None
        self._xlrd = None
    
    @property
    def openpyxl(self):
        if self._openpyxl is None:
            self._openpyxl = importlib.import_module('openpyxl')
        return self._openpyxl
    
    @property
    def xlrd(self):
        if self._xlrd is None:
            self._xlrd = importlib.import_module('xlrd')
        return self._xlrd

class QtLoader:
    """Lazy loader for PyQt5 modules."""
    
    def __init__(self):
        self._qt_widgets = None
        self._qt_gui = None
        self._qt_core = None
    
    @property
    def widgets(self):
        if self._qt_widgets is None:
            self._qt_widgets = importlib.import_module('PyQt5.QtWidgets')
        return self._qt_widgets
    
    @property
    def gui(self):
        if self._qt_gui is None:
            self._qt_gui = importlib.import_module('PyQt5.QtGui')
        return self._qt_gui
    
    @property
    def core(self):
        if self._qt_core is None:
            self._qt_core = importlib.import_module('PyQt5.QtCore')
        return self._qt_core

# Global instances
pandas_loader = PandasLoader()
excel_loader = ExcelLoader()
qt_loader = QtLoader()

def preload_heavy_modules():
    """
    Preload heavy modules in background threads to improve perceived performance.
    This should be called early in the application lifecycle.
    """
    # Preload in order of importance and size
    preload_modules = [
        'PyQt5.QtCore',
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
        'pandas',
        'numpy',
        'openpyxl',
        'xlrd'
    ]
    
    lazy.preload(*preload_modules)

def get_import_time(module_name: str) -> float:
    """
    Measure the time it takes to import a module.
    
    Args:
        module_name: Name of the module to measure
        
    Returns:
        Import time in seconds
    """
    import time
    
    start_time = time.time()
    try:
        importlib.import_module(module_name)
        return time.time() - start_time
    except ImportError:
        return -1

def benchmark_imports() -> Dict[str, float]:
    """
    Benchmark import times for all heavy modules.
    
    Returns:
        Dictionary mapping module names to import times
    """
    modules = [
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets', 
        'pandas',
        'numpy',
        'openpyxl',
        'xlrd',
        'requests',
        'json',
        'threading'
    ]
    
    results = {}
    for module in modules:
        results[module] = get_import_time(module)
    
    return results

if __name__ == "__main__":
    # Benchmark import times
    print("Benchmarking import times...")
    times = benchmark_imports()
    
    print("\nImport Times:")
    for module, time_taken in sorted(times.items(), key=lambda x: x[1], reverse=True):
        if time_taken > 0:
            print(f"  {module}: {time_taken:.3f}s")
        else:
            print(f"  {module}: Failed to import")
    
    total_time = sum(t for t in times.values() if t > 0)
    print(f"\nTotal import time: {total_time:.3f}s")
