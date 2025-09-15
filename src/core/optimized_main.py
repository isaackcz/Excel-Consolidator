"""
Optimized Main Application for Excel Consolidator v1.0.7

This module provides an optimized version of the main application with:
- Lazy loading of heavy dependencies
- Asynchronous initialization
- Improved startup performance
- Better memory management
- Enhanced error handling

Author: Excel Consolidator Team
Version: 1.0.7
"""

import sys
import os
import time
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Import our optimized modules
from src.core.lazy_loader import (
    lazy, pandas_loader, excel_loader, qt_loader, 
    preload_heavy_modules, benchmark_imports
)
from src.core.async_loader import AsyncLoader, ProgressTracker, measure_execution_time
from src.core.version import APP_VERSION, APP_NAME, GITHUB_OWNER, GITHUB_REPO

# Import optimized auto-updater
from src.modules.optimized_auto_update import setup_optimized_auto_updater

class OptimizedExcelConsolidator:
    """
    Optimized Excel Consolidator application with lazy loading and async initialization.
    """
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.auto_updater = None
        self.async_loader = AsyncLoader(max_workers=4)
        self.initialization_progress = ProgressTracker(100)
        self.logger = self._setup_logging()
        
        # Performance metrics
        self.startup_time = 0
        self.import_times = {}
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the application."""
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_dir / "app.log"),
                    logging.StreamHandler()
                ]
            )
            return logging.getLogger(__name__)
        except Exception:
            return logging.getLogger(__name__)
    
    @measure_execution_time
    def initialize_async(self, progress_callback: Optional[callable] = None):
        """
        Initialize the application asynchronously to improve perceived performance.
        
        Args:
            progress_callback: Optional callback for progress updates
        """
        try:
            self.logger.info("Starting optimized application initialization")
            start_time = time.time()
            
            if progress_callback:
                progress_callback(0, "Initializing Excel Consolidator v1.0.7...")
            
            # Step 1: Preload heavy modules in background
            if progress_callback:
                progress_callback(10, "Preloading modules...")
            
            self._preload_modules_async()
            
            # Step 2: Initialize Qt application
            if progress_callback:
                progress_callback(30, "Initializing GUI framework...")
            
            self._initialize_qt_app()
            
            # Step 3: Setup auto-updater
            if progress_callback:
                progress_callback(50, "Setting up auto-updater...")
            
            self._setup_auto_updater()
            
            # Step 4: Initialize main window
            if progress_callback:
                progress_callback(70, "Creating main window...")
            
            self._initialize_main_window()
            
            # Step 5: Final setup
            if progress_callback:
                progress_callback(90, "Finalizing setup...")
            
            self._finalize_setup()
            
            # Calculate startup time
            self.startup_time = time.time() - start_time
            
            if progress_callback:
                progress_callback(100, f"Application ready! (Startup: {self.startup_time:.2f}s)")
            
            self.logger.info(f"Application initialization completed in {self.startup_time:.2f} seconds")
            
        except Exception as e:
            self.logger.error(f"Error during initialization: {e}")
            if progress_callback:
                progress_callback(100, f"Initialization failed: {str(e)}")
            raise
    
    def _preload_modules_async(self):
        """Preload heavy modules in background threads."""
        try:
            self.logger.info("Preloading heavy modules...")
            
            # Start preloading in background
            preload_heavy_modules()
            
            # Benchmark import times for performance monitoring
            self.import_times = benchmark_imports()
            
            self.logger.info("Module preloading completed")
            
        except Exception as e:
            self.logger.warning(f"Error preloading modules: {e}")
    
    def _initialize_qt_app(self):
        """Initialize Qt application with lazy loading."""
        try:
            self.logger.info("Initializing Qt application...")
            
            # Use lazy loading for Qt modules
            QtWidgets = qt_loader.widgets
            QtCore = qt_loader.core
            
            # Create QApplication
            self.app = QtWidgets.QApplication(sys.argv)
            self.app.setApplicationName(APP_NAME)
            self.app.setApplicationVersion(APP_VERSION)
            
            # Set application properties
            self.app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
            self.app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
            
            self.logger.info("Qt application initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing Qt application: {e}")
            raise
    
    def _setup_auto_updater(self):
        """Setup optimized auto-updater."""
        try:
            self.logger.info("Setting up optimized auto-updater...")
            
            self.auto_updater = setup_optimized_auto_updater(
                current_version=APP_VERSION,
                github_owner=GITHUB_OWNER,
                github_repo=GITHUB_REPO
            )
            
            if self.auto_updater:
                self.logger.info("Auto-updater setup successful")
            else:
                self.logger.warning("Auto-updater setup failed")
                
        except Exception as e:
            self.logger.warning(f"Error setting up auto-updater: {e}")
    
    def _initialize_main_window(self):
        """Initialize the main window with lazy loading."""
        try:
            self.logger.info("Creating main window...")
            
            # Import main window class lazily
            from src.core.main import ExcelConsolidatorApp
            
            # Create main window
            self.main_window = ExcelConsolidatorApp()
            
            self.logger.info("Main window created successfully")
            
        except Exception as e:
            self.logger.error(f"Error creating main window: {e}")
            raise
    
    def _finalize_setup(self):
        """Finalize application setup."""
        try:
            self.logger.info("Finalizing application setup...")
            
            # Show main window
            if self.main_window:
                self.main_window.show()
            
            # Log performance metrics
            self._log_performance_metrics()
            
            self.logger.info("Application setup finalized")
            
        except Exception as e:
            self.logger.error(f"Error finalizing setup: {e}")
            raise
    
    def _log_performance_metrics(self):
        """Log performance metrics for monitoring."""
        try:
            self.logger.info("=" * 50)
            self.logger.info("PERFORMANCE METRICS")
            self.logger.info("=" * 50)
            self.logger.info(f"Total startup time: {self.startup_time:.3f} seconds")
            
            if self.import_times:
                self.logger.info("Import times:")
                for module, import_time in sorted(self.import_times.items(), key=lambda x: x[1], reverse=True):
                    if import_time > 0:
                        self.logger.info(f"  {module}: {import_time:.3f}s")
            
            self.logger.info("=" * 50)
            
        except Exception as e:
            self.logger.warning(f"Error logging performance metrics: {e}")
    
    def run(self):
        """Run the application."""
        try:
            if not self.app:
                raise RuntimeError("Application not initialized")
            
            self.logger.info("Starting application main loop")
            
            # Run the application
            return self.app.exec_()
            
        except Exception as e:
            self.logger.error(f"Error running application: {e}")
            raise
    
    def cleanup(self):
        """Clean up resources."""
        try:
            self.logger.info("Cleaning up application resources...")
            
            # Stop auto-updater
            if self.auto_updater:
                self.auto_updater.cleanup()
            
            # Shutdown async loader
            if self.async_loader:
                self.async_loader.shutdown()
            
            self.logger.info("Application cleanup completed")
            
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")

def create_splash_screen():
    """Create a splash screen for better user experience during startup."""
    try:
        QtWidgets = qt_loader.widgets
        QtGui = qt_loader.gui
        QtCore = qt_loader.core
        
        # Create splash screen
        splash_pix = QtGui.QPixmap(400, 300)
        splash_pix.fill(QtGui.QColor(240, 240, 240))
        
        splash = QtWidgets.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
        splash.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint)
        
        # Add text to splash screen
        splash.showMessage(
            f"Loading {APP_NAME} v{APP_VERSION}...",
            QtCore.Qt.AlignBottom | QtCore.Qt.AlignCenter,
            QtGui.QColor(0, 0, 0)
        )
        
        splash.show()
        return splash
        
    except Exception as e:
        logging.getLogger(__name__).warning(f"Error creating splash screen: {e}")
        return None

def main():
    """Main entry point for the optimized application."""
    try:
        # Create splash screen
        splash = create_splash_screen()
        
        # Create application instance
        app = OptimizedExcelConsolidator()
        
        # Initialize asynchronously with progress updates
        def progress_callback(progress: int, message: str):
            if splash:
                splash.showMessage(
                    f"{message} ({progress}%)",
                    splash.Alignment.Bottom | splash.Alignment.Center
                )
                splash.repaint()
        
        # Initialize the application
        app.initialize_async(progress_callback)
        
        # Close splash screen
        if splash:
            splash.finish(app.main_window)
        
        # Run the application
        return app.run()
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Fatal error: {e}")
        return 1
    finally:
        # Cleanup
        if 'app' in locals():
            app.cleanup()

if __name__ == "__main__":
    sys.exit(main())
