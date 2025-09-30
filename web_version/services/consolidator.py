"""
Excel Consolidation Service - Extracted from desktop app
Reusable core logic without GUI dependencies
"""
import os
import glob
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.cell.cell import MergedCell
from openpyxl.comments import Comment
from openpyxl.styles import Border, Side, Font, PatternFill
from decimal import Decimal, InvalidOperation
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ExcelConsolidator:
    """
    Consolidates multiple Excel files into one template file
    Extracted from desktop application for web use
    """
    
    def __init__(self, template_path, source_folder, settings=None, progress_callback=None):
        """
        Initialize consolidator
        
        Args:
            template_path: Path to Excel template file
            source_folder: Folder containing source Excel files
            settings: Dict of processing settings
            progress_callback: Function(current, total, filename) for progress updates
        """
        self.template_path = template_path
        self.source_folder = source_folder
        self.settings = settings or {}
        self.progress_callback = progress_callback
        
        # Processing flags
        self.convert_text_to_numbers = self.settings.get('convert_text_to_numbers', True)
        self.convert_percentages = self.settings.get('convert_percentages', True)
        self.skip_validation = self.settings.get('skip_validation', True)
        
        logger.info(f"Consolidator initialized: template={template_path}, sources={source_folder}")
    
    def consolidate(self):
        """
        Main consolidation method
        Returns: Path to consolidated output file
        """
        logger.info("=" * 60)
        logger.info("Starting Excel Consolidation")
        logger.info("=" * 60)
        
        # Find all Excel files
        files = self._get_excel_files()
        if not files:
            raise ValueError("No Excel files found in source folder")
        
        logger.info(f"Found {len(files)} Excel files to consolidate")
        
        # Load template
        template_wb = openpyxl.load_workbook(self.template_path, data_only=False)
        output_ws = template_wb.active
        
        logger.info(f"Template loaded: {output_ws.title}")
        
        # Storage for totals and contributions
        totals = {}
        contributions = {}
        percent_counts = {}
        
        # Analyze template for format information
        coord_format_info = self._analyze_template_formats(output_ws)
        
        # Process each source file
        for idx, file in enumerate(files, 1):
            if self.progress_callback:
                self.progress_callback(idx, len(files), os.path.basename(file))
            
            logger.info(f"Processing [{idx}/{len(files)}]: {os.path.basename(file)}")
            
            try:
                self._process_file(
                    file,
                    totals,
                    contributions,
                    percent_counts,
                    coord_format_info,
                    len(files)
                )
            except Exception as e:
                logger.error(f"Error processing {file}: {str(e)}")
                # Continue with next file
        
        # Write consolidated values to template
        self._write_consolidated_values(
            output_ws,
            totals,
            contributions,
            percent_counts,
            coord_format_info,
            len(files)
        )
        
        # Save output file
        output_path = self._generate_output_path()
        template_wb.save(output_path)
        template_wb.close()
        
        logger.info(f"✅ Consolidation complete: {output_path}")
        logger.info("=" * 60)
        
        return output_path
    
    def _get_excel_files(self):
        """Get list of Excel files from source folder"""
        files = []
        
        # Look for .xlsx files
        xlsx_files = glob.glob(os.path.join(self.source_folder, '*.xlsx'))
        files.extend([f for f in xlsx_files if not os.path.basename(f).startswith('~$')])
        
        # Optionally include .xls files
        if self.settings.get('support_xls', True):
            xls_files = glob.glob(os.path.join(self.source_folder, '*.xls'))
            files.extend([f for f in xls_files if not os.path.basename(f).startswith('~$')])
        
        return sorted(files)
    
    def _analyze_template_formats(self, worksheet):
        """
        Analyze template to determine cell formats (currency, percentage, etc.)
        Returns dict: {coordinate: {format_info}}
        """
        format_info = {}
        
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue
                
                coord = cell.coordinate
                number_format = cell.number_format or ''
                
                info = {
                    'number_format': number_format,
                    'is_percentage': self._is_percentage_format(number_format),
                    'is_currency': self._is_currency_format(number_format),
                    'is_number': self._is_number_format(number_format),
                    'consolidation_method': 'average' if self._is_percentage_format(number_format) else 'sum'
                }
                
                format_info[coord] = info
        
        logger.info(f"Analyzed {len(format_info)} cells in template")
        return format_info
    
    def _is_percentage_format(self, format_str):
        """Check if cell format is percentage"""
        if not format_str:
            return False
        return '%' in format_str
    
    def _is_currency_format(self, format_str):
        """Check if cell format is currency"""
        if not format_str:
            return False
        currency_symbols = ['$', '€', '£', '¥', '₱']
        return any(symbol in format_str for symbol in currency_symbols)
    
    def _is_number_format(self, format_str):
        """Check if cell format is numeric"""
        if not format_str:
            return False
        number_patterns = ['0.00', '#,##0', '0.0', '0']
        return any(pattern in format_str for pattern in number_patterns)
    
    def _process_file(self, filepath, totals, contributions, percent_counts, coord_format_info, total_files):
        """Process a single Excel file and update totals"""
        wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
        ws = wb.active
        
        file_label = os.path.splitext(os.path.basename(filepath))[0]
        
        for row in ws.iter_rows():
            for cell in row:
                value = cell.value
                coord = cell.coordinate
                
                # Skip empty cells
                if value is None or value == '':
                    continue
                
                # Skip formulas to prevent double-counting
                if hasattr(cell, 'data_type') and cell.data_type == 'f':
                    continue
                
                # Get format info
                format_info = coord_format_info.get(coord, {})
                
                # Process cell value
                val = self._process_cell_value(value, format_info)
                if val is None:
                    continue
                
                # Determine consolidation method
                consolidation_method = format_info.get('consolidation_method', 'sum')
                
                if consolidation_method == 'average':
                    # Percentage cells - accumulate for average
                    current_total = totals.get(coord)
                    totals[coord] = (current_total + val) if current_total is not None else val
                    
                    # Initialize count
                    if coord not in percent_counts:
                        percent_counts[coord] = total_files
                else:
                    # Sum values
                    current_total = totals.get(coord)
                    totals[coord] = (current_total + val) if current_total is not None else val
                
                # Track contributions
                if coord not in contributions:
                    contributions[coord] = {}
                prev = contributions[coord].get(file_label)
                contributions[coord][file_label] = (prev + val) if prev is not None else val
        
        wb.close()
    
    def _process_cell_value(self, value, format_info):
        """
        Process cell value based on type and settings
        Returns numeric value or None
        """
        # Already a number
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        
        # Try to convert text to number
        if isinstance(value, str):
            # Remove commas
            cleaned = value.replace(',', '').strip()
            
            # Handle percentages
            if self.convert_percentages and cleaned.endswith('%'):
                try:
                    # "82.5%" → 82.5 (stored as percentage points)
                    numeric = float(cleaned[:-1])
                    return Decimal(str(numeric))
                except (ValueError, InvalidOperation):
                    pass
            
            # Handle currency
            currency_symbols = ['$', '€', '£', '¥', '₱']
            for symbol in currency_symbols:
                cleaned = cleaned.replace(symbol, '')
            
            # Try to convert to number
            if self.convert_text_to_numbers:
                try:
                    return Decimal(cleaned)
                except (ValueError, InvalidOperation):
                    pass
        
        return None
    
    def _write_consolidated_values(self, worksheet, totals, contributions, percent_counts, coord_format_info, total_files):
        """Write consolidated values back to template"""
        
        # Orange border for consolidated cells
        thin_orange = Border(
            left=Side(style='thin', color='FF8C00'),
            right=Side(style='thin', color='FF8C00'),
            top=Side(style='thin', color='FF8C00'),
            bottom=Side(style='thin', color='FF8C00')
        )
        
        for coord, value in totals.items():
            cell = worksheet[coord]
            
            if isinstance(cell, MergedCell):
                continue
            
            format_info = coord_format_info.get(coord, {})
            consolidation_method = format_info.get('consolidation_method', 'sum')
            
            try:
                if consolidation_method == 'average':
                    # Calculate average for percentage cells
                    count = max(1, percent_counts.get(coord, 1))
                    avg_value = float(value / Decimal(count))
                    
                    # Excel expects percentages as decimals (e.g., 0.825 for 82.5%)
                    cell.value = avg_value / 100
                    
                    # Maintain percentage format
                    template_format = format_info.get('number_format', '0.00%')
                    cell.number_format = template_format
                    
                    logger.debug(f"{coord}: Average = {avg_value:.2f}% (format: {template_format})")
                else:
                    # Sum for other cells
                    cell.value = float(value)
                    
                    # Apply formatting
                    if format_info.get('is_currency', False):
                        cell.number_format = format_info.get('number_format', '$#,##0.00')
                    elif format_info.get('is_number', False):
                        cell.number_format = format_info.get('number_format', '#,##0.00')
                    
                    logger.debug(f"{coord}: Sum = {float(value):,.2f}")
            except Exception as e:
                logger.error(f"Error writing value to {coord}: {e}")
                cell.value = float(value) if value is not None else 0
            
            # Add comment showing contributions
            file_map = contributions.get(coord, {})
            if file_map:
                comment_text = self._build_comment_text(coord, value, file_map, format_info, percent_counts, total_files)
                cell.comment = Comment(comment_text, "Excel Consolidator")
            
            # Add orange border
            cell.border = thin_orange
    
    def _build_comment_text(self, coord, total_value, file_map, format_info, percent_counts, total_files):
        """Build comment text showing file contributions"""
        items = sorted(file_map.items(), key=lambda x: x[0].lower())
        max_name = max((len(n) for n, _ in items), default=4)
        
        lines = []
        lines.append("Consolidation Summary")
        lines.append(f"Cell: {coord}")
        
        # Format total based on cell type
        if format_info.get('is_percentage', False):
            count = max(1, percent_counts.get(coord, 1))
            avg_val = float(total_value / Decimal(count))
            lines.append(f"Average: {avg_val:.2f}% (from {count} files)\n")
        elif format_info.get('is_currency', False):
            lines.append(f"Total: ${float(total_value):,.2f}\n")
        else:
            lines.append(f"Total: {float(total_value):,.2f}\n")
        
        lines.append("Contributors (file  |  value)")
        lines.append("-" * 30)
        
        # List each file's contribution
        for name, v in items:
            pad = " " * (max_name - len(name))
            if format_info.get('is_percentage', False):
                lines.append(f"{name}{pad}  |  {float(v):.2f}%")
            elif format_info.get('is_currency', False):
                lines.append(f"{name}{pad}  |  ${float(v):,.2f}")
            else:
                lines.append(f"{name}{pad}  |  {float(v):,.2f}")
        
        return "\n".join(lines)
    
    def _generate_output_path(self):
        """Generate output file path with timestamp"""
        # Use same folder as template
        template_dir = os.path.dirname(self.template_path)
        template_ext = os.path.splitext(self.template_path)[1]
        
        # Generate filename with date
        date_str = datetime.now().strftime("%b_%d_%Y")
        filename = f"Consolidated_{date_str}{template_ext}"
        
        return os.path.join(template_dir, filename)
