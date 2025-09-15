"""
Update Dialog for Excel Consolidator

This module provides a non-blocking update dialog that shows download progress
while allowing users to continue using the application.

Author: Excel Consolidator Team
Version: 1.0.0
"""

import sys
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QTextEdit, QFrame, QSizePolicy, QApplication
)
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPalette, QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject, QSize
from typing import Optional, Callable
import threading
import time


class UpdateProgressWorker(QObject):
    """
    Worker thread for handling update progress updates.
    """
    progress_updated = pyqtSignal(int, str)  # progress, message
    update_completed = pyqtSignal(bool, str)  # success, message
    download_progress = pyqtSignal(int, int, str)  # downloaded, total, message
    
    def __init__(self, update_callback: Callable):
        super().__init__()
        self.update_callback = update_callback
        self.is_running = False
        
    def start_update(self):
        """Start the update process in a separate thread."""
        self.is_running = True
        thread = threading.Thread(target=self._perform_update, daemon=True)
        thread.start()
        
    def _perform_update(self):
        """Perform the actual update process."""
        try:
            # Call the update callback with progress reporting
            success = self.update_callback(self._report_progress, self._report_download_progress)
            self.update_completed.emit(success, "Update completed successfully" if success else "Update failed")
        except Exception as e:
            self.update_completed.emit(False, f"Update error: {str(e)}")
        finally:
            self.is_running = False
            
    def _report_progress(self, progress: int, message: str):
        """Report progress update."""
        if self.is_running:
            self.progress_updated.emit(progress, message)
            
    def _report_download_progress(self, downloaded: int, total: int, message: str):
        """Report download progress update."""
        if self.is_running:
            self.download_progress.emit(downloaded, total, message)


class UpdateDialog(QDialog):
    """
    Non-blocking update dialog that shows download progress and status.
    
    This dialog cannot be closed until the update is complete and successfully installed.
    """
    
    def __init__(self, parent=None, update_callback: Optional[Callable] = None):
        super().__init__(parent)
        self.update_callback = update_callback
        self.is_updating = False
        self.update_successful = False
        self.worker = None
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Excel Consolidator - Updating")
        self.setModal(False)  # Non-blocking dialog
        self.resize(900, 650)  # Same size as main application window
        self.setMinimumSize(800, 600)
        self.setWindowFlags(
            Qt.Dialog | 
            Qt.WindowTitleHint | 
            Qt.WindowCloseButtonHint | 
            Qt.WindowMinimizeButtonHint
        )
        
        # Disable close button initially
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        
        # Apply the same styling as the main application
        self.setStyleSheet("""
            QDialog {
                background-color: #deeaee;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header section - using the same teal color scheme as the app
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_frame.setFixedHeight(100)
        header_frame.setStyleSheet("""
            QFrame#HeaderFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0f766e, stop:1 #0d9488);
                border: 1px solid #0f766e;
                border-radius: 10px;
                margin: 5px;
            }
        """)
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Title - matching the app's header styling
        self.title_label = QLabel("🔄 Updating Excel Consolidator")
        self.title_label.setObjectName("HeaderTitle")
        self.title_label.setStyleSheet("""
            QLabel#HeaderTitle {
                color: #ffffff;
                font-size: 22px;
                font-weight: bold;
                background: transparent;
            }
        """)
        header_layout.addWidget(self.title_label)
        
        # Subtitle - matching the app's subtitle styling
        self.subtitle_label = QLabel("Please wait while we download and install the latest version...")
        self.subtitle_label.setObjectName("HeaderSubtitle")
        self.subtitle_label.setStyleSheet("""
            QLabel#HeaderSubtitle {
                color: rgba(255, 255, 255, 0.9);
                font-size: 14px;
                background: transparent;
            }
        """)
        header_layout.addWidget(self.subtitle_label)
        
        main_layout.addWidget(header_frame)
        
        # Progress section - using the same group box styling as the app
        progress_frame = QFrame()
        progress_frame.setObjectName("ProgressFrame")
        progress_frame.setStyleSheet("""
            QFrame#ProgressFrame {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                margin: 5px;
                padding-top: 22px;
            }
        """)
        
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(20, 20, 20, 20)
        progress_layout.setSpacing(18)
        
        # Current status - matching the app's text styling
        self.status_label = QLabel("Initializing update...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #1f2937;
                font-size: 16px;
                font-weight: 600;
                background: transparent;
            }
        """)
        progress_layout.addWidget(self.status_label)
        
        # Main progress bar - using the exact same styling as the app
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                text-align: center;
                background-color: #ffffff;
                height: 20px;
                color: #1f2937;
                font-weight: 600;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 8px;
            }
        """)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        # Download progress (for detailed download tracking) - using secondary styling
        self.download_label = QLabel("")
        self.download_label.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 13px;
                background: transparent;
            }
        """)
        self.download_label.hide()  # Initially hidden
        progress_layout.addWidget(self.download_label)
        
        self.download_progress = QProgressBar()
        self.download_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                text-align: center;
                font-size: 11px;
                color: #6b7280;
                background-color: #f9fafb;
                height: 16px;
            }
            QProgressBar::chunk {
                background-color: #0ea5e9;
                border-radius: 6px;
            }
        """)
        self.download_progress.setRange(0, 100)
        self.download_progress.setValue(0)
        self.download_progress.hide()  # Initially hidden
        progress_layout.addWidget(self.download_progress)
        
        main_layout.addWidget(progress_frame)
        
        # Log section - using the same styling as read-only text areas in the app
        log_frame = QFrame()
        log_frame.setObjectName("LogFrame")
        log_frame.setStyleSheet("""
            QFrame#LogFrame {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                margin: 5px;
                padding-top: 22px;
            }
        """)
        
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(15, 15, 15, 15)
        
        log_title = QLabel("Update Log")
        log_title.setStyleSheet("""
            QLabel {
                color: #0f766e;
                font-size: 14px;
                font-weight: 600;
                background: transparent;
            }
        """)
        log_layout.addWidget(log_title)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit[readOnly="true"] {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                color: #1f2937;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 10px;
                line-height: 1.4;
            }
        """)
        self.log_text.setMinimumHeight(200)
        log_layout.addWidget(self.log_text)
        
        main_layout.addWidget(log_frame)
        
        # Button section - using the exact same button styling as the app
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Minimize button - using tertiary button styling
        self.minimize_button = QPushButton("Minimize")
        self.minimize_button.setObjectName("TertiaryButton")
        self.minimize_button.setStyleSheet("""
            QPushButton#TertiaryButton {
                background: #ffffff;
                color: #111827;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton#TertiaryButton:hover {
                background: #f9fafb;
            }
        """)
        self.minimize_button.clicked.connect(self.showMinimized)
        button_layout.addWidget(self.minimize_button)
        
        button_layout.addStretch()
        
        # Close button - using danger button styling when enabled
        self.close_button = QPushButton("Close")
        self.close_button.setObjectName("DangerButton")
        self.close_button.setStyleSheet("""
            QPushButton#DangerButton {
                background: #ef4444;
                color: white;
                border: 1px solid #ef4444;
                border-radius: 8px;
                padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton#DangerButton:hover {
                background: #dc2626;
                border-color: #dc2626;
            }
            QPushButton#DangerButton:disabled {
                background-color: #f3f4f6;
                color: #9ca3af;
                border-color: #e5e7eb;
            }
        """)
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        main_layout.addLayout(button_layout)
        
        # Add initial log entry
        self.add_log("Update dialog initialized")
        
    def setup_connections(self):
        """Setup signal connections."""
        pass  # Will be set up when worker is created
        
    def start_update(self):
        """Start the update process."""
        if not self.update_callback:
            self.add_log("ERROR: No update callback provided")
            return
            
        self.is_updating = True
        self.add_log("Starting update process...")
        
        # Create and start worker
        self.worker = UpdateProgressWorker(self.update_callback)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.download_progress.connect(self.update_download_progress)
        self.worker.update_completed.connect(self.on_update_completed)
        
        self.worker.start_update()
        
    def update_progress(self, progress: int, message: str):
        """Update the main progress bar and status."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
        self.add_log(f"[{progress}%] {message}")
        
    def update_download_progress(self, downloaded: int, total: int, message: str):
        """Update the download progress bar."""
        if total > 0:
            download_percent = int((downloaded / total) * 100)
            self.download_progress.setValue(download_percent)
            self.download_label.setText(f"Download: {self.format_bytes(downloaded)} / {self.format_bytes(total)} ({download_percent}%)")
            self.download_label.show()
            self.download_progress.show()
            self.add_log(f"Download: {self.format_bytes(downloaded)} / {self.format_bytes(total)}")
        else:
            self.download_label.setText(message)
            self.download_label.show()
            
    def on_update_completed(self, success: bool, message: str):
        """Handle update completion."""
        self.is_updating = False
        self.update_successful = success
        
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("Update completed successfully!")
            self.title_label.setText("✅ Update Complete")
            self.subtitle_label.setText("The application will restart automatically.")
            self.add_log("✅ Update completed successfully!")
            
            # Change header to success styling
            header_frame = self.findChild(QFrame, "HeaderFrame")
            if header_frame:
                header_frame.setStyleSheet("""
                    QFrame#HeaderFrame {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #10b981, stop:1 #059669);
                        border: 1px solid #10b981;
                        border-radius: 10px;
                        margin: 5px;
                    }
                """)
            
            # Enable close button and allow dialog to be closed
            self.close_button.setEnabled(True)
            self.close_button.setObjectName("SuccessButton")
            self.close_button.setStyleSheet("""
                QPushButton#SuccessButton {
                    background: #10b981;
                    color: white;
                    border: 1px solid #10b981;
                    border-radius: 8px;
                    padding: 10px 14px;
                    font-weight: 600;
                }
                QPushButton#SuccessButton:hover {
                    background: #059669;
                    border-color: #059669;
                }
            """)
            self.close_button.setText("Restart Application")
            self.setWindowFlags(self.windowFlags() | Qt.WindowCloseButtonHint)
            self.setWindowTitle("Excel Consolidator - Update Complete")
            
            # Auto-close after 3 seconds
            QTimer.singleShot(3000, self.accept)
        else:
            self.status_label.setText("Update failed!")
            self.title_label.setText("❌ Update Failed")
            self.subtitle_label.setText("Please try updating manually or contact support.")
            self.add_log(f"❌ Update failed: {message}")
            
            # Change header to error styling
            header_frame = self.findChild(QFrame, "HeaderFrame")
            if header_frame:
                header_frame.setStyleSheet("""
                    QFrame#HeaderFrame {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #ef4444, stop:1 #dc2626);
                        border: 1px solid #ef4444;
                        border-radius: 10px;
                        margin: 5px;
                    }
                """)
            
            # Enable close button for failed updates
            self.close_button.setEnabled(True)
            self.setWindowFlags(self.windowFlags() | Qt.WindowCloseButtonHint)
            self.setWindowTitle("Excel Consolidator - Update Failed")
            
    def add_log(self, message: str):
        """Add a message to the log."""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_text.append(log_entry)
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"
        
    def closeEvent(self, event):
        """Handle close event."""
        if self.is_updating:
            # Prevent closing while updating
            event.ignore()
            return
            
        if not self.update_successful and self.is_updating:
            # Prevent closing if update failed and we're still updating
            event.ignore()
            return
            
        # Allow closing if update is complete or failed
        event.accept()
        
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key_Escape and self.is_updating:
            # Prevent closing with Escape while updating
            event.ignore()
            return
            
        super().keyPressEvent(event)


def create_update_dialog(parent=None, update_callback: Optional[Callable] = None) -> UpdateDialog:
    """
    Create and return a new update dialog.
    
    Args:
        parent: Parent widget
        update_callback: Callback function for performing the update
        
    Returns:
        UpdateDialog instance
    """
    dialog = UpdateDialog(parent, update_callback)
    return dialog


# Example usage and testing
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    def test_update_callback(progress_callback, download_callback):
        """Test callback for demonstration."""
        import time
        
        # Simulate update process
        steps = [
            (10, "Checking for updates..."),
            (20, "Update available! Preparing download..."),
            (30, "Downloading update..."),
            (50, "Downloading update..."),
            (70, "Downloading update..."),
            (90, "Download complete! Installing..."),
            (95, "Installing update..."),
            (100, "Update complete! Restarting...")
        ]
        
        for progress, message in steps:
            progress_callback(progress, message)
            
            # Simulate download progress for some steps
            if "Downloading" in message:
                for i in range(3):
                    download_callback(1024 * 1024 * (i + 1), 3 * 1024 * 1024, f"Downloading... {i+1}/3")
                    time.sleep(0.5)
            
            time.sleep(1)
        
        return True  # Simulate successful update
    
    app = QApplication(sys.argv)
    
    dialog = create_update_dialog(update_callback=test_update_callback)
    dialog.show()
    dialog.start_update()
    
    sys.exit(app.exec_())
