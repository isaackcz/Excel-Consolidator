import sys
import os
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QFrame, QSpacerItem, QSizePolicy, QDialog, 
    QProgressBar, QGroupBox, QTextEdit, QListWidget, QSplitter, QCheckBox,
    QComboBox, QSpinBox, QLineEdit, QTabWidget, QScrollArea, QGridLayout,
    QSlider, QDoubleSpinBox, QRadioButton, QButtonGroup, QStyle
)
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QPixmap, QCursor
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QObject, QEvent, QPoint
from PyQt5.QtGui import QHelpEvent
from typing import Optional
import webbrowser
from copy import copy
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.cell.cell import MergedCell
from openpyxl.utils import get_column_letter, column_index_from_string
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.comments import Comment
import glob
from datetime import datetime, timedelta
import json
import shutil
import hashlib
import re
import xlrd  # For .xls files
import csv
from decimal import Decimal, InvalidOperation
import threading
import warnings
warnings.filterwarnings('ignore')

# Import our custom modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.modules.google_sheets_reporter import setup_google_sheets_error_reporting, GoogleSheetsErrorReporter
from src.modules.auto_update import setup_auto_updater, AutoUpdater
from src.core.version import APP_VERSION, APP_NAME, GITHUB_OWNER, GITHUB_REPO, ERROR_REPORTING_ENABLED, AUTO_UPDATE_ENABLED

class FileProcessor:
    """Handles different file formats"""
    
    @staticmethod
    def read_excel_file(filepath, sheet_name=None, data_only=True):
        """Read Excel file (.xlsx, .xls)"""
        try:
            if filepath.endswith('.xlsx'):
                wb = openpyxl.load_workbook(filepath, data_only=data_only)
                if sheet_name and sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                else:
                    ws = wb.active
                return wb, ws, "xlsx"
            
            elif filepath.endswith('.xls'):
                # Handle legacy Excel format
                wb_xlrd = xlrd.open_workbook(filepath)
                if sheet_name:
                    try:
                        sheet_idx = wb_xlrd.sheet_names().index(sheet_name)
                        ws_xlrd = wb_xlrd.sheet_by_index(sheet_idx)
                    except ValueError:
                        ws_xlrd = wb_xlrd.sheet_by_index(0)
                else:
                    ws_xlrd = wb_xlrd.sheet_by_index(0)
                return wb_xlrd, ws_xlrd, "xls"
            
        except Exception as e:
            return None, None, f"error: {str(e)}"
        
        return None, None, "unsupported_format"
    
    @staticmethod
    def read_csv_file(filepath):
        """Read CSV file"""
        try:
            df = pd.read_csv(filepath)
            return df, "csv"
        except Exception as e:
            return None, f"error: {str(e)}"

# ---------------- Sticky Tooltip Manager ----------------
class StickyToolTip(QWidget):
    """A small frameless widget that behaves like a sticky tooltip.

    It stays open until the user clicks outside it. Position near a global point.
    """
    def __init__(self, text: str, parent: QWidget = None):
        # Use Popup so it stays until clicking outside; frameless for tooltip look
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        label = QLabel(text, self)
        label.setWordWrap(True)
        layout.addWidget(label)

        # Match app tooltip style
        self.setStyleSheet("QWidget { background-color: #333333; color: #ffffff; border: none; border-radius: 4px; }")

    def show_at(self, global_pos: QPoint):
        self.move(global_pos)
        self.show()


class GlobalToolTipFilter(QObject):
    """Intercepts QEvent.ToolTip and shows a sticky tooltip that closes on outside click."""
    def __init__(self, app: QApplication):
        super().__init__(app)
        self.app = app
        self.current_tip: Optional[StickyToolTip] = None

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        # Replace default tooltip behavior with a sticky popup
        if event.type() == QEvent.ToolTip:
            # Safely get tooltip text if widget provides one
            tooltip_text = ''
            try:
                tooltip_text = obj.toolTip()  # type: ignore[attr-defined]
            except Exception:
                tooltip_text = ''

            # Always suppress default tooltip handling
            if not tooltip_text:
                if self.current_tip:
                    self.current_tip.close()
                    self.current_tip = None
                return True

            # Toggle off if already visible
            if self.current_tip and self.current_tip.isVisible():
                self.current_tip.close()
                self.current_tip = None
                return True

            # Determine global position if available
            global_pos = QPoint(QCursor.pos())
            try:
                # If it's a help event, prefer its global pos
                if hasattr(event, 'globalPos'):
                    global_pos = event.globalPos()  # type: ignore
            except Exception:
                pass

            # Show sticky popup offset from cursor
            self.current_tip = StickyToolTip(tooltip_text)
            self.current_tip.show_at(global_pos + QPoint(12, 12))
            return True

        # Close popup when clicking outside of it
        if event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick):
            if self.current_tip and self.current_tip.isVisible():
                global_click = QCursor.pos()
                if not self.current_tip.frameGeometry().contains(global_click):
                    self.current_tip.close()
                    self.current_tip = None
        return False

# ---------------- Advanced Configuration Dialog ----------------
class AdvancedConfigDialog(QDialog):
    """Advanced configuration options for consolidation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Consolidation Settings")
        self.setFixedSize(800, 700)
        self.setup_tooltip_timing()
        self.init_ui()
    
    def setup_tooltip_timing(self):
        """Configure global tooltip timing for this dialog"""
        # Set tooltip delay to 1000ms (1 second) and hide after 5000ms (5 seconds)
        QApplication.instance().setAttribute(Qt.AA_DisableWindowContextHelpButton, True)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Advanced Consolidation Settings")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2F5597; padding: 10px;")
        layout.addWidget(title_label)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left panel - Section selection
        left_panel = self.create_section_panel()
        content_layout.addWidget(left_panel, 1)
        
        # Right panel - Preview
        right_panel = self.create_preview_panel()
        content_layout.addWidget(right_panel, 2)
        
        layout.addLayout(content_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("Preview analysis")
        self.preview_btn.clicked.connect(self.preview_analysis)
        self.preview_btn.setEnabled(False)
        
        self.generate_btn = QPushButton("Generate analysis")
        self.generate_btn.clicked.connect(self.generate_analysis)
        self.generate_btn.setEnabled(False)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.preview_btn)
        button_layout.addWidget(self.generate_btn)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def create_section_panel(self):
        """Create the section selection panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Panel title
        title = QLabel("📋 Available Sections")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #2F5597;")
        layout.addWidget(title)
        
        # Scroll area for sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(300)
        
        self.section_widget = QWidget()
        self.section_layout = QVBoxLayout(self.section_widget)
        scroll.setWidget(self.section_widget)
        
        layout.addWidget(scroll)
        
        return panel
    
    def create_preview_panel(self):
        """Create the preview panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Panel title and file filter
        header_layout = QHBoxLayout()
        
        title = QLabel("👁️ Analysis Preview")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #2F5597;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # File filter dropdown
        filter_label = QLabel("Filter by file:")
        self.file_filter = QComboBox()
        self.file_filter.addItem("All Files")
        for filename in getattr(self, 'file_data', {}).keys():
            self.file_filter.addItem(filename)
        self.file_filter.currentTextChanged.connect(self.update_preview)
        
        header_layout.addWidget(filter_label)
        header_layout.addWidget(self.file_filter)
        
        layout.addLayout(header_layout)
        
        # Preview area
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setStyleSheet("background-color: #f8f9fa; border: 1px solid #ddd;")
        layout.addWidget(self.preview_text)
        
        return panel
    
    def scan_sections(self):
        """Scan the consolidated file for available sections"""
        try:
            wb = openpyxl.load_workbook(self.consolidated_file_path, data_only=True)
            ws = wb.active
            
            sections = self._identify_sections(ws)
            
            for section in sections:
                checkbox = QCheckBox(section['name'])
                checkbox.setStyleSheet("font-size: 12px; padding: 5px;")
                checkbox.stateChanged.connect(self.on_section_changed)
                checkbox.section_data = section
                self.section_layout.addWidget(checkbox)
            
            self.section_layout.addStretch()
            
        except Exception as e:
            error_label = QLabel(f"Error scanning sections: {e}")
            error_label.setStyleSheet("color: red; font-style: italic;")
            self.section_layout.addWidget(error_label)
    
    def _identify_sections(self, worksheet):
        """Identify sections in the worksheet"""
        sections = []
        
        # Scan for different types of sections
        for row in range(1, min(worksheet.max_row + 1, 100)):
            for col in range(1, min(worksheet.max_column + 1, 20)):
                cell = worksheet.cell(row=row, column=col)
                
                if cell.value and isinstance(cell.value, str):
                    value = str(cell.value).strip().upper()
                    
                    # Look for section headers
                    if any(keyword in value for keyword in ['ACCESS', 'ENROLLMENT', 'ENROLMENT', 'DROPOUT', 'INFRASTRUCTURE', 'GRADE', 'TOTAL']):
                        # Check if this is a significant section with data
                        data_range = self._get_section_data_range(worksheet, row, col)
                        if data_range['data_count'] > 0:
                            sections.append({
                                'name': value,
                                'start_row': row,
                                'start_col': col,
                                'data_range': data_range,
                                'type': self._classify_section_type(value)
                            })
        
        # Remove duplicates and sort
        unique_sections = {}
        for section in sections:
            key = section['name']
            if key not in unique_sections or section['data_range']['data_count'] > unique_sections[key]['data_range']['data_count']:
                unique_sections[key] = section
        
        return list(unique_sections.values())
    
    def _get_section_data_range(self, worksheet, start_row, start_col):
        """Get the data range for a specific section with proper boundaries"""
        data_count = 0
        numeric_values = []
        end_row = start_row
        end_col = start_col
        
        # Find the actual section boundaries by looking for the next section header or empty space
        section_end_row = self._find_section_end_row(worksheet, start_row)
        section_end_col = self._find_section_end_col(worksheet, start_col, start_row)
        
        # Scan only within this specific section's boundaries
        for row in range(start_row, min(section_end_row + 1, worksheet.max_row + 1)):
            for col in range(start_col, min(section_end_col + 1, worksheet.max_column + 1)):
                cell = worksheet.cell(row=row, column=col)
                if cell.value is not None:
                    # Skip TOTAL cells and similar summary cells
                    if isinstance(cell.value, str) and any(total_word in str(cell.value).upper() for total_word in ['TOTAL', 'SUM', 'GRAND']):
                        continue
                    
                    if isinstance(cell.value, (int, float)) and cell.value != 0:
                        data_count += 1
                        numeric_values.append(cell.value)
                        end_row = max(end_row, row)
                        end_col = max(end_col, col)
        
        return {
            'start_row': start_row,
            'start_col': start_col,
            'end_row': min(end_row, section_end_row),
            'end_col': min(end_col, section_end_col),
            'data_count': data_count,
            'numeric_values': numeric_values,
            'section_boundaries': {
                'end_row': section_end_row,
                'end_col': section_end_col
            }
        }
    
    def _find_section_end_row(self, worksheet, start_row):
        """Find where this section ends by looking for the next section header or significant gap"""
        max_scan_rows = 50
        empty_row_count = 0
        
        for row in range(start_row + 1, min(start_row + max_scan_rows, worksheet.max_row + 1)):
            row_has_content = False
            
            # Check if this row has any content
            for col in range(1, min(worksheet.max_column + 1, 30)):
                cell = worksheet.cell(row=row, column=col)
                if cell.value is not None:
                    row_has_content = True
                    
                    # Check if this looks like a new section header
                    if isinstance(cell.value, str):
                        value = str(cell.value).strip().upper()
                        if any(keyword in value for keyword in ['ACCESS', 'ENROLLMENT', 'ENROLMENT', 'DROPOUT', 'INFRASTRUCTURE', 'GRADE', 'OVERALL TOTAL']):
                            # This looks like a new section, so previous row is our boundary
                            return row - 1
                    break
            
            if not row_has_content:
                empty_row_count += 1
                if empty_row_count >= 3:  # 3 consecutive empty rows = section end
                    return row - empty_row_count
            else:
                empty_row_count = 0
        
        return start_row + max_scan_rows - 1
    
    def _find_section_end_col(self, worksheet, start_col, start_row):
        """Find where this section ends horizontally"""
        max_scan_cols = 25
        
        for col in range(start_col + 1, min(start_col + max_scan_cols, worksheet.max_column + 1)):
            col_has_content = False
            
            # Check if this column has any content in the section area
            for row in range(start_row, min(start_row + 20, worksheet.max_row + 1)):
                cell = worksheet.cell(row=row, column=col)
                if cell.value is not None:
                    col_has_content = True
                    break
            
            if not col_has_content:
                return col - 1
        
        return start_col + max_scan_cols - 1
    
    def _classify_section_type(self, section_name):
        """Classify the type of section"""
        name_lower = section_name.lower()
        
        if 'grade' in name_lower:
            return 'grade_analysis'
        elif any(word in name_lower for word in ['access', 'enrollment', 'enrolment']):
            return 'enrollment_analysis'
        elif 'dropout' in name_lower:
            return 'dropout_analysis'
        elif 'infrastructure' in name_lower:
            return 'infrastructure_analysis'
        else:
            return 'general_analysis'
    
    def _process_file_data(self, file_details):
        """Process file data for filtering"""
        processed = {}
        for file_detail in file_details:
            if 'filename' in file_detail:
                filename = file_detail['filename']
                processed[filename] = {
                    'total_value': file_detail.get('total_value', 0),
                    'values_found': file_detail.get('values_found', 0),
                    'cells': file_detail.get('cell_details', [])
                }
        return processed
    
    def on_section_changed(self):
        """Handle section checkbox changes"""
        self.selected_sections = []
        
        for i in range(self.section_layout.count()):
            widget = self.section_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                self.selected_sections.append(widget.section_data)
        
        # Enable/disable buttons based on selection
        has_selection = len(self.selected_sections) > 0
        self.preview_btn.setEnabled(has_selection)
        self.generate_btn.setEnabled(False)  # Enable only after preview
    
    def preview_analysis(self):
        """Preview the analysis that will be generated"""
        if not getattr(self, 'selected_sections', []):
            return
        
        # Ensure we have a consolidated file to read from
        if not getattr(self, 'consolidated_file_path', None) or not os.path.exists(self.consolidated_file_path):
            self.preview_text.setPlainText("No consolidated Excel file set. Please run consolidation first.")
            return
        
        try:
            # Generate preview data
            self.preview_data = self._generate_preview_data()
            self.update_preview()
            self.generate_btn.setEnabled(True)
            
        except Exception as e:
            self.preview_text.setPlainText(f"Error generating preview: {e}")
    
    def _generate_preview_data(self):
        """Generate preview data for selected sections"""
        if not getattr(self, 'consolidated_file_path', None) or not os.path.exists(self.consolidated_file_path):
            return {}
        wb = openpyxl.load_workbook(self.consolidated_file_path, data_only=True)
        ws = wb.active
        
        preview_data = {}
        
        for section in self.selected_sections:
            section_name = section['name']
            data_range = section['data_range']
            
            # Extract section data
            section_data = self._extract_section_data(ws, section)
            
            # Generate analysis preview
            preview_data[section_name] = {
                'type': section['type'],
                'total_values': len(section_data['numeric_data']),
                'sum_values': sum(section_data['numeric_data']),
                'average': sum(section_data['numeric_data']) / len(section_data['numeric_data']) if section_data['numeric_data'] else 0,
                'categories': section_data['categories'],
                'detailed_categories': section_data.get('detailed_categories', {}),
                'file_breakdown': self._get_file_breakdown_for_section(section)
            }
        
        return preview_data
    
    def _extract_section_data(self, worksheet, section):
        """Extract data from a specific section within its strict boundaries"""
        data_range = section['data_range']
        numeric_data = []
        categories = {}
        detailed_categories = {}
        
        # Use the section boundaries to limit our scan
        section_boundaries = data_range.get('section_boundaries', {})
        end_row = section_boundaries.get('end_row', data_range['end_row'])
        end_col = section_boundaries.get('end_col', data_range['end_col'])
        
        for row in range(data_range['start_row'], min(end_row + 1, data_range['end_row'] + 1)):
            for col in range(data_range['start_col'], min(end_col + 1, data_range['end_col'] + 1)):
                cell = worksheet.cell(row=row, column=col)
                
                # Skip TOTAL cells and similar summary cells
                if cell.value is not None and isinstance(cell.value, str):
                    if any(total_word in str(cell.value).upper() for total_word in ['TOTAL', 'SUM', 'GRAND', 'OVERALL']):
                        continue
                
                if isinstance(cell.value, (int, float)) and cell.value != 0:
                    # Check if this cell is in a TOTAL row or column
                    if self._is_total_cell(worksheet, row, col):
                        continue
                    
                    numeric_data.append(cell.value)
                    
                    # Get context only within this section's boundaries
                    row_context = self._get_section_row_context(worksheet, row, col, data_range['start_row'], end_row)
                    col_context = self._get_section_col_context(worksheet, row, col, data_range['start_col'], end_col)
                    
                    # Create main category from row context
                    if row_context['main']:
                        main_category = row_context['main']
                        categories[main_category] = categories.get(main_category, 0) + cell.value
                        
                        # Create detailed category with subcategory if available
                        if col_context['main']:
                            detailed_key = f"{main_category} - {col_context['main']}"
                            detailed_categories[detailed_key] = detailed_categories.get(detailed_key, 0) + cell.value
                    
                    # Also check if column has grade/level information
                    elif col_context['main']:
                        main_category = col_context['main']
                        categories[main_category] = categories.get(main_category, 0) + cell.value
        
        return {
            'numeric_data': numeric_data,
            'categories': categories,
            'detailed_categories': detailed_categories
        }
    
    def _get_comprehensive_row_context(self, worksheet, row, col):
        """Get comprehensive row context including main category and subcategory"""
        context = {'main': None, 'sub': None, 'full': None}
        
        # Scan left from the current column to find row headers
        row_headers = []
        for check_col in range(max(1, col - 10), col):
            cell = worksheet.cell(row=row, column=check_col)
            if cell.value and isinstance(cell.value, str) and not str(cell.value).replace('.', '').isdigit():
                header = str(cell.value).strip()
                if header and header not in ['TOTAL', 'Total']:
                    row_headers.append(header)
        
        if row_headers:
            # The rightmost (closest) header is usually the main category
            context['main'] = row_headers[-1]
            if len(row_headers) > 1:
                context['sub'] = row_headers[-2] if len(row_headers) > 1 else None
            context['full'] = ' - '.join(row_headers)
        
        return context
    
    def _get_comprehensive_col_context(self, worksheet, row, col):
        """Get comprehensive column context including main category and subcategory"""
        context = {'main': None, 'sub': None, 'full': None}
        
        # Scan up from the current row to find column headers
        col_headers = []
        for check_row in range(max(1, row - 10), row):
            cell = worksheet.cell(row=check_row, column=col)
            if cell.value and isinstance(cell.value, str) and not str(cell.value).replace('.', '').isdigit():
                header = str(cell.value).strip()
                if header and header not in ['TOTAL', 'Total']:
                    col_headers.append(header)
        
        if col_headers:
            # Look for grade patterns in column headers
            grade_headers = []
            level_headers = []
            gender_headers = []
            
            for header in col_headers:
                header_lower = header.lower()
                if any(grade_word in header_lower for grade_word in ['grade', 'level', 'year', 'class']):
                    grade_headers.append(header)
                elif any(level_word in header_lower for level_word in ['elementary', 'secondary', 'senior', 'primary', 'high']):
                    level_headers.append(header)
                elif any(gender_word in header_lower for gender_word in ['male', 'female', 'boy', 'girl']):
                    gender_headers.append(header)
            
            # Prioritize grade/level information over gender
            if grade_headers:
                context['main'] = grade_headers[-1]  # Most specific grade
                if gender_headers:
                    context['sub'] = gender_headers[-1]
            elif level_headers:
                context['main'] = level_headers[-1]
                if gender_headers:
                    context['sub'] = gender_headers[-1]
            elif col_headers:
                context['main'] = col_headers[-1]  # Closest header
            
            context['full'] = ' - '.join(col_headers)
        
        return context
    
    def _get_row_context(self, worksheet, row, col):
        """Get row context for a cell (legacy method)"""
        for check_col in range(max(1, col - 5), col):
            cell = worksheet.cell(row=row, column=check_col)
            if cell.value and isinstance(cell.value, str) and not str(cell.value).isdigit():
                return str(cell.value).strip()
        return None
    
    def _get_col_context(self, worksheet, row, col):
        """Get column context for a cell (legacy method)"""
        for check_row in range(max(1, row - 5), row):
            cell = worksheet.cell(row=check_row, column=col)
            if cell.value and isinstance(cell.value, str) and not str(cell.value).isdigit():
                return str(cell.value).strip()
        return None
    
    def _is_total_cell(self, worksheet, row, col):
        """Check if this cell is in a TOTAL row or column"""
        # Check the row for TOTAL indicators
        for check_col in range(max(1, col - 10), col + 5):
            try:
                cell = worksheet.cell(row=row, column=check_col)
                if cell.value and isinstance(cell.value, str):
                    if any(total_word in str(cell.value).upper() for total_word in ['TOTAL', 'SUM', 'GRAND', 'OVERALL']):
                        return True
            except:
                continue
        
        # Check the column for TOTAL indicators
        for check_row in range(max(1, row - 10), row + 5):
            try:
                cell = worksheet.cell(row=check_row, column=col)
                if cell.value and isinstance(cell.value, str):
                    if any(total_word in str(cell.value).upper() for total_word in ['TOTAL', 'SUM', 'GRAND', 'OVERALL']):
                        return True
            except:
                continue
        
        return False
    
    def _get_section_row_context(self, worksheet, row, col, section_start_row, section_end_row):
        """Get row context only within this section's boundaries"""
        context = {'main': None, 'sub': None, 'full': None}
        
        # Scan left from the current column to find row headers, but only within section
        row_headers = []
        for check_col in range(max(1, col - 10), col):
            cell = worksheet.cell(row=row, column=check_col)
            if cell.value and isinstance(cell.value, str) and not str(cell.value).replace('.', '').isdigit():
                header = str(cell.value).strip()
                if header and not any(total_word in header.upper() for total_word in ['TOTAL', 'SUM', 'GRAND', 'OVERALL']):
                    row_headers.append(header)
        
        if row_headers:
            # The rightmost (closest) header is usually the main category
            context['main'] = row_headers[-1]
            if len(row_headers) > 1:
                context['sub'] = row_headers[-2]
            context['full'] = ' - '.join(row_headers)
        
        return context
    
    def _get_section_col_context(self, worksheet, row, col, section_start_col, section_end_col):
        """Get column context only within this section's boundaries"""
        context = {'main': None, 'sub': None, 'full': None}
        
        # Scan up from the current row to find column headers, but only within reasonable bounds
        col_headers = []
        for check_row in range(max(1, row - 10), row):
            cell = worksheet.cell(row=check_row, column=col)
            if cell.value and isinstance(cell.value, str) and not str(cell.value).replace('.', '').isdigit():
                header = str(cell.value).strip()
                if header and not any(total_word in header.upper() for total_word in ['TOTAL', 'SUM', 'GRAND', 'OVERALL']):
                    col_headers.append(header)
        
        if col_headers:
            # Look for grade patterns in column headers
            grade_headers = []
            level_headers = []
            gender_headers = []
            
            for header in col_headers:
                header_lower = header.lower()
                if any(grade_word in header_lower for grade_word in ['grade', 'level', 'year', 'class']) and not 'non' in header_lower:
                    grade_headers.append(header)
                elif any(level_word in header_lower for level_word in ['elementary', 'secondary', 'senior', 'primary', 'high']):
                    level_headers.append(header)
                elif any(gender_word in header_lower for gender_word in ['male', 'female', 'boy', 'girl']):
                    gender_headers.append(header)
            
            # Prioritize grade/level information over gender
            if grade_headers:
                context['main'] = grade_headers[-1]  # Most specific grade
                if gender_headers:
                    context['sub'] = gender_headers[-1]
            elif level_headers:
                context['main'] = level_headers[-1]
                if gender_headers:
                    context['sub'] = gender_headers[-1]
            elif col_headers:
                context['main'] = col_headers[-1]  # Closest header
            
            context['full'] = ' - '.join(col_headers)
        
        return context
    
    def _get_file_breakdown_for_section(self, section):
        """Get file breakdown for a specific section"""
        file_breakdown = {}
        
        for filename, file_info in self.file_data.items():
            # This would analyze which cells in this section came from which files
            # For now, we'll use the total file data
            file_breakdown[filename] = {
                'value': file_info['total_value'],
                'percentage': 0  # Will be calculated
            }
        
        # Calculate percentages
        total = sum(data['value'] for data in file_breakdown.values())
        if total > 0:
            for data in file_breakdown.values():
                data['percentage'] = (data['value'] / total) * 100
        
        return file_breakdown
    
    def update_preview(self):
        """Update the preview based on current selections and filters"""
        if not getattr(self, 'preview_data', {}):
            self.preview_text.setPlainText("Click 'Preview Analysis' to see what will be generated.")
            return
        
        selected_file = self.file_filter.currentText()
        
        preview_text = "Analysis preview\n" + "="*50 + "\n\n"
        
        for section_name, data in self.preview_data.items():
            preview_text += f"📋 {section_name}\n"
            preview_text += "-" * 30 + "\n"
            preview_text += f"• Total Values: {data['total_values']}\n"
            preview_text += f"• Sum: {data['sum_values']:,.0f}\n"
            preview_text += f"• Average: {data['average']:.2f}\n\n"
            
            # Categories (Main Categories)
            if data['categories']:
                preview_text += "Main categories:\n"
                for category, value in data['categories'].items():
                    preview_text += f"  - {category}: {value:,.0f}\n"
                preview_text += "\n"
            
            # Detailed Categories (with subcategories)
            if data.get('detailed_categories'):
                preview_text += "📋 Detailed Breakdown:\n"
                for detailed_category, value in data['detailed_categories'].items():
                    preview_text += f"  - {detailed_category}: {value:,.0f}\n"
                preview_text += "\n"
            
            # File breakdown
            if selected_file != "All Files" and 'file_breakdown' in data and selected_file in data['file_breakdown']:
                file_data = data['file_breakdown'][selected_file]
                preview_text += f"📂 {selected_file} Contribution:\n"
                preview_text += f"  - Value: {file_data['value']:,.0f}\n"
                preview_text += f"  - Percentage: {file_data['percentage']:.1f}%\n"
            else:
                preview_text += "📂 File Breakdown:\n"
                for filename, file_data in data.get('file_breakdown', {}).items():
                    preview_text += f"  - {filename}: {file_data['value']:,.0f} ({file_data['percentage']:.1f}%)\n"
            
            preview_text += "\n" + "="*50 + "\n\n"
        
        self.preview_text.setPlainText(preview_text)
    
    def generate_analysis(self):
        """Generate the actual analysis sheets (disabled: analysis module removed)"""
        QMessageBox.information(self, "Analysis Disabled",
                                "The AI analysis report module has been removed."
                                "\nPreview is available, but sheet generation is disabled.")
        return

# ---------------- Advanced Configuration Dialog ----------------
class AdvancedConfigDialog(QDialog):
    """Advanced configuration options for consolidation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Consolidation Settings")
        self.setModal(True)
        self.setFixedSize(600, 700)
        
        # Configure tooltip timing globally
        QApplication.instance().setAttribute(Qt.AA_DisableWindowContextHelpButton)
        self.setup_tooltip_timing()
        
        self.init_ui()
    
    def setup_tooltip_timing(self):
        """Configure tooltip display timing"""
        # Set tooltip delay to 1000ms (1 second)
        QApplication.instance().setAttribute(Qt.AA_UseHighDpiPixmaps)
        # Note: PyQt5 doesn't have direct control over tooltip fade timing
        # but we can set the show delay
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Data Processing Tab
        data_tab = self.create_data_processing_tab()
        tabs.addTab(data_tab, "Data Processing")
        
        # File Handling Tab
        file_tab = self.create_file_handling_tab()
        tabs.addTab(file_tab, "File Handling")
        
        # Validation Tab
        validation_tab = self.create_validation_tab()
        tabs.addTab(validation_tab, "Validation")
        
        # Performance Tab
        performance_tab = self.create_performance_tab()
        tabs.addTab(performance_tab, "Performance")
        
        layout.addWidget(tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        # Reset to defaults button
        reset_btn = QPushButton("🔄 Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        reset_btn.setToolTip("Reset all settings to their default values")
        btn_layout.addWidget(reset_btn)
        
        # OK and Cancel buttons
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def create_data_processing_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Data Type Handling
        group = QGroupBox("Data Type Handling")
        group_layout = QVBoxLayout(group)
        
        self.auto_convert_text = QCheckBox("Auto-convert text numbers to numeric")
        self.auto_convert_text.setChecked(True)
        self.auto_convert_text.setToolTip(
            "When ENABLED: Automatically converts text that looks like numbers into actual numbers.\n\n"
            "Examples:\n"
            "• '123' becomes 123\n"
            "• '45.67' becomes 45.67\n"
            "• '1,234' becomes 1234\n\n"
            "When DISABLED: Only processes cells that are already numbers.\n\n"
            "💡 TIP: Keep this enabled unless your data has text that looks like numbers but shouldn't be added."
        )
        group_layout.addWidget(self.auto_convert_text)
        
        self.handle_percentages = QCheckBox("Convert percentages (e.g., '50%' → 0.5)")
        self.handle_percentages.setChecked(True)

# ---------------- Advanced Configuration Dialog ----------------
class AdvancedConfigDialog(QDialog):
    """Advanced configuration options for consolidation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Consolidation Settings")
        self.setModal(True)
        self.setFixedSize(600, 700)
        
        # Configure tooltip timing globally
        QApplication.instance().setAttribute(Qt.AA_DisableWindowContextHelpButton)
        self.setup_tooltip_timing()
        
        self.init_ui()
    
    def setup_tooltip_timing(self):
        """Configure tooltip display timing"""
        # Set tooltip delay to 1000ms (1 second)
        QApplication.instance().setAttribute(Qt.AA_UseHighDpiPixmaps)
        # Note: PyQt5 doesn't have direct control over tooltip fade timing
        # but we can set the show delay
        self.setToolTipDuration(5000)  # Keep tooltip visible for 5 seconds
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Data Processing Tab
        data_tab = self.create_data_processing_tab()
        tabs.addTab(data_tab, "Data Processing")
        
        # File Handling Tab
        file_tab = self.create_file_handling_tab()
        tabs.addTab(file_tab, "File Handling")
        
        # Validation Tab
        validation_tab = self.create_validation_tab()
        tabs.addTab(validation_tab, "Validation")
        
        # Performance Tab
        performance_tab = self.create_performance_tab()
        tabs.addTab(performance_tab, "Performance")
        
        layout.addWidget(tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("Apply settings")
        self.ok_btn.setObjectName("SuccessButton")
        self.ok_btn.setToolTip(
            "Save all your advanced settings and use them for consolidation.\n\n"
            "After clicking this:\n"
            "• Your settings will be remembered\n"
            "• The consolidation will use these settings\n"
            "• The Advanced Settings button will show a ✓ checkmark\n\n"
            "💡 TIP: Review all tabs before applying!"
        )
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("TertiaryButton")
        self.cancel_btn.setToolTip(
            "Close the Advanced Settings without saving any changes.\n\n"
            "When you click this:\n"
            "• All changes are discarded\n"
            "• Previous settings remain unchanged\n"
            "• Consolidation will use default or previous settings\n\n"
            "💡 TIP: Use this if you changed something by mistake."
        )
        
        self.reset_btn = QPushButton("Reset to defaults")
        self.reset_btn.setObjectName("DangerButton")
        self.reset_btn.setToolTip(
            "Reset ALL settings back to their original default values.\n\n"
            "This will:\n"
            "• Clear all custom settings\n"
            "• Restore factory defaults\n"
            "• Work like a fresh installation\n\n"
            "⚠️ WARNING: This cannot be undone! Make sure this is what you want."
        )
        
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.ok_btn)
        
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        
        layout.addLayout(btn_layout)
    
    def create_data_processing_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Data Type Handling
        group = QGroupBox("Data Type Handling")
        group_layout = QVBoxLayout(group)
        
        self.auto_convert_text = QCheckBox("Auto-convert text numbers to numeric")
        self.auto_convert_text.setChecked(True)
        self.auto_convert_text.setToolTip(
            "When ENABLED: Automatically converts text that looks like numbers into actual numbers.\n\n"
            "Examples:\n"
            "• '123' becomes 123\n"
            "• '45.67' becomes 45.67\n"
            "• '1,234' becomes 1234\n\n"
            "When DISABLED: Only processes cells that are already numbers.\n\n"
            "💡 TIP: Keep this enabled unless your data has text that looks like numbers but shouldn't be added."
        )
        group_layout.addWidget(self.auto_convert_text)
        
        self.handle_percentages = QCheckBox("Convert percentages (e.g., '50%' → 0.5)")
        self.handle_percentages.setChecked(True)
        self.handle_percentages.setToolTip(
            "When ENABLED: Converts percentage text into decimal numbers.\n\n"
            "Examples:\n"
            "• '50%' becomes 0.5\n"
            "• '100%' becomes 1.0\n"
            "• '25%' becomes 0.25\n\n"
            "When DISABLED: Treats percentage symbols as text and ignores them.\n\n"
            "💡 TIP: Enable this if your Excel files contain percentage values as text."
        )
        group_layout.addWidget(self.handle_percentages)
        
        self.handle_currency = QCheckBox("Strip currency symbols (e.g., '$100' → 100)")
        self.handle_currency.setChecked(True)
        self.handle_currency.setToolTip(
            "When ENABLED: Removes currency symbols and converts to numbers.\n\n"
            "Examples:\n"
            "• '$100' becomes 100\n"
            "• '$1,500.50' becomes 1500.50\n"
            "• '€250' becomes 250\n\n"
            "When DISABLED: Treats currency symbols as text and ignores them.\n\n"
            "💡 TIP: Enable this if your Excel files have money amounts with $ or other currency symbols."
        )
        group_layout.addWidget(self.handle_currency)
        
        self.ignore_formulas = QCheckBox("Ignore cells with formulas (use calculated values only)")
        self.ignore_formulas.setChecked(True)
        self.ignore_formulas.setToolTip(
            "When ENABLED: Uses the calculated result of formulas, not the formula itself.\n\n"
            "Example:\n"
            "• Cell contains '=A1+B1' and shows '50'\n"
            "• System will use 50 (the result)\n\n"
            "When DISABLED: Tries to process the formula text as data.\n\n"
            "💡 TIP: Keep this enabled! You want the calculated values, not the formula text."
        )
        group_layout.addWidget(self.ignore_formulas)
        
        layout.addWidget(group)
        
        # Cell Range Selection
        range_group = QGroupBox("Cell Range Selection")
        range_layout = QVBoxLayout(range_group)
        
        self.use_custom_range = QCheckBox("Use custom cell range")
        self.use_custom_range.setToolTip(
            "When ENABLED: Only processes cells within the specified range.\n\n"
            "When DISABLED: Processes ALL cells in each Excel file.\n\n"
            "Examples of custom ranges:\n"
            "• 'A1:D10' - processes cells from A1 to D10\n"
            "• 'B2:F50' - processes cells from B2 to F50\n"
            "• 'A1:A100' - processes only column A, rows 1 to 100\n\n"
            "💡 TIP: Use this when you only want to consolidate specific areas of your spreadsheets."
        )
        range_layout.addWidget(self.use_custom_range)
        
        range_input_layout = QHBoxLayout()
        range_label = QLabel("Range:")
        range_label.setToolTip(
            "Enter the cell range you want to process.\n\n"
            "Format: StartCell:EndCell\n\n"
            "Examples:\n"
            "• A1:Z100 (columns A to Z, rows 1 to 100)\n"
            "• B5:H25 (columns B to H, rows 5 to 25)\n"
            "• A1:A1000 (only column A, rows 1 to 1000)\n\n"
            "💡 TIP: Make sure this range covers all the data you want to consolidate!"
        )
        range_input_layout.addWidget(range_label)
        
        self.range_input = QLineEdit("A1:Z100")
        self.range_input.setEnabled(False)
        self.range_input.setToolTip(
            "Type the exact cell range you want to consolidate.\n\n"
            "Must be in Excel format: StartCell:EndCell\n\n"
            "Examples:\n"
            "• A1:Z100 - processes a large area\n"
            "• B2:E20 - processes a smaller specific area\n"
            "• A1:A1000 - processes only one column\n\n"
            "⚠️ WARNING: Only cells within this range will be included in the consolidation!"
        )
        range_input_layout.addWidget(self.range_input)
        range_layout.addLayout(range_input_layout)
        
        self.use_custom_range.toggled.connect(self.range_input.setEnabled)
        
        layout.addWidget(range_group)
        
        layout.addStretch()
        return widget
    
    def create_file_handling_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # File Format Support
        format_group = QGroupBox("File Format Support")
        format_layout = QVBoxLayout(format_group)
        
        self.support_xlsx = QCheckBox("Excel 2007+ (.xlsx)")
        self.support_xlsx.setChecked(True)
        self.support_xlsx.setEnabled(False)  # Always enabled
        self.support_xlsx.setToolTip(
            "Excel 2007+ format (.xlsx files) - ALWAYS ENABLED\n\n"
            "This is the main Excel format used by:\n"
            "• Excel 2007 and newer\n"
            "• Most modern spreadsheet programs\n\n"
            "These files usually contain:\n"
            "• Advanced formatting\n"
            "• Multiple worksheets\n"
            "• Charts and images\n\n"
            "💡 INFO: This cannot be disabled because it's the primary format."
        )
        format_layout.addWidget(self.support_xlsx)
        
        self.support_xls = QCheckBox("Legacy Excel (.xls)")
        self.support_xls.setChecked(True)
        self.support_xls.setToolTip(
            "When ENABLED: Also processes older Excel files (.xls format).\n\n"
            "Legacy Excel format is used by:\n"
            "• Excel 97-2003\n"
            "• Some older business systems\n"
            "• Files created many years ago\n\n"
            "When DISABLED: Only processes modern .xlsx files.\n\n"
            "💡 TIP: Enable this if you have old Excel files mixed with new ones."
        )
        format_layout.addWidget(self.support_xls)
        
        self.support_csv = QCheckBox("CSV files (.csv)")
        self.support_csv.setChecked(True)
        self.support_csv.setToolTip(
            "When ENABLED: Also processes CSV (comma-separated values) files.\n\n"
            "CSV files are:\n"
            "• Simple text files with data separated by commas\n"
            "• Can be opened in Excel\n"
            "• Often exported from databases or other systems\n"
            "• Have no formatting, just pure data\n\n"
            "When DISABLED: Only processes Excel files.\n\n"
            "💡 TIP: Enable this if you have data exported as CSV files that need to be included."
        )
        format_layout.addWidget(self.support_csv)
        
        layout.addWidget(format_group)
        
        # Duplicate Handling
        dup_group = QGroupBox("Duplicate File Handling")
        dup_layout = QVBoxLayout(dup_group)
        
        self.duplicate_action = QComboBox()
        self.duplicate_action.addItems([
            "Skip duplicates",
            "Include all duplicates",
            "Use newest file",
            "Use largest file",
            "Prompt for each duplicate"
        ])
        self.duplicate_action.setToolTip(
            "Choose what happens when files with the same name are found:\n\n"
            "• SKIP DUPLICATES: Use only the first file found, ignore others\n"
            "• INCLUDE ALL: Process all files, even if they have the same name\n"
            "• USE NEWEST: Choose the file that was modified most recently\n"
            "• USE LARGEST: Choose the file with the biggest file size\n"
            "• PROMPT FOR EACH: Ask you to choose for every duplicate found\n\n"
            "💡 TIP: 'Use newest file' is usually the best choice for updated data."
        )
        
        dup_label = QLabel("When duplicate files are found:")
        dup_label.setToolTip(
            "Duplicate files are files that have the exact same filename.\n\n"
            "This commonly happens when:\n"
            "• Files are copied to multiple folders\n"
            "• Backup copies exist\n"
            "• Different versions of the same file exist\n\n"
            "Choose how to handle these situations."
        )
        dup_layout.addWidget(dup_label)
        dup_layout.addWidget(self.duplicate_action)
        
        layout.addWidget(dup_group)
        
        # File Filtering
        filter_group = QGroupBox("File Filtering")
        filter_layout = QVBoxLayout(filter_group)
        
        self.enable_name_filter = QCheckBox("Filter by filename pattern")
        self.enable_name_filter.setToolTip(
            "When ENABLED: Only processes files that match a specific name pattern.\n\n"
            "When DISABLED: Processes ALL files in the folder.\n\n"
            "Examples of useful patterns:\n"
            "• 'Sales_*.xlsx' - only files starting with 'Sales_'\n"
            "• '*_2024.xlsx' - only files ending with '_2024'\n"
            "• 'Report*.xlsx' - only files starting with 'Report'\n\n"
            "💡 TIP: Use this to exclude files you don't want to consolidate."
        )
        filter_layout.addWidget(self.enable_name_filter)
        
        name_filter_layout = QHBoxLayout()
        pattern_label = QLabel("Pattern:")
        pattern_label.setToolTip(
            "Enter a pattern to match filenames.\n\n"
            "Use * as a wildcard (matches anything):\n"
            "• '*.xlsx' - all Excel files\n"
            "• 'Sales_*' - files starting with 'Sales_'\n"
            "• '*_report.xlsx' - files ending with '_report.xlsx'\n"
            "• 'Q1_*_2024.xlsx' - specific pattern matching\n\n"
            "💡 TIP: Test your pattern with a few files first!"
        )
        name_filter_layout.addWidget(pattern_label)
        
        self.name_filter_pattern = QLineEdit("*.xlsx")
        self.name_filter_pattern.setEnabled(False)
        self.name_filter_pattern.setToolTip(
            "Type the filename pattern here.\n\n"
            "Wildcard rules:\n"
            "• * = matches any text\n"
            "• ? = matches any single character\n\n"
            "Examples:\n"
            "• '*.xlsx' matches: file1.xlsx, data.xlsx, report.xlsx\n"
            "• 'Sales_*' matches: Sales_Jan.xlsx, Sales_Q1.xlsx\n"
            "• '*_2024.xlsx' matches: Report_2024.xlsx, Data_2024.xlsx\n\n"
            "⚠️ WARNING: Only files matching this pattern will be processed!"
        )
        name_filter_layout.addWidget(self.name_filter_pattern)
        filter_layout.addLayout(name_filter_layout)
        
        self.enable_name_filter.toggled.connect(self.name_filter_pattern.setEnabled)
        
        # Date filtering
        self.enable_date_filter = QCheckBox("Filter by modification date")
        self.enable_date_filter.setToolTip(
            "When ENABLED: Only processes files that were modified recently.\n\n"
            "When DISABLED: Processes files regardless of when they were last changed.\n\n"
            "This is useful for:\n"
            "• Processing only today's files\n"
            "• Ignoring old, outdated files\n"
            "• Focusing on recent data only\n\n"
            "💡 TIP: Use this if you have a folder with both new and old files, but only want the recent ones."
        )
        filter_layout.addWidget(self.enable_date_filter)
        
        date_layout = QHBoxLayout()
        days_label = QLabel("Days ago:")
        days_label.setToolTip(
            "How many days back to look for files.\n\n"
            "Examples:\n"
            "• 1 day = only files from today\n"
            "• 7 days = files from the last week\n"
            "• 30 days = files from the last month\n"
            "• 365 days = files from the last year\n\n"
            "The system checks when each file was last modified."
        )
        date_layout.addWidget(days_label)
        
        self.date_filter_days = QSpinBox()
        self.date_filter_days.setRange(1, 365)
        self.date_filter_days.setValue(30)
        self.date_filter_days.setEnabled(False)
        self.date_filter_days.setToolTip(
            "Enter the number of days to look back.\n\n"
            "Examples:\n"
            "• 1 = only files modified today\n"
            "• 7 = files modified in the last week\n"
            "• 30 = files modified in the last month\n\n"
            "Range: 1 to 365 days\n\n"
            "💡 TIP: Start with 30 days and adjust based on your needs."
        )
        date_layout.addWidget(self.date_filter_days)
        filter_layout.addLayout(date_layout)
        
        self.enable_date_filter.toggled.connect(self.date_filter_days.setEnabled)
        
        layout.addWidget(filter_group)
        
        layout.addStretch()
        return widget
    
    def create_validation_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Data Validation
        validation_group = QGroupBox("Data Validation")
        validation_layout = QVBoxLayout(validation_group)
        
        self.validate_structure = QCheckBox("Validate file structure consistency")
        self.validate_structure.setChecked(True)
        self.validate_structure.setToolTip(
            "When ENABLED: Checks that all Excel files have similar structure.\n\n"
            "This validation checks:\n"
            "• All files have the same worksheet names\n"
            "• Data appears in similar cell locations\n"
            "• Files have compatible layouts\n\n"
            "When DISABLED: Processes files without structure checking.\n\n"
            "💡 TIP: Keep this enabled to catch files that don't match your template."
        )
        validation_layout.addWidget(self.validate_structure)
        
        self.validate_data_types = QCheckBox("Validate data types")
        self.validate_data_types.setChecked(True)
        self.validate_data_types.setToolTip(
            "When ENABLED: Checks that cell values are the expected type (numbers, text, etc.).\n\n"
            "This validation catches:\n"
            "• Text in cells that should contain numbers\n"
            "• Unexpected data formats\n"
            "• Conversion issues\n\n"
            "When DISABLED: Accepts any data type without checking.\n\n"
            "💡 TIP: Keep this enabled to catch data quality issues early."
        )
        validation_layout.addWidget(self.validate_data_types)
        
        self.validate_ranges = QCheckBox("Validate value ranges")
        self.validate_ranges.setToolTip(
            "When ENABLED: Checks that numbers fall within acceptable ranges.\n\n"
            "This validation catches:\n"
            "• Numbers that are too large or too small\n"
            "• Potential data entry errors\n"
            "• Outliers that might be mistakes\n\n"
            "When DISABLED: Accepts any numeric value.\n\n"
            "💡 TIP: Enable this if you know your data should be within specific limits."
        )
        validation_layout.addWidget(self.validate_ranges)
        
        # Range validation settings
        range_layout = QHBoxLayout()
        
        min_label = QLabel("Min value:")
        min_label.setToolTip(
            "The smallest acceptable number.\n\n"
            "Any number smaller than this will be flagged as invalid.\n\n"
            "Examples:\n"
            "• 0 = no negative numbers allowed\n"
            "• -1000 = allows negative numbers down to -1000\n"
            "• 1 = only positive numbers allowed\n\n"
            "💡 TIP: Set this based on what makes sense for your data."
        )
        range_layout.addWidget(min_label)
        
        self.min_value = QDoubleSpinBox()
        self.min_value.setRange(-999999, 999999)
        self.min_value.setValue(-1000)
        self.min_value.setEnabled(False)
        self.min_value.setToolTip(
            "Enter the minimum acceptable value.\n\n"
            "Any number below this will be considered invalid.\n\n"
            "Range: -999,999 to 999,999\n\n"
            "Examples for different data types:\n"
            "• Sales amounts: 0 (no negative sales)\n"
            "• Temperature: -100 (reasonable low temperature)\n"
            "• Percentages: 0 (no negative percentages)\n"
            "• General data: -1000 (reasonable lower bound)"
        )
        range_layout.addWidget(self.min_value)
        
        max_label = QLabel("Max value:")
        max_label.setToolTip(
            "The largest acceptable number.\n\n"
            "Any number larger than this will be flagged as invalid.\n\n"
            "Examples:\n"
            "• 1000000 = allows numbers up to 1 million\n"
            "• 100 = for percentage data (0-100%)\n"
            "• 999999 = very large upper bound\n\n"
            "💡 TIP: Set this based on the maximum reasonable value for your data."
        )
        range_layout.addWidget(max_label)
        
        self.max_value = QDoubleSpinBox()
        self.max_value.setRange(-999999, 999999)
        self.max_value.setValue(1000000)
        self.max_value.setEnabled(False)
        self.max_value.setToolTip(
            "Enter the maximum acceptable value.\n\n"
            "Any number above this will be considered invalid.\n\n"
            "Range: -999,999 to 999,999\n\n"
            "Examples for different data types:\n"
            "• Sales amounts: 1000000 (1 million max)\n"
            "• Percentages: 100 (maximum 100%)\n"
            "• Counts: 9999 (reasonable upper limit)\n"
            "• General data: 1000000 (reasonable upper bound)"
        )
        range_layout.addWidget(self.max_value)
        
        validation_layout.addLayout(range_layout)
        
        self.validate_ranges.toggled.connect(self.min_value.setEnabled)
        self.validate_ranges.toggled.connect(self.max_value.setEnabled)
        
        layout.addWidget(validation_group)
        
        # Error Handling
        error_group = QGroupBox("Error Handling")
        error_layout = QVBoxLayout(error_group)
        
        self.stop_on_error = QRadioButton("Stop processing on first error")
        self.stop_on_error.setToolTip(
            "When SELECTED: Stops the entire consolidation as soon as any error is found.\n\n"
            "Use this when:\n"
            "• You want to fix errors immediately\n"
            "• Data quality is critical\n"
            "• You prefer to address issues before continuing\n\n"
            "⚠️ WARNING: If there are many errors, you'll need to fix them one by one."
        )
        
        self.continue_on_error = QRadioButton("Continue processing and report errors")
        self.continue_on_error.setChecked(True)
        self.continue_on_error.setToolTip(
            "When SELECTED: Continues processing all files even if errors are found.\n\n"
            "Benefits:\n"
            "• Processes as much data as possible\n"
            "• Shows all errors at once in the report\n"
            "• Saves time by not stopping for each error\n\n"
            "💡 TIP: This is usually the better choice - you can review all issues together."
        )
        
        error_layout.addWidget(self.stop_on_error)
        error_layout.addWidget(self.continue_on_error)
        
        layout.addWidget(error_group)
        
        layout.addStretch()
        return widget
    
    def create_performance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Performance Settings
        perf_group = QGroupBox("Performance Optimization")
        perf_layout = QVBoxLayout(perf_group)
        
        self.enable_parallel = QCheckBox("Enable parallel processing")
        self.enable_parallel.setChecked(True)
        self.enable_parallel.setToolTip(
            "When ENABLED: Processes multiple files at the same time for faster speed.\n\n"
            "Benefits:\n"
            "• Much faster processing with many files\n"
            "• Better use of your computer's power\n"
            "• Especially helpful with 10+ files\n\n"
            "When DISABLED: Processes files one at a time.\n\n"
            "💡 TIP: Keep this enabled unless you have a very old computer."
        )
        perf_layout.addWidget(self.enable_parallel)
        
        thread_layout = QHBoxLayout()
        thread_label = QLabel("Max threads:")
        thread_label.setToolTip(
            "How many files to process at the same time.\n\n"
            "Guidelines:\n"
            "• 2-4 threads: Good for most computers\n"
            "• 4-8 threads: Good for modern computers\n"
            "• 8+ threads: Only for powerful computers\n\n"
            "💡 TIP: Higher numbers aren't always better - try 4 first."
        )
        thread_layout.addWidget(thread_label)
        
        self.max_threads = QSpinBox()
        self.max_threads.setRange(1, 16)
        self.max_threads.setValue(4)
        self.max_threads.setEnabled(True)
        self.max_threads.setToolTip(
            "Number of files to process simultaneously.\n\n"
            "Range: 1 to 16 threads\n\n"
            "Recommendations by computer type:\n"
            "• Older computer: 2 threads\n"
            "• Average computer: 4 threads\n"
            "• Fast computer: 6-8 threads\n"
            "• Very powerful computer: 8+ threads\n\n"
            "⚠️ WARNING: Too many threads can actually slow things down!"
        )
        thread_layout.addWidget(self.max_threads)
        perf_layout.addLayout(thread_layout)
        
        self.enable_parallel.toggled.connect(self.max_threads.setEnabled)
        
        self.memory_optimization = QCheckBox("Memory optimization for large files")
        self.memory_optimization.setChecked(True)
        self.memory_optimization.setToolTip(
            "When ENABLED: Uses special techniques to handle large Excel files without using too much memory.\n\n"
            "Benefits:\n"
            "• Can process very large files (100MB+)\n"
            "• Prevents 'out of memory' errors\n"
            "• Keeps your computer responsive\n\n"
            "When DISABLED: Loads entire files into memory (faster but uses more RAM).\n\n"
            "💡 TIP: Keep this enabled if you work with large Excel files."
        )
        perf_layout.addWidget(self.memory_optimization)
        
        layout.addWidget(perf_group)
        
        # Backup Settings
        backup_group = QGroupBox("Backup & Recovery")
        backup_layout = QVBoxLayout(backup_group)
        
        self.create_backup = QCheckBox("Create backup before consolidation")
        self.create_backup.setChecked(True)
        self.create_backup.setToolTip(
            "When ENABLED: Automatically saves a copy of your consolidated file before overwriting it.\n\n"
            "Benefits:\n"
            "• Protects against data loss\n"
            "• Allows you to recover previous versions\n"
            "• Peace of mind when processing important data\n\n"
            "When DISABLED: No backup is created (not recommended).\n\n"
            "💡 TIP: Always keep this enabled for safety!"
        )
        backup_layout.addWidget(self.create_backup)
        
        self.keep_backups = QCheckBox("Keep historical backups")
        self.keep_backups.setChecked(True)
        self.keep_backups.setToolTip(
            "When ENABLED: Saves multiple backup files over time.\n\n"
            "Benefits:\n"
            "• Access to previous consolidations\n"
            "• Compare results from different dates\n"
            "• Extra protection against mistakes\n\n"
            "When DISABLED: Only keeps the most recent backup.\n\n"
            "💡 TIP: Enable this if you consolidate the same files regularly."
        )
        backup_layout.addWidget(self.keep_backups)
        
        backup_count_layout = QHBoxLayout()
        backup_label = QLabel("Max backups to keep:")
        backup_label.setToolTip(
            "How many backup files to save before deleting old ones.\n\n"
            "Examples:\n"
            "• 5 backups = last 5 consolidations\n"
            "• 10 backups = last 10 consolidations\n"
            "• 20 backups = last 20 consolidations\n\n"
            "Old backups are automatically deleted to save disk space."
        )
        backup_count_layout.addWidget(backup_label)
        
        self.max_backups = QSpinBox()
        self.max_backups.setRange(1, 50)
        self.max_backups.setValue(10)
        self.max_backups.setEnabled(True)
        self.max_backups.setToolTip(
            "Number of backup files to keep.\n\n"
            "Range: 1 to 50 backups\n\n"
            "Recommended values:\n"
            "• 5 backups = good for occasional use\n"
            "• 10 backups = good for regular use (default)\n"
            "• 20+ backups = for frequent consolidations\n\n"
            "💡 TIP: 10 backups is usually enough for most people."
        )
        backup_count_layout.addWidget(self.max_backups)
        backup_layout.addLayout(backup_count_layout)
        
        self.keep_backups.toggled.connect(self.max_backups.setEnabled)
        
        layout.addWidget(backup_group)
        
        layout.addStretch()
        return widget
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        # Data Processing
        self.auto_convert_text.setChecked(True)
        self.handle_percentages.setChecked(True)
        self.handle_currency.setChecked(True)
        self.ignore_formulas.setChecked(True)
        self.use_custom_range.setChecked(False)
        self.range_input.setText("A1:Z100")
        
        # File Handling
        self.support_xls.setChecked(True)
        self.support_csv.setChecked(True)
        self.duplicate_action.setCurrentIndex(0)
        self.enable_name_filter.setChecked(False)
        self.name_filter_pattern.setText("*.xlsx")
        self.enable_date_filter.setChecked(False)
        self.date_filter_days.setValue(30)
        
        # Validation
        self.validate_structure.setChecked(True)
        self.validate_data_types.setChecked(True)
        self.validate_ranges.setChecked(False)
        self.min_value.setValue(-1000)
        self.max_value.setValue(1000000)
        self.continue_on_error.setChecked(True)
        
        # Performance
        self.enable_parallel.setChecked(True)
        self.max_threads.setValue(4)
        self.memory_optimization.setChecked(True)
        self.create_backup.setChecked(True)
        self.keep_backups.setChecked(True)
        self.max_backups.setValue(10)
    
    def get_settings(self):
        """Get all current settings as dictionary"""
        return {
            'data_processing': {
                'auto_convert_text': self.auto_convert_text.isChecked(),
                'handle_percentages': self.handle_percentages.isChecked(),
                'handle_currency': self.handle_currency.isChecked(),
                'ignore_formulas': self.ignore_formulas.isChecked(),
                'use_custom_range': self.use_custom_range.isChecked(),
                'custom_range': self.range_input.text()
            },
            'file_handling': {
                'support_xls': self.support_xls.isChecked(),
                'support_csv': self.support_csv.isChecked(),
                'duplicate_action': self.duplicate_action.currentIndex(),
                'enable_name_filter': self.enable_name_filter.isChecked(),
                'name_filter_pattern': self.name_filter_pattern.text(),
                'enable_date_filter': self.enable_date_filter.isChecked(),
                'date_filter_days': self.date_filter_days.value()
            },
            'validation': {
                'validate_structure': self.validate_structure.isChecked(),
                'validate_data_types': self.validate_data_types.isChecked(),
                'validate_ranges': self.validate_ranges.isChecked(),
                'min_value': self.min_value.value(),
                'max_value': self.max_value.value(),
                'stop_on_error': self.stop_on_error.isChecked()
            },
            'performance': {
                'enable_parallel': self.enable_parallel.isChecked(),
                'max_threads': self.max_threads.value(),
                'memory_optimization': self.memory_optimization.isChecked(),
                'create_backup': self.create_backup.isChecked(),
                'keep_backups': self.keep_backups.isChecked(),
                'max_backups': self.max_backups.value()
            }
        }
# ---------------- Modern Loading Dialog ----------------
class ModernLoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing...")
        self.setModal(True)
        self.setFixedSize(400, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        
        # Loading icon
        self.loading_label = QLabel()
        self.loading_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.loading_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("⏳ Consolidating Excel files, please wait...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Files processed list
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(80)
        layout.addWidget(self.file_list)
        
        self.setStyleSheet("""
            QDialog { background-color: #deeaee; }
            QLabel { color: #111827; font-size: 14px; background: transparent; }
            QProgressBar {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                text-align: center;
                background-color: #ffffff;
                height: 18px;
            }
            QProgressBar::chunk { background-color: #10b981; border-radius: 8px; }
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def add_processed_file(self, filename):
        self.file_list.addItem(f"✓ {filename}")
        self.file_list.scrollToBottom()


# ---------------- Minimal Consolidation Worker (restored) ----------------
class ConsolidationWorker(QThread):
    finished = pyqtSignal(str, str)  # (status, message)
    progress = pyqtSignal(int)
    file_processed = pyqtSignal(str)

    def __init__(self, template_path, excel_folder, save_folder, settings=None, error_reporter=None):
        super().__init__()
        self.template_path = template_path
        self.excel_folder = excel_folder
        self.save_folder = save_folder
        self.settings = settings or {}
        self.error_reporter = error_reporter

    def _get_user_friendly_error_message(self, error):
        """Convert technical errors into user-friendly messages with guidance."""
        error_str = str(error).lower()
        
        # File access errors
        if "permission denied" in error_str or "access denied" in error_str:
            return ("File Access Denied\n\n"
                   "The application cannot access one or more files. This usually happens when:\n"
                   "• Files are open in Excel or another program\n"
                   "• Files are in a read-only location\n"
                   "• Insufficient permissions to the folder\n\n"
                   "Solution: Close all Excel files and ensure you have write permissions to the folder.")
        
        # File format errors
        elif "badzipfile" in error_str or "zipfile" in error_str:
            return ("Corrupted Excel File\n\n"
                   "One or more Excel files appear to be corrupted or not valid Excel files.\n\n"
                   "Solution: Try opening the problematic files in Excel first to repair them, "
                   "or exclude them from consolidation.")
        
        # Memory errors
        elif "memory" in error_str or "out of memory" in error_str:
            return ("Insufficient Memory\n\n"
                   "The files are too large or numerous to process with available memory.\n\n"
                   "Solution: Try processing fewer files at once, or close other applications to free up memory.")
        
        # Template errors
        elif "template" in error_str or "workbook" in error_str:
            return ("Template File Issue\n\n"
                   "There's a problem with the template file. It may be:\n"
                   "• Corrupted or not a valid Excel file\n"
                   "• Protected with a password\n"
                   "• In an unsupported format\n\n"
                   "Solution: Use a different template file or create a new one.")
        
        # Merged cell errors (already handled, but just in case)
        elif "mergedcell" in error_str or "read only" in error_str:
            return ("Merged Cell Conflict\n\n"
                   "The template contains merged cells that conflict with the consolidation process.\n\n"
                   "Solution: Unmerge cells in the template file before consolidation.")
        
        # Network/path errors
        elif "no such file" in error_str or "file not found" in error_str:
            return ("File Not Found\n\n"
                   "One or more files specified in the consolidation could not be found.\n\n"
                   "Solution: Check that all source files still exist and the folder path is correct.")
        
        # Generic fallback with the original error for debugging
        else:
            return (f"Consolidation Error\n\n"
                   f"An unexpected error occurred during processing:\n\n"
                   f"Technical details: {str(error)}\n\n"
                   f"Common solutions:\n"
                   f"• Ensure all Excel files are closed\n"
                   f"• Check that files are not corrupted\n"
                   f"• Verify you have write permissions to the output folder\n"
                   f"• Try with a smaller set of files first")

    def _get_file_error_message(self, file_path, error):
        """Get user-friendly error message for individual file processing errors."""
        error_str = str(error).lower()
        filename = os.path.basename(file_path)
        
        # File access errors
        if "permission denied" in error_str or "access denied" in error_str:
            return f"File '{filename}' is open in Excel or locked by another program. Please close it and try again."
        
        # File format errors
        elif "badzipfile" in error_str or "zipfile" in error_str:
            return f"File '{filename}' is corrupted or not a valid Excel file. Please repair or exclude it."
        
        # Template structure errors
        elif "template" in error_str or "structure" in error_str:
            return f"File '{filename}' has a different structure than the template. Please check the file format."
        
        # Memory errors
        elif "memory" in error_str:
            return f"File '{filename}' is too large to process. Try closing other applications or exclude this file."
        
        # Generic file error
        else:
            return f"File '{filename}' could not be processed: {str(error)}"

    def _get_template_load_error_message(self, error):
        """Get user-friendly error message for template loading errors."""
        error_str = str(error).lower()
        filename = os.path.basename(self.template_path)
        
        # Password protected files
        if "password" in error_str or "encrypted" in error_str:
            return (f"Password Protected Template\n\n"
                   f"The template file '{filename}' is password protected.\n\n"
                   f"Solution: Remove the password from the template file before using it.")
        
        # Corrupted template
        elif "badzipfile" in error_str or "zipfile" in error_str:
            return (f"Corrupted Template File\n\n"
                   f"The template file '{filename}' appears to be corrupted.\n\n"
                   f"Solution: Try opening the file in Excel to repair it, or use a different template.")
        
        # File format issues
        elif "invalid" in error_str or "format" in error_str:
            return (f"Invalid Template Format\n\n"
                   f"The template file '{filename}' is not a valid Excel file.\n\n"
                   f"Solution: Ensure the file is a .xlsx or .xlsm file created by Excel.")
        
        # Permission issues
        elif "permission" in error_str or "access" in error_str:
            return (f"Template Access Denied\n\n"
                   f"Cannot access the template file '{filename}'.\n\n"
                   f"Solution: Ensure the file is not open in Excel and you have read permissions.")
        
        # Generic template error
        else:
            return (f"Template Loading Error\n\n"
                   f"Could not load the template file '{filename}'.\n\n"
                   f"Technical details: {str(error)}\n\n"
                   f"Solution: Try opening the file in Excel first to ensure it's valid.")

    def _get_save_error_message(self, error, output_path):
        """Get user-friendly error message for file saving errors."""
        error_str = str(error).lower()
        filename = os.path.basename(output_path)
        folder = os.path.dirname(output_path)
        
        # Permission denied
        if "permission denied" in error_str or "access denied" in error_str:
            return (f"Cannot Save File\n\n"
                   f"Permission denied when trying to save '{filename}' to:\n"
                   f"'{folder}'\n\n"
                   f"Solution: Ensure you have write permissions to the output folder.")
        
        # File in use
        elif "being used" in error_str or "in use" in error_str:
            return (f"File Currently Open\n\n"
                   f"The file '{filename}' is currently open in Excel or another program.\n\n"
                   f"Solution: Close the file in Excel and try again.")
        
        # Disk space
        elif "no space" in error_str or "disk full" in error_str:
            return (f"Insufficient Disk Space\n\n"
                   f"Not enough disk space to save the consolidated file.\n\n"
                   f"Solution: Free up disk space or choose a different output folder.")
        
        # Path too long
        elif "path too long" in error_str or "filename too long" in error_str:
            return (f"Path Too Long\n\n"
                   f"The file path is too long for the system to handle.\n\n"
                   f"Solution: Choose a shorter folder path or filename.")
        
        # Generic save error
        else:
            return (f"Save Error\n\n"
                   f"Could not save the consolidated file '{filename}'.\n\n"
                   f"Technical details: {str(error)}\n\n"
                   f"Solution: Check that the output folder exists and you have write permissions.")

    def run(self):
        try:
            self.progress.emit(5)
            if not os.path.exists(self.template_path):
                error_msg = (f"Template File Not Found\n\n"
                           f"The template file could not be found at:\n"
                           f"'{self.template_path}'\n\n"
                           f"Please check:\n"
                           f"• The file path is correct\n"
                           f"• The file still exists\n"
                           f"• You have permission to access the file\n"
                           f"• The file is not currently open in Excel")
                self.finished.emit("error", error_msg)
                return

            template_ext = os.path.splitext(self.template_path)[1].lower()
            keep_vba = template_ext == '.xlsm'
            try:
                output_wb = openpyxl.load_workbook(self.template_path, keep_vba=keep_vba)
                output_ws = output_wb.active
            except Exception as e:
                # Report error to Google Sheets if error reporter is available
                if self.error_reporter:
                    try:
                        self.error_reporter.report_error(
                            type(e), e, e.__traceback__,
                            triggered_by="Template Loading in ConsolidationWorker",
                            user_file=self.template_path
                        )
                    except Exception:
                        pass  # Don't let error reporting failure stop the process
                
                error_msg = self._get_template_load_error_message(e)
                self.finished.emit("error", error_msg)
                return

            # Collect source files per advanced settings
            try:
                from advanced_settings import list_source_files, load_cells, normalize_value, validate_value, ensure_backup
            except Exception as e:
                # Advanced settings module not available - use basic functionality
                list_source_files = None
                load_cells = None
                normalize_value = None
                validate_value = None
                ensure_backup = None
                print(f"Advanced settings module not available: {e}")

            if list_source_files is not None:
                files = list_source_files(self.excel_folder, self.settings)
            else:
                pattern = os.path.join(self.excel_folder, "*.xlsx")
                files = [f for f in glob.glob(pattern) if not os.path.basename(f).startswith("~$")]
            if not files:
                error_msg = ("No Excel Files Found\n\n"
                           f"No valid Excel files (.xlsx) were found in the folder:\n"
                           f"'{self.excel_folder}'\n\n"
                           f"Please check:\n"
                           f"• The folder path is correct\n"
                           f"• The folder contains .xlsx files\n"
                           f"• Files are not hidden or in subfolders\n"
                           f"• Files are not currently open in Excel")
                self.finished.emit("error", error_msg)
                return

            totals = {}
            # coord -> { filename_no_ext: contribution_value }
            contributions = {}
            validate_structure = bool(self.settings.get('validation', {}).get('validate_structure'))
            validate_data_types = bool(self.settings.get('validation', {}).get('validate_data_types'))
            stop_on_error = bool(self.settings.get('validation', {}).get('stop_on_error'))

            # Template reference for structure validation
            template_ws = None
            if validate_structure:
                try:
                    template_ws = openpyxl.load_workbook(self.template_path, data_only=True, read_only=True).active
                except Exception:
                    template_ws = None
            for idx, file in enumerate(files, 1):
                try:
                    # Dispatch by extension; handle xlsx/xls/csv
                    ext = os.path.splitext(file)[1].lower()
                    file_label = os.path.splitext(os.path.basename(file))[0]

                    if ext in ('.xlsx', '.xls'):
                        wb = openpyxl.load_workbook(file, data_only=True, read_only=bool(self.settings.get('performance', {}).get('memory_optimization')))
                        ws = wb.active
                        # Validate structure against template if enabled
                        if validate_structure and template_ws is not None:
                            try:
                                if (ws.max_row != template_ws.max_row) or (ws.max_column != template_ws.max_column):
                                    if stop_on_error:
                                        wb.close()
                                        filename = os.path.basename(file)
                                        error_msg = (f"File Structure Mismatch\n\n"
                                                   f"File '{filename}' has a different structure than the template:\n\n"
                                                   f"Template: {template_ws.max_row} rows × {template_ws.max_column} columns\n"
                                                   f"File: {ws.max_row} rows × {ws.max_column} columns\n\n"
                                                   f"Solution: Ensure all files have the same structure as the template, "
                                                   f"or disable structure validation in settings.")
                                        self.finished.emit("error", error_msg)
                                        return
                                    wb.close()
                                    self.file_processed.emit(os.path.basename(file))
                                    continue
                            except Exception:
                                pass
                        # Iterate cells with optional range and ignore_formulas
                        if load_cells is not None:
                            cells_iter = load_cells(ws, self.settings)
                        else:
                            cells_iter = (cell for row in ws.iter_rows() for cell in row)

                        for cell in cells_iter:
                            value = cell.value
                            if normalize_value is not None:
                                val = normalize_value(value, self.settings)
                            else:
                                val = float(value) if isinstance(value, (int, float)) else None
                            if val is None:
                                # If data-type validation is on and raw is not empty, treat as error/skip
                                if validate_data_types and (cell.value not in (None, "")):
                                    if stop_on_error:
                                        wb.close()
                                        filename = os.path.basename(file)
                                        error_msg = (f"Non-Numeric Data Found\n\n"
                                                   f"Cell {cell.coordinate} in file '{filename}' contains non-numeric data:\n"
                                                   f"'{cell.value}'\n\n"
                                                   f"This conflicts with data type validation settings.\n\n"
                                                   f"Solution: Either:\n"
                                                   f"• Convert the data to numbers in the source file\n"
                                                   f"• Disable data type validation in settings\n"
                                                   f"• Use a different template that allows text data")
                                        self.finished.emit("error", error_msg)
                                        return
                                    # continue_on_error -> skip cell
                                    continue
                                continue
                            if validate_value is not None and not validate_value(val, self.settings):
                                if self.settings.get('validation', {}).get('stop_on_error'):
                                    wb.close()
                                    filename = os.path.basename(file)
                                    error_msg = (f"Data Validation Error\n\n"
                                               f"Value {val} at cell {cell.coordinate} in file '{filename}' "
                                               f"is outside the allowed range.\n\n"
                                               f"Please check the data in this file or adjust the validation settings.")
                                    self.finished.emit("error", error_msg)
                                    return
                                continue
                            coord = cell.coordinate
                            totals[coord] = totals.get(coord, 0) + val
                            if coord not in contributions:
                                contributions[coord] = {}
                            contributions[coord][file_label] = contributions[coord].get(file_label, 0.0) + val
                        wb.close()
                    elif ext == '.csv':
                        # CSV support removed; skip file but report as processed
                        self.file_processed.emit(os.path.basename(file))
                        continue
                    self.file_processed.emit(os.path.basename(file))
                except Exception as e:
                    # Skip problematic files but continue
                    error_msg = self._get_file_error_message(file, e)
                    print(f"Error processing {file}: {error_msg}")
                    
                    # Report error to Google Sheets if error reporter is available
                    try:
                        # Try to get the error reporter from the main application
                        from google_sheets_reporter import GoogleSheetsErrorReporter
                        error_reporter = GoogleSheetsErrorReporter("1.0.0")
                        error_reporter.report_error(
                            type(e), e, e.__traceback__,
                            triggered_by="File Processing in ConsolidationWorker",
                            user_file=file
                        )
                    except Exception:
                        # If error reporting fails, just continue
                        pass

                self.progress.emit(5 + int(idx / max(len(files), 1) * 80))

            # Write totals to output
            from openpyxl.comments import Comment
            from openpyxl.styles import Border, Side
            thin_orange = Border(
                left=Side(style='thin', color='FF8C00'),
                right=Side(style='thin', color='FF8C00'),
                top=Side(style='thin', color='FF8C00'),
                bottom=Side(style='thin', color='FF8C00')
            )

            for coord, value in totals.items():
                cell = output_ws[coord]
                # Check if cell is a MergedCell (read-only) before modifying
                if isinstance(cell, MergedCell):
                    # Skip merged cells as they have read-only attributes
                    continue
                
                cell.value = value
                # Add hover comment listing contributing filenames
                file_map = contributions.get(coord, {})
                if file_map:
                    # Build professional, aligned text block
                    items = sorted(file_map.items(), key=lambda x: x[0].lower())
                    max_name = max((len(n) for n, _ in items), default=4)
                    header = "Consolidation Summary\n"
                    header += f"Cell: {coord}\n"
                    header += f"Total: {value:,.2f}\n\n"
                    header += "Contributors (file  |  value)\n"
                    header += "-" * (max(26, max_name + 10)) + "\n"
                    lines = []
                    for name, v in items:
                        pad = " " * (max_name - len(name))
                        lines.append(f"{name}{pad}  |  {v:,.2f}")
                    body = "\n".join(lines)
                    comment_text = header + body
                    # Excel comments are limited (~32,767 chars). Truncate safely if needed.
                    max_len = 32000
                    if len(comment_text) > max_len:
                        comment_text = comment_text[: max_len - 21] + "\n... (truncated)"
                    comment = Comment(comment_text, "Excel Consolidator")
                    # Size hint
                    # Cap size to encourage Excel to add scrollbars for long content
                    comment.width = min(520, 200 + max_name * 7)
                    comment.height = min(600, 140 + len(items) * 14)
                    cell.comment = comment
                    # Visual indicator border
                    cell.border = thin_orange


            self.progress.emit(90)
            os.makedirs(self.save_folder, exist_ok=True)
            date_str = datetime.now().strftime("%b %d %Y")
            output_name = f"Consolidated - {date_str}.xlsm" if keep_vba else f"Consolidated - {date_str}.xlsx"
            output_path = os.path.join(self.save_folder, output_name)
            
            # Optional: add Contributions sheet with simple search/filter
            try:
                contrib_ws = output_wb.create_sheet("Contributions")
                contrib_ws["A1"] = "CONTRIBUTIONS INDEX"
                contrib_ws["A1"].font = Font(bold=True, size=14, color="2F5597")
                contrib_ws.merge_cells('A1:D1')
                contrib_ws["A3"] = "Search (use column filters):"
                contrib_ws["A5"] = "Cell"
                contrib_ws["B5"] = "File Name"
                contrib_ws["C5"] = "Contribution"
                # Fill rows with per-file contributions
                r = 6
                coord_to_first_row = {}
                for coord, file_map in contributions.items():
                    for fname, v in file_map.items():
                        contrib_ws[f"A{r}"] = coord
                        contrib_ws[f"B{r}"] = fname
                        contrib_ws[f"C{r}"] = v
                        if coord not in coord_to_first_row:
                            coord_to_first_row[coord] = r
                        r += 1
                # Add autofilter over the table
                if r > 6:
                    contrib_ws.auto_filter.ref = f"A5:C{r-1}"
                # Set widths
                contrib_ws.column_dimensions['A'].width = 12
                contrib_ws.column_dimensions['B'].width = 40
                contrib_ws.column_dimensions['C'].width = 16
                # Add hyperlinks from consolidated cells to their first row in Contributions
                try:
                    for coord in totals.keys():
                        first_row = coord_to_first_row.get(coord)
                        if first_row:
                            cell = output_ws[coord]
                            # Check if cell is a MergedCell (read-only) before modifying
                            if isinstance(cell, MergedCell):
                                # Skip merged cells as they have read-only attributes
                                continue
                            
                            link = f"#'Contributions'!A{first_row}"
                            cell.hyperlink = link
                            # Optional tooltip
                            cell.hyperlink.tooltip = "Click to view full contributions"
                except Exception:
                    pass
            except Exception as _e:
                # Non-fatal if we cannot add the sheet
                pass

            # Optionally create/rotate backups before overwriting
            backup_target = None
            if ensure_backup is not None:
                backup_target = ensure_backup(self.save_folder, self.settings, os.path.basename(output_path))
            try:
                output_wb.save(output_path)
            except Exception as e:
                error_msg = self._get_save_error_message(e, output_path)
                self.finished.emit("error", error_msg)
                return
            if backup_target:
                try:
                    # Copy the freshly saved consolidated file to backup target
                    import shutil
                    shutil.copy2(output_path, backup_target)
                except Exception:
                    pass
            self.progress.emit(100)
            # Send both consolidated path and optional audit placeholder (None)
            self.finished.emit("success", output_path)
        except Exception as e:
            error_message = self._get_user_friendly_error_message(e)
            self.finished.emit("error", error_message)

def _num_to_col_name(n):
    """Convert 1-based index to Excel column name (1->A, 27->AA)."""
    name = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        name = chr(65 + rem) + name
    return name

# ---------------- Main App ----------------
class ExcelProcessorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setGeometry(400, 200, 900, 650)
        
        # Update icon loading to use resource_path
        icon_path = self.resource_path("assets/icons/app.ico")
        self.setWindowIcon(QIcon(icon_path))

        self.template_path = None
        self.excel_folder = None
        self.save_folder = None
        self.advanced_settings = None
        
        # Initialize error reporting and auto-update systems
        self.error_reporter = None
        self.auto_updater = None
        self.setup_error_reporting_and_updates()

        # Apply modern style
        self.apply_modern_style()
        self.initUI()

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
    
    def setup_error_reporting_and_updates(self):
        """
        Setup error reporting and auto-update systems.
        """
        try:
            # Setup error reporting
            if ERROR_REPORTING_ENABLED:
                self.error_reporter, _ = setup_google_sheets_error_reporting(APP_VERSION)
                if self.error_reporter:
                    print("Google Sheets error reporting system initialized successfully")
                else:
                    print("Warning: Google Sheets error reporting system failed to initialize")
            
            # Setup auto-updater
            if AUTO_UPDATE_ENABLED:
                self.auto_updater = setup_auto_updater(APP_VERSION, GITHUB_OWNER, GITHUB_REPO)
                if self.auto_updater:
                    print("Auto-update system initialized successfully")
                    # Start background update checker
                    self.auto_updater.start_background_checker()
                    # Check for updates on startup (but don't show notification immediately)
                    self.check_for_updates_on_startup()
                else:
                    print("Warning: Auto-update system failed to initialize")
                    
        except Exception as e:
            print(f"Warning: Failed to setup error reporting and auto-update systems: {e}")
    
    def check_for_updates_on_startup(self):
        """
        Check for updates when the application starts (silent check).
        """
        try:
            if self.auto_updater:
                # Just check for updates silently - background checker will handle the rest
                self.auto_updater.check_for_updates()
                # Don't show notification immediately - let background process handle updates
        except Exception as e:
            print(f"Error checking for updates on startup: {e}")
    
    def show_update_notification(self):
        """
        Show a user-friendly notification about available updates.
        """
        try:
            if self.auto_updater and self.auto_updater.update_available:
                update_info = self.auto_updater.get_update_info()
                message = (f"An update is available!\n\n"
                          f"Current version: {update_info['current_version']}\n"
                          f"Latest version: {update_info['latest_version']}\n\n"
                          f"The update will be downloaded and installed automatically.")
                
                QMessageBox.information(
                    self, 
                    "Update Available", 
                    message
                )
        except Exception as e:
            print(f"Error showing update notification: {e}")
    
    def closeEvent(self, event):
        """
        Handle application close event.
        """
        try:
            # Stop background update checker
            if self.auto_updater:
                self.auto_updater.stop_background_checker()
                print("Auto-updater background checker stopped")
        except Exception as e:
            print(f"Error stopping auto-updater: {e}")
        
        # Accept the close event
        event.accept()
    
    def report_error_with_context(self, exc_type, exc_value, exc_traceback, triggered_by="Unknown", user_file=None):
        """
        Report an error with additional context.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
            triggered_by: What triggered the error
            user_file: Path to user file if available
        """
        try:
            if self.error_reporter:
                self.error_reporter.report_error(exc_type, exc_value, exc_traceback, triggered_by, user_file)
                
                # Show user-friendly message
                QMessageBox.information(
                    self,
                    "Error Reported",
                    self.error_reporter.get_user_friendly_message()
                )
        except Exception as e:
            print(f"Error reporting failed: {e}")

    def apply_modern_style(self):
        check_svg = self.resource_path("assets/icons/check.svg").replace("\\", "/")
        check_disabled_svg = self.resource_path("assets/icons/check_disabled.svg").replace("\\", "/")
        css = """
            /* Base */
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #1f2937; /* slate-800 */
            }
            QMainWindow, QWidget, QDialog {
                background-color: #deeaee; /* requested background */
            }
            /* Dialog text widgets should inherit group box white background */
            QDialog QLabel, QDialog QCheckBox, QDialog QRadioButton {
                background: transparent;
            }
            /* Read-only rich text areas in dialogs should be white */
            QDialog QTextEdit[readOnly="true"] {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }

            /* Headings */
            QLabel#HeaderTitle { color: #0f766e; } /* teal-700 */
            QLabel#HeaderSubtitle { color: #6b7280; } /* gray-500 */

            /* Buttons - default */
            QPushButton {
                border: 1px solid #e5e7eb; /* gray-200 */
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f5f7fb);
                color: #111827; /* gray-900 */
                border-radius: 8px;
                padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #eef2ff; /* indigo-50 */
                border-color: #c7d2fe; /* indigo-200 */
            }
            QPushButton:pressed {
                background-color: #e0e7ff; /* indigo-100 */
            }
            QPushButton:disabled {
                background-color: #f3f4f6;
                color: #9ca3af;
                border-color: #e5e7eb;
            }

            /* Group boxes */
            QGroupBox {
                font-weight: 600;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 22px; /* lower the floating title slightly */
                background: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 2px 6px; /* add slight top padding to lower text */
                color: #0f766e; /* match title color */
                background: transparent; /* transparent label background */
            }

            /* Inputs */
            QLineEdit, QComboBox, QTextEdit, QSpinBox, QDoubleSpinBox {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 8px 10px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus,
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #34d399; /* emerald-400 */
                outline: none;
            }

            /* Spin boxes: align button area with rounded input */
            QAbstractSpinBox {
                padding-right: 30px; /* space for buttons */
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
            QAbstractSpinBox::up-button,
            QAbstractSpinBox::down-button {
                subcontrol-origin: border;
                width: 28px;
                background: #ffffff;
                border-left: 1px solid #e5e7eb;
                margin: 0;
            }
            QAbstractSpinBox::up-button {
                subcontrol-position: right top;
                border-top-right-radius: 8px;
            }
            QAbstractSpinBox::down-button {
                subcontrol-position: right bottom;
                border-bottom-right-radius: 8px;
            }
            QAbstractSpinBox::up-button:hover,
            QAbstractSpinBox::down-button:hover { background: #f9fafb; }

            /* Tabs */
            QTabWidget::pane { border: 1px solid #e5e7eb; border-radius: 10px; }
            QTabBar::tab {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                padding: 8px 14px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }
            QTabBar::tab:selected { color: #0f766e; border-bottom: 2px solid #10b981; }
            QTabBar::tab:hover { background: #f8fafc; }

            /* Lists */
            QListWidget {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }

            /* Progress */
            QProgressBar {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                text-align: center;
                background-color: #ffffff;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #10b981; /* emerald-500 */
                border-radius: 8px;
            }

            /* Splitter */
            QSplitter { border: none; }
            QSplitter::handle { background: #edf2f7; width: 6px; }
            QSplitter::handle:hover { background: #e2e8f0; }

            /* Tooltips */
            QToolTip {
                background-color: #111827; /* gray-900 */
                color: #f9fafb; /* gray-50 */
                border: 1px solid #111827;
                padding: 6px 8px;
                border-radius: 6px;
                font-size: 12px;
            }

            /* Checkboxes and Radios */
            QCheckBox::indicator {
                width: 12px; height: 12px;
                border-radius: 6px;
                border: 2px solid #15803d; /* green-700 */
                background: #ffffff; /* white box */
            }
            QCheckBox::indicator:hover { border-color: #16a34a; }
            QCheckBox::indicator:checked {
                background: #ffffff; /* keep white like reference */
                border: 2px solid #15803d;
                image: url(./resources/check.svg);
            }
            QCheckBox::indicator:disabled {
                border-color: #e5e7eb;
                background: #f3f4f6;
                image: url(./resources/check_disabled.svg);
            }

            QRadioButton::indicator {
                width: 16px; height: 16px;
                border-radius: 8px;
                border: 2px solid #d1d5db;
                background: #ffffff;
            }
            QRadioButton::indicator:checked {
                border: 6px solid #16a34a; /* inner dot via border */
            }

            /* Button variants via objectName */
            QPushButton#PrimaryButton { background: #0ea5e9; color: white; border: 1px solid #0ea5e9; }
            QPushButton#PrimaryButton:hover { background: #0284c7; border-color: #0284c7; }
            QPushButton#SuccessButton { background: #10b981; color: white; border: 1px solid #10b981; }
            QPushButton#SuccessButton:hover { background: #059669; border-color: #059669; }
            QPushButton#DangerButton { background: #ef4444; color: white; border: 1px solid #ef4444; }
            QPushButton#DangerButton:hover { background: #dc2626; border-color: #dc2626; }
            QPushButton#TertiaryButton { background: #ffffff; color: #111827; border: 1px solid #e5e7eb; }
            QPushButton#TertiaryButton:hover { background: #f9fafb; }
        """
        css = css.replace("./resources/check.svg", check_svg)
        css = css.replace("./resources/check_disabled.svg", check_disabled_svg)
        self.setStyleSheet(css)

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Add watermark
        watermark = QLabel("© 2025 Izak. All rights reserved.", self)
        watermark.setStyleSheet("""
            QLabel {
                color: rgba(0, 0, 0, 0.2);
                font-size: 12px;
                font-style: italic;
            }
        """)
        watermark.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        watermark.setGeometry(0, 0, 200, 30)  # Initial geometry
        # Make sure watermark stays in bottom-right corner when window is resized
        def updateWatermarkPos():
            watermark.move(self.width() - watermark.width() - 20, 
                         self.height() - watermark.height() - 5)
        self.resizeEvent = lambda e: updateWatermarkPos()

        # Header with logo and title
        header_frame = QFrame()
        header_frame.setObjectName("AppHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 14, 20, 12)
        header_layout.setSpacing(16)
                
        # Update resource paths to work both in development and when bundled
        def resource_path(relative_path):
            try:
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)

        # Logo with actual image
        logo_label = QLabel()
        logo_path = self.resource_path("assets/icons/logo.png")
        logo_pixmap = QPixmap(logo_path)
        # Ensure high-quality scaling and HiDPI usage
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        scaled_pixmap = logo_pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)

        logo_label.setFixedSize(100, 100)
        logo_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(logo_label)
        
        # Title and subtitle
        title_container = QVBoxLayout()
        title_container.setContentsMargins(0, 0, 0, 0)
        title_container.setSpacing(2)
        title = QLabel("Excel Consolidator")
        title.setObjectName("HeaderTitle")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet("color: #0f766e;")
        subtitle = QLabel("Sum values from multiple Excel files while preserving formatting")
        subtitle.setObjectName("HeaderSubtitle")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: #6b7280;")
        title_container.addWidget(title)
        title_container.addWidget(subtitle)
        header_layout.addLayout(title_container)
        header_layout.setAlignment(title_container, Qt.AlignVCenter | Qt.AlignLeft)
        
        header_layout.addStretch()
        main_layout.addWidget(header_frame)
        # subtle separator under header
        header_sep = QFrame()
        header_sep.setObjectName("Separator")
        header_sep.setFixedHeight(1)
        main_layout.addWidget(header_sep)

        # Main content area
        content_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Steps
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 4, 8, 8)
        left_layout.setSpacing(12)
        
        # Step 1: Select Template
        template_group = QGroupBox("Step 1: Select Template File")
        template_group.setStyleSheet("QGroupBox::title{background:transparent;color:#0f766e;}")
        template_layout = QVBoxLayout()
        template_layout.setContentsMargins(12, 12, 12, 12)
        template_layout.setSpacing(10)
        self.template_btn = QPushButton("📄 Browse Template File")
        self.template_btn.setObjectName("TertiaryButton")
        self.template_btn.clicked.connect(self.open_template_file)
        self.template_label = QLabel("No template selected")
        self.template_label.setWordWrap(True)
        self.template_label.setStyleSheet("color: #0f766e; background: transparent; padding: 0; border-radius: 0;")
        template_layout.addWidget(self.template_btn)
        template_layout.addWidget(self.template_label)
        template_group.setLayout(template_layout)
        left_layout.addWidget(template_group)

        # Step 2: Select Excel Folder
        folder_group = QGroupBox("Step 2: Select Excel Folder")
        folder_group.setStyleSheet("QGroupBox::title{background:transparent;color:#0f766e;}")
        folder_layout = QVBoxLayout()
        folder_layout.setContentsMargins(12, 12, 12, 12)
        folder_layout.setSpacing(10)
        self.folder_btn = QPushButton("📂 Browse Excel Folder")
        self._style_button(self.folder_btn, "#388E3C")
        self.folder_btn.clicked.connect(self.open_excel_folder)
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setWordWrap(True)
        self.folder_label.setStyleSheet("color: #0f766e; background: transparent; padding: 0; border-radius: 0;")
        folder_layout.addWidget(self.folder_btn)
        folder_layout.addWidget(self.folder_label)
        folder_group.setLayout(folder_layout)
        left_layout.addWidget(folder_group)

        # Step 3: Select Save Folder
        save_group = QGroupBox("Step 3: Select Save Location")
        save_group.setStyleSheet("QGroupBox::title{background:transparent;color:#0f766e;}")
        save_layout = QVBoxLayout()
        save_layout.setContentsMargins(12, 12, 12, 12)
        save_layout.setSpacing(10)
        self.save_btn = QPushButton("💾 Browse Save Location")
        self._style_button(self.save_btn, "#D32F2F")
        self.save_btn.clicked.connect(self.open_save_folder)
        self.save_label = QLabel("No save location selected")
        self.save_label.setWordWrap(True)
        self.save_label.setStyleSheet("color: #0f766e; background: transparent; padding: 0; border-radius: 0;")
        save_layout.addWidget(self.save_btn)
        save_layout.addWidget(self.save_label)
        save_group.setLayout(save_layout)
        left_layout.addWidget(save_group)

        # Step 4: Advanced Settings and Run
        settings_run_layout = QVBoxLayout()
        
        # Advanced Settings Button
        self.advanced_btn = QPushButton("⚙️ Advanced Settings")
        self.advanced_btn.setObjectName("TertiaryButton")
        self.advanced_btn.clicked.connect(self.open_advanced_settings)
        settings_run_layout.addWidget(self.advanced_btn)
        
        # Run Button
        self.run_btn = QPushButton("🚀 Run Consolidation")
        self.run_btn.setObjectName("SuccessButton")
        self.run_btn.clicked.connect(self.run_processing)
        settings_run_layout.addWidget(self.run_btn)
        
        left_layout.addLayout(settings_run_layout)
        
        left_layout.addStretch()
        content_splitter.addWidget(left_widget)
        
        # Right panel - Info and Preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 4, 8, 8)
        right_layout.setSpacing(12)
        
        # Info box
        info_group = QGroupBox("Information")
        info_group.setStyleSheet("QGroupBox::title{background:transparent;color:#0f766e;}")
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(10)
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setHtml("""
            <h3>About Excel Consolidator</h3>
            <p>This tool helps you sum values from multiple Excel files while preserving all formatting from your template.</p>
            <h4>Core Features:</h4>
            <ul>
                <li>Sums numeric values from multiple Excel files</li>
                <li>Preserves colors, fonts, borders, and cell formatting</li>
                <li>Maintains column widths and row heights</li>
                <li>Handles merged cells correctly</li>
                <li>Shows real-time progress</li>
            </ul>
            <h4>Advanced Features:</h4>
            <ul>
                <li><b>Advanced settings</b> for maximum flexibility</li>
                <li>Multi-format support (XLSX, XLS, CSV)</li>
                <li>Smart data validation & conversion</li>
                <li>Duplicate file detection & handling</li>
                <li>Performance optimization options</li>
                <li>Automatic backup & recovery</li>
            </ul>
            <h4>Interactive Verification:</h4>
            <ul>
                <li><b>Hover over any cell</b> to see breakdown</li>
                <li>Excel comments show file contributions</li>
                <li>Visual indicators for consolidated cells</li>
            </ul>
            <h4>Verification & Quality:</h4>
            <ul>
                <li><b>Interactive comments</b> - Hover over cells to see breakdown</li>
                <li><b>Audit reports</b> - Complete traceability of all data</li>
                <li><b>Visual indicators</b> - Orange borders on consolidated cells</li>
                <li><b>Quality checks</b> - Data validation and error detection</li>
                <li><b>Backup system</b> - Automatic file protection</li>
            </ul>
            <h4>Instructions:</h4>
            <ol>
                <li>Select a template Excel file with your desired formatting</li>
                <li>Choose a folder containing Excel files to consolidate</li>
                <li>Select where to save the consolidated file</li>
                <li><b>Optional:</b> Configure Advanced Settings for custom behavior</li>
                <li>Click "Run Consolidation" to process</li>
                <li>Review the audit report for complete verification</li>
            </ol>
        """)
        info_text.setMaximumHeight(300)
        info_layout.addWidget(info_text)
        info_group.setLayout(info_layout)
        right_layout.addWidget(info_group)
        
        # Stats box
        stats_group = QGroupBox("Statistics")
        stats_group.setStyleSheet("QGroupBox::title{background:transparent;color:#0f766e;}")
        stats_layout = QVBoxLayout()
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(10)
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setHtml("""
            <p>No operations performed yet.</p>
        """)
        stats_layout.addWidget(self.stats_text)
        stats_group.setLayout(stats_layout)
        right_layout.addWidget(stats_group)
        
        right_layout.addStretch()
        content_splitter.addWidget(right_widget)
        
        # Set initial sizes for the splitter
        content_splitter.setSizes([420, 520])
        content_splitter.setStyleSheet("""
            QSplitter { border: none; }
            QSplitter::handle { background: #edf2f7; width: 6px; }
            QSplitter::handle:hover { background: #e2e8f0; }
        """)
        main_layout.addWidget(content_splitter)

        self.setLayout(main_layout)

    def _style_button(self, button, color, is_primary=False):
        if is_primary:
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 15px;
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    background-color: {self._adjust_color(color, -20)};
                }}
                QPushButton:pressed {{
                    background-color: {self._adjust_color(color, -40)};
                }}
                QPushButton:disabled {{
                    background-color: #cccccc;
                    color: #888888;
                }}
            """)
        else:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    color: #333;
                    font-size: 14px;
                    padding: 12px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """)

    def _adjust_color(self, color, amount):
        """Adjust hex color by amount (-255 to 255)"""
        if color.startswith('#'):
            color = color[1:]
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(max(0, min(255, c + amount)) for c in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    # ---------------- Actions ----------------
    def open_template_file(self):
        try:
            file, _ = QFileDialog.getOpenFileName(self, "Select Excel Template", "", "Excel Files (*.xlsx *.xls)")
            if file:
                self.template_path = file
                self.template_label.setText(f"📄 {os.path.basename(file)}")
                self.template_label.setStyleSheet("color: #0f766e; background: transparent; padding: 0; border-radius: 0;")
                self.update_stats()
        except Exception as e:
            self.report_error_with_context(
                type(e), e, e.__traceback__, 
                triggered_by="Open Template File Button",
                user_file=file if 'file' in locals() else None
            )

    def open_excel_folder(self):
        try:
            folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Excel Files")
            if folder:
                self.excel_folder = folder
                files = [f for f in os.listdir(folder) if f.endswith(".xlsx") and not f.startswith("~$")]
                self.folder_label.setText(f"📂 {os.path.basename(folder)}\n({len(files)} Excel files found)")
                self.folder_label.setStyleSheet("color: #0f766e; background: transparent; padding: 0; border-radius: 0;")
                self.update_stats()
        except Exception as e:
            self.report_error_with_context(
                type(e), e, e.__traceback__, 
                triggered_by="Open Excel Folder Button",
                user_file=folder if 'folder' in locals() else None
            )

    def open_save_folder(self):
        try:
            folder = QFileDialog.getExistingDirectory(self, "Select Save Folder")
            if folder:
                self.save_folder = folder
                self.save_label.setText(f"💾 {os.path.basename(folder)}")
                self.save_label.setStyleSheet("color: #0f766e; background: transparent; padding: 0; border-radius: 0;")
                self.update_stats()
        except Exception as e:
            self.report_error_with_context(
                type(e), e, e.__traceback__, 
                triggered_by="Open Save Folder Button",
                user_file=folder if 'folder' in locals() else None
            )

    def update_stats(self):
        stats_html = "<h3>Current Selection</h3>"
        
        if self.template_path:
            stats_html += f"<p>📄 Template: <b>{os.path.basename(self.template_path)}</b></p>"
        else:
            stats_html += "<p>📄 Template: <span style='color: #D32F2F;'>Not selected</span></p>"
            
        if self.excel_folder:
            files = [f for f in os.listdir(self.excel_folder) if f.endswith(".xlsx") and not f.startswith("~$")]
            stats_html += f"<p>📂 Source Folder: <b>{os.path.basename(self.excel_folder)}</b> ({len(files)} files)</p>"
        else:
            stats_html += "<p>📂 Source Folder: <span style='color: #D32F2F;'>Not selected</span></p>"
            
        if self.save_folder:
            stats_html += f"<p>💾 Save Location: <b>{os.path.basename(self.save_folder)}</b></p>"
        else:
            stats_html += "<p>💾 Save Location: <span style='color: #D32F2F;'>Not selected</span></p>"
            
        self.stats_text.setHtml(stats_html)

    def open_advanced_settings(self):
        """Open advanced settings dialog"""
        dialog = AdvancedConfigDialog(self)
        
        # If we have previous settings, apply them
        if self.advanced_settings:
            # Apply previous settings to dialog (would need methods to set values)
            pass
        
        if dialog.exec_() == QDialog.Accepted:
            self.advanced_settings = dialog.get_settings()
            
            # Update UI to show advanced settings are configured
            self.advanced_btn.setText("Advanced Settings")
            self.advanced_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
            self.advanced_btn.setObjectName("SuccessButton")
            
            # Show summary of settings in stats
            self.update_stats_with_settings()

    def update_stats_with_settings(self):
        """Update stats display to show current advanced settings"""
        if self.advanced_settings:
            stats_html = "<h3>Current Selection</h3>"
            
            if self.template_path:
                stats_html += f"<p>📄 Template: <b>{os.path.basename(self.template_path)}</b></p>"
            else:
                stats_html += "<p>📄 Template: <span style='color: #D32F2F;'>Not selected</span></p>"
                
            if self.excel_folder:
                files = [f for f in os.listdir(self.excel_folder) if f.endswith(".xlsx") and not f.startswith("~$")]
                stats_html += f"<p>📂 Source Folder: <b>{os.path.basename(self.excel_folder)}</b> ({len(files)} files)</p>"
            else:
                stats_html += "<p>📂 Source Folder: <span style='color: #D32F2F;'>Not selected</span></p>"
                
            if self.save_folder:
                stats_html += f"<p>💾 Save Location: <b>{os.path.basename(self.save_folder)}</b></p>"
            else:
                stats_html += "<p>💾 Save Location: <span style='color: #D32F2F;'>Not selected</span></p>"
            
            # Add advanced settings summary
            stats_html += "<hr><h4>Advanced Settings Active</h4>"
            
            # File format support
            formats = []
            if self.advanced_settings['file_handling']['support_xls']:
                formats.append("XLS")
            if self.advanced_settings['file_handling']['support_csv']:
                formats.append("CSV")
            formats.append("XLSX")  # Always supported
            stats_html += f"<p>📊 Formats: {', '.join(formats)}</p>"
            
            # Data processing
            if self.advanced_settings['data_processing']['auto_convert_text']:
                stats_html += "<p>🔄 Auto-convert text numbers: Enabled</p>"
            
            # Validation
            validations = []
            if self.advanced_settings['validation']['validate_structure']:
                validations.append("Structure")
            if self.advanced_settings['validation']['validate_data_types']:
                validations.append("Data Types")
            if self.advanced_settings['validation']['validate_ranges']:
                validations.append("Value Ranges")
            
            if validations:
                stats_html += f"<p>✅ Validation: {', '.join(validations)}</p>"
            
            # Backup
            if self.advanced_settings['performance']['create_backup']:
                stats_html += "<p>💾 Backup: Enabled</p>"
                
            self.stats_text.setHtml(stats_html)
        else:
            self.update_stats()

    def run_processing(self):
        try:
            if not self.template_path or not self.excel_folder or not self.save_folder:
                missing_items = []
                if not self.template_path:
                    missing_items.append("• Select a template file")
                if not self.excel_folder:
                    missing_items.append("• Choose source folder with Excel files")
                if not self.save_folder:
                    missing_items.append("• Choose output folder for consolidated file")
                
                QMessageBox.warning(self, "Missing Information", 
                                   f"Please complete all required steps before running consolidation:\n\n"
                                   f"{chr(10).join(missing_items)}\n\n"
                                   f"All three steps are required for the consolidation to work properly.")
                return

            # Disable run button during processing
            self.run_btn.setEnabled(False)

            # Modern loading dialog
            self.loading_dialog = ModernLoadingDialog(self)
            
            # Start background worker with advanced settings
            worker_cls = globals().get('ConsolidationWorker')
            if worker_cls is None:
                self.loading_dialog.close()
                self.run_btn.setEnabled(True)
                QMessageBox.information(self, "Processing Disabled",
                                        "The consolidation worker was removed from this build,"
                                        " so processing cannot run.")
                return
            
            self.worker = worker_cls(
                self.template_path, 
                self.excel_folder, 
                self.save_folder, 
                self.advanced_settings,
                self.error_reporter
            )
            self.worker.progress.connect(self.loading_dialog.update_progress)
            self.worker.file_processed.connect(self.loading_dialog.add_processed_file)
            self.worker.finished.connect(self.on_finished)
            self.worker.start()
            
            self.loading_dialog.exec_()
            
        except Exception as e:
            # Report error with context
            self.report_error_with_context(
                type(e), e, e.__traceback__, 
                triggered_by="Run Processing Button",
                user_file=self.template_path if self.template_path else None
            )
            # Re-enable button
            if hasattr(self, 'run_btn'):
                self.run_btn.setEnabled(True)
            # Close dialog if open
            if hasattr(self, 'loading_dialog'):
                self.loading_dialog.close()

    def on_finished(self, status, message):
        self.loading_dialog.close()
        self.run_btn.setEnabled(True)
        
        if status == "success":
            # Parse the message to get file paths
            paths = message.split("|")
            consolidated_path = paths[0]
            audit_path = paths[1] if len(paths) > 1 else None
            
            # Success message with a professional dialog
            success_dialog = QDialog(self)
            success_dialog.setWindowTitle("Consolidation complete")
            success_dialog.setModal(True)
            success_dialog.setFixedSize(560, 340)
            success_dialog.setWindowFlags(success_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)

            # Dialog-wide styling
            success_dialog.setStyleSheet(
                """
                QDialog { background: #ffffff; }
                QLabel#HeaderTitle { font-size: 16px; font-weight: 600; color: #1b5e20; }
                QLabel#BodyText { font-size: 12px; color: #2c2c2c; }
                QFrame#HeaderBar { background-color: #E8F5E9; border-radius: 6px; }
                QFrame#Separator { background-color: #e0e0e0; max-height: 1px; min-height: 1px; }
                QPushButton[primary="true"] {
                    background-color: #2e7d32; color: #ffffff; font-weight: 600; padding: 8px 14px; border-radius: 6px; border: none;
                }
                QPushButton[primary="true"]:hover { background-color: #276a2a; }
                QPushButton[secondary="true"] {
                    background-color: #eeeeee; color: #333333; font-weight: 600; padding: 8px 14px; border-radius: 6px; border: 1px solid #d5d5d5;
                }
                QPushButton[secondary="true"]:hover { background-color: #e6e6e6; }
                """
            )

            layout = QVBoxLayout(success_dialog)
            layout.setContentsMargins(18, 18, 18, 18)
            layout.setSpacing(14)

            # Header banner
            header = QFrame()
            header.setObjectName("HeaderBar")
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(14, 12, 14, 12)
            header_layout.setSpacing(12)

            header_icon = QLabel("✔")
            header_icon.setAlignment(Qt.AlignCenter)
            header_icon.setFixedSize(28, 28)
            header_icon.setStyleSheet(
                "background-color: #2e7d32; border-radius: 14px; color: #ffffff; font-size: 16px; font-weight: 700;"
            )
            header_layout.addWidget(header_icon)

            header_title = QLabel("Consolidation completed successfully")
            header_title.setObjectName("HeaderTitle")
            header_layout.addWidget(header_title, 1)

            layout.addWidget(header)

            # Details
            body_text = ""
            body_text += f"Consolidated file: {os.path.basename(consolidated_path)}\n"
            if audit_path:
                body_text += f"Audit report: {os.path.basename(audit_path)}\n"
            body_text += "\nTip: In Excel, hover over any consolidated cell to see the detailed breakdown of file contributions. Consolidated cells have orange borders and interactive comments."

            message_label = QLabel(body_text)
            message_label.setObjectName("BodyText")
            message_label.setWordWrap(True)
            layout.addWidget(message_label)

            # Separator
            separator = QFrame()
            separator.setObjectName("Separator")
            layout.addWidget(separator)

            # Action buttons (right-aligned)
            btn_layout = QHBoxLayout()
            btn_layout.addStretch(1)

            consolidated_btn = QPushButton("Open consolidated file")
            consolidated_btn.setProperty("primary", True)
            consolidated_btn.clicked.connect(lambda: webbrowser.open(consolidated_path))

            if audit_path:
                audit_btn = QPushButton("Open audit report")
                audit_btn.setProperty("secondary", True)
                audit_btn.clicked.connect(lambda: webbrowser.open(audit_path))

            open_folder_btn = QPushButton("Open containing folder")
            open_folder_btn.setProperty("secondary", True)
            open_folder_btn.clicked.connect(lambda: webbrowser.open(os.path.dirname(consolidated_path)))

            close_btn = QPushButton("Close")
            close_btn.setProperty("secondary", True)
            close_btn.clicked.connect(success_dialog.accept)

            btn_layout.addWidget(open_folder_btn)
            if audit_path:
                btn_layout.addWidget(audit_btn)
            btn_layout.addWidget(consolidated_btn)
            btn_layout.addWidget(close_btn)
            layout.addLayout(btn_layout)

            # Default action
            consolidated_btn.setDefault(True)

            success_dialog.exec_()
        else:
            QMessageBox.critical(self, "Error", f"An error occurred during processing:\n\n{message}")
    


def build_global_stylesheet():
    """Return an application-wide stylesheet to provide a consistent, modern UI.
    Uses neutral surfaces, accessible contrasts, and consistent paddings.
    """
    return """
    QWidget {
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 10pt;
        color: #1f1f1f;
    }
    QMainWindow, QWidget, QDialog {
        background-color: #deeaee; /* match app bg */
    }
    QLabel[hint="true"] { color: #616161; }

    /* App header */
    QFrame#AppHeader {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f7f9fb);
        border-bottom: 1px solid #e6e6e6;
    }

    /* Group containers */
    QGroupBox {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        margin-top: 14px; /* space for title */
        padding: 12px 10px 12px 10px; /* lower title a bit */
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                   stop:0 #ffffff, stop:1 #fbfbfb);
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 16px;
        padding: 2px 6px; /* slight top padding to lower text */
        color: #005423;
        background: transparent; /* keep floating label transparent */
        font-weight: 600;
    }

    /* Buttons */
    QPushButton {
        background-color: #f0f0f0;
        color: #222222;
        padding: 8px 12px;
        border: 1px solid #d5d5d5;
        border-radius: 6px;
    }
    QPushButton:hover { background-color: #eaeaea; }
    QPushButton:pressed { background-color: #e0e0e0; }
    QPushButton:disabled { color: #9e9e9e; background-color: #f7f7f7; border-color: #e8e8e8; }

    /* Primary buttons can opt-in via property */
    QPushButton[primary="true"] {
        background-color: #2e7d32; color: #ffffff; border: none; font-weight: 600;
    }
    QPushButton[primary="true"]:hover { background-color: #276a2a; }
    QPushButton[primary="true"]:pressed { background-color: #225b24; }

    /* Inputs */
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QListWidget, QTreeWidget, QTableView {
        background-color: #fafafa;
        border: 1px solid #dcdcdc;
        border-radius: 6px;
        selection-background-color: #cce8cc;
        selection-color: #1b1b1b;
    }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
        border: 1px solid #4CAF50;
        background-color: #ffffff;
    }

    /* Headers / subtle separators */
    QFrame[role="separator"], QFrame#Separator { background-color: #e0e0e0; max-height: 1px; min-height: 1px; }

    /* Scrollbars (compact, unobtrusive) */
    QScrollBar:vertical { width: 10px; background: transparent; }
    QScrollBar::handle:vertical { background: #cfcfcf; border-radius: 5px; min-height: 24px; }
    QScrollBar::handle:vertical:hover { background: #bdbdbd; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

    QToolTip { background-color: #333333; color: #ffffff; border: none; padding: 6px 8px; border-radius: 4px; }
    """


def main():
    """Main entry point for the Excel Consolidator application."""
    # Improve rendering on HiDPI displays and reduce pixelation
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Apply global stylesheet
    try:
        app.setStyleSheet(build_global_stylesheet())
    except Exception:
        pass
    # Install global tooltip filter to make tooltips sticky and close on outside click
    try:
        tooltip_filter = GlobalToolTipFilter(app)
        app.installEventFilter(tooltip_filter)
    except Exception:
        pass
    
    # Update app icon loading
    window = ExcelProcessorApp()
    app.setWindowIcon(window.windowIcon())
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()