# Conflict Detection Quick Reference

## Quick Formula Rules

```
📊 PERCENTAGE FORMAT → AVERAGE
🔢 NUMBER FORMAT → SUM
💰 CURRENCY FORMAT → SUM
📝 UNFORMATTED → SUM
```

---

## Detection Methods by Conflict Type

### 1. Format Type Detection
```python
# Location: src/core/main.py:1035-1059

def _is_percentage_format(self, format_str: str) -> bool:
    """Detects: '%' in number_format"""
    patterns = ['%', 'percent', '0.0%', '0.00%', '#,##0%']
    return any(pattern in format_str.lower() for pattern in patterns)

def _is_currency_format(self, format_str: str) -> bool:
    """Detects: Currency symbols in number_format"""
    symbols = ['$', '€', '£', '¥', '₽', '₹', '₩']
    return any(symbol in format_str for symbol in symbols)
```

**Triggered**: During template scanning (lines 1768-1799)
**Stored**: In `coord_format_info` dictionary
**Used**: During value processing (lines 1987-2006)

---

### 2. Data Type Conflict Detection
```python
# Location: src/core/main.py:1268-1397

def _process_cell_value_with_format_verification(value, format_info, coord, file_label, wb, stop_on_error):
    """Main dispatcher for format-specific processing"""
    
    if format_info.get('is_percentage'):
        return _process_percentage_value(...)  # Line 1298
    elif format_info.get('is_currency'):
        return _process_currency_value(...)    # Line 1341
    elif format_info.get('is_number'):
        return _process_number_value(...)      # Line 1363
    else:
        return _process_default_value(...)     # Line 1385
```

**Error Handling**:
- Returns `None` if conversion fails
- Emits error signal if `stop_on_error=True`
- Skips cell and continues if `stop_on_error=False`

---

### 3. Structure Conflict Detection
```python
# Location: src/core/main.py:1735-1736, 1905-1919

if validate_structure:
    # Check if file structure matches template
    # Compare worksheet names, dimensions
    if mismatch_detected:
        if stop_on_error:
            emit error and halt
        else:
            log warning and continue
```

**Checked Items**:
- Worksheet name matching
- Row/column dimensions
- Cell coordinate existence

---

### 4. Formula Conflict Detection
```python
# Location: src/core/main.py:1942-1960

# In source files:
if format_info.get('has_formula', False):
    if not include_totals and _is_total_cell(cell):
        continue  # Skip
    try:
        val = cell.value  # Use calculated value
    except:
        continue  # Skip if can't evaluate

# In output template:
if not overwrite_output_formulas:
    if cell.data_type == 'f' or cell.value.startswith('='):
        continue  # Preserve formula
```

**Settings**:
- `include_totals`: Process formula cells or skip
- `overwrite_output_formulas`: Replace template formulas or preserve

---

### 5. Merged Cell Detection
```python
# Location: Throughout processing

from openpyxl.cell import MergedCell

if isinstance(cell, MergedCell):
    continue  # Skip merged cells
```

**Error Detection**:
- Read-only attribute errors
- MergedCell type checks
- "attribute 'value' is read-only" exceptions

---

### 6. File Access Conflict Detection
```python
# Location: src/core/main.py:2018-2031, 1203-1257

try:
    wb = openpyxl.load_workbook(file)
except Exception as e:
    error_str = str(e).lower()
    
    # File access errors
    if "permission denied" in error_str or "sharing violation" in error_str:
        → Error: File currently open
    
    # File format errors
    elif "badzipfile" in error_str:
        → Error: Corrupted file
    
    # Password errors
    elif "password" in error_str or "encrypted" in error_str:
        → Error: Password protected
```

**Error Messages**: Lines 1203-1257 (file-specific), 1125-1201 (general)

---

### 7. Validation Conflict Detection
```python
# Location: src/core/main.py:1973-1984

if validate_value is not None and not validate_value(val, settings):
    if stop_on_error:
        emit error with details
        halt processing
    else:
        continue  # Skip invalid value
```

**Validation Checks**:
- Range validation (min/max)
- Data type validation
- Custom validation rules

---

## Consolidation Flow with Conflict Checks

```
1. TEMPLATE LOADING (Lines 1645-1685)
   ├── Check: File exists
   ├── Check: Not password protected
   ├── Check: Valid Excel format
   └── Scan: Extract format info → coord_format_info

2. FILE DISCOVERY (Lines 1687-1724)
   ├── Check: Folder has Excel files
   ├── Filter: Skip temp files (~$)
   └── Validate: File accessibility

3. FORMAT STANDARDIZATION (Lines 1399-1472)
   ├── For each source file:
   │   ├── Check: File accessible
   │   ├── Match: Apply template formats
   │   ├── Convert: Percentage normalization
   │   └── Preserve: Skip formula cells

4. VALUE EXTRACTION (Lines 1926-2013)
   ├── For each cell in source:
   │   ├── Check: Coordinate in template
   │   ├── Check: Not merged cell
   │   ├── Check: Format compatibility
   │   ├── Process: Format-specific conversion
   │   ├── Validate: Range/type checks
   │   └── Accumulate: Add to totals
   
5. CONSOLIDATION (Lines 2049-2156)
   ├── For each coordinate:
   │   ├── Check: Not merged cell
   │   ├── Check: Overwrite formulas setting
   │   ├── Calculate: SUM or AVERAGE
   │   ├── Apply: Template format
   │   └── Add: Comment with breakdown

6. OUTPUT GENERATION (Lines 2157-2274)
   ├── Create: Consolidated file
   ├── Add: Contributions sheet
   └── Save: With date stamp
```

---

## Error Emission Points

| Line Range | Trigger | Severity | Halts Processing |
|-----------|---------|----------|------------------|
| 1330-1338 | Percentage format error | HIGH | If stop_on_error |
| 1353-1360 | Currency format error | HIGH | If stop_on_error |
| 1375-1382 | Number format error | HIGH | If stop_on_error |
| 1653-1666 | Template not found | CRITICAL | Always |
| 1684-1685 | Template load error | CRITICAL | Always |
| 1713-1724 | No Excel files found | CRITICAL | Always |
| 1905-1919 | Structure mismatch | HIGH | If stop_on_error |
| 1978-1983 | Validation error | MEDIUM | If stop_on_error |
| 2018-2031 | File processing error | VARIES | Never (logged) |
| 2247-2256 | Save error | CRITICAL | Always |

---

## Settings That Affect Conflict Resolution

```python
settings = {
    'data_processing': {
        'auto_convert_text': bool,        # Auto-convert text to numbers
        'handle_percentages': bool,       # Handle percentage conversion
        'include_totals': bool,           # Include total row cells
        'ignore_formulas': bool,          # Skip formula cells
    },
    'validation': {
        'validate_structure': bool,       # Check file structure matches
        'validate_data_types': bool,      # Validate data type consistency
        'validate_ranges': bool,          # Check min/max ranges
        'stop_on_error': bool,            # Halt on first error vs continue
    },
    'output_handling': {
        'overwrite_output_formulas': bool,# Replace template formulas
    },
    'performance': {
        'read_only_mode': bool,           # Faster but no formulas
        'cell_filter': bool,              # Process subset of cells
    }
}
```

---

## Common Conflict Scenarios & Detection

### Scenario 1: Mixed Percentage Formats
```
FILE 1: 82.5    → Detected as percentage points (>1)
FILE 2: 0.825   → Detected as decimal, converted to 82.5
FILE 3: "82.5%" → Detected as text %, parsed to 82.5
```
**Detection**: `_process_percentage_value()` at line 1298
**Normalization**: Lines 1302-1326
**Result**: All normalized to percentage points before averaging

### Scenario 2: Text in Numeric Cell
```
FILE 1: 100     → Processes normally
FILE 2: "N/A"   → Triggers exception at Decimal() conversion
```
**Detection**: Exception in `_process_number_value()` at line 1363
**Action**: Returns `None`, cell skipped
**Error**: Emitted if `stop_on_error=True` (line 1375-1382)

### Scenario 3: Formula in Source
```
FILE 1: 500           → Static value, processes normally
FILE 2: =SUM(A1:A10) → Detected by format_info['has_formula']
```
**Detection**: Line 1942, `format_info.get('has_formula', False)`
**Action**: 
- If `include_totals=False`: Skip (line 1944)
- If `include_totals=True`: Use calculated value (line 1948)

### Scenario 4: File Currently Open
```
openpyxl.load_workbook("File1.xlsx")
→ PermissionError: [Errno 13] Permission denied
```
**Detection**: Exception at line 2018
**Classification**: `_get_file_error_message()` at line 1203
**Action**: Log error, skip file, continue processing
**User Message**: "File Currently Open" with instructions

### Scenario 5: Structure Mismatch
```
Template: Worksheet "Data", 100 rows
Source:   Worksheet "Sheet1", 50 rows
```
**Detection**: Line 1905-1919, if `validate_structure=True`
**Action**:
- If `stop_on_error=True`: Halt and show error
- If `stop_on_error=False`: Log warning, process available cells

---

## Debugging Commands

### Check Format Detection
```python
# In template scanning phase
print(f"Format info for {coord}: {format_info}")
# Output: {'is_percentage': True, 'is_currency': False, 'number_format': '0.00%', ...}
```

### Check Value Processing
```python
# In value extraction phase
processing_logger.info(f"Processing {coord}: value={value}, format={format_info}")
# Check logs/consolidation_processing.log
```

### Check Consolidation Method
```python
# In consolidation phase
consolidation_method = format_info.get('consolidation_method', 'sum')
print(f"{coord}: Using {consolidation_method} for value {value}")
```

### Check Error Classification
```python
# In exception handler
error_str = str(error).lower()
print(f"Error type: {error_str}")
# Match against patterns in _get_file_error_message()
```

---

## Testing Checklist

### Unit Tests Needed
- [ ] `_is_percentage_format()` with various format strings
- [ ] `_is_currency_format()` with various symbols
- [ ] `_process_percentage_value()` with mixed formats
- [ ] `_process_currency_value()` with various currencies
- [ ] `_process_number_value()` with text numbers
- [ ] Error classification in `_get_file_error_message()`

### Integration Tests Needed
- [ ] Consolidate 3 files with mixed percentage formats
- [ ] Consolidate files with text in numeric cells
- [ ] Consolidate with structure mismatch
- [ ] Consolidate with formulas (include vs exclude)
- [ ] Consolidate with merged cells
- [ ] Consolidate with file access errors (mock)

### Test Data Sets
1. **Perfect Match**: All files identical format
2. **Mixed Percentages**: 82.5, 0.825, "82.5%"
3. **Mixed Currency**: $100, €100, 100
4. **Text Numbers**: "100", 100, '100
5. **Structure Mismatch**: Different sheet names/sizes
6. **Formula Mix**: Static values and formulas
7. **Merged Cells**: Various merge scenarios
8. **Empty Values**: Mix of 0, empty, null

---

## Performance Considerations

### High-Frequency Operations
- **Format detection**: Cached in `coord_format_info` (O(1) lookup)
- **Cell iteration**: Uses `iter_rows()` for memory efficiency
- **Value processing**: Minimal logging in production
- **File I/O**: Read-only mode when possible

### Bottlenecks to Monitor
- **Format standardization** (lines 1399-1472): Updates every source file
- **Percentage normalization** (lines 1439-1446): Per-cell calculation
- **Contribution tracking** (lines 2008-2012): Memory overhead for large datasets
- **Comment generation** (lines 2110-2155): String concatenation per cell

---

## END OF QUICK REFERENCE
Version: 1.0
Last Updated: 2025-09-30
