# Consolidation Conflicts - Complete Reference Guide

## Overview
This document identifies all types of conflicts that can occur during Excel consolidation and explains how the system detects and handles them. The system uses **SUM** for numeric values and **AVERAGE** for percentage values.

---

## 🎯 Core Consolidation Logic

### **Rule 1: Numbers → SUM**
When the system detects numeric values (numbers, currency), it uses **SUM** formula:
```
Result = Value1 + Value2 + Value3 + ... + ValueN
```

### **Rule 2: Percentages → AVERAGE**
When the system detects percentage format, it uses **AVERAGE** formula:
```
Result = (Value1 + Value2 + Value3 + ... + ValueN) / N
```

---

## 📊 Conflict Types

### **1. FORMAT TYPE CONFLICTS**

#### 1.1 Percentage Format Mismatch
**Description**: Cell has percentage format in template but numeric format in source files (or vice versa)

**Detection**:
- Template cell has `%` in number_format
- Source cell has different format

**Example**:
```
Template Cell G867: Format = "0.00%" (Percentage)
File 1 Cell G867: Value = 50 (Number without % format)
File 2 Cell G867: Value = 0.75 (Decimal number)
File 3 Cell G867: Value = "82.5%" (Text with %)
```

**System Behavior**:
- **Auto-converts** values to match template format
- Values > 1 treated as percentage points (82.5 = 82.5%)
- Values 0-1 treated as decimals (0.825 = 82.5%)
- Text with '%' parsed and converted

**Resolution**:
```python
# System normalizes all to percentage points for averaging:
File 1: 50 → 50 (percentage points)
File 2: 0.75 → 75 (0.75 * 100)
File 3: "82.5%" → 82.5
Average: (50 + 75 + 82.5) / 3 = 69.17%
```

**Conflict Severity**: ⚠️ MEDIUM (Auto-resolved with normalization)

---

#### 1.2 Currency Format Mismatch
**Description**: Different currency symbols or formatting

**Detection**:
- Template has currency symbol ($, €, £, ¥, etc.)
- Source file has different or no currency symbol

**Example**:
```
Template: $#,##0.00
File 1: $1,000.00 (Currency)
File 2: 1500 (Number)
File 3: "€1,200" (Different currency)
```

**System Behavior**:
- **Strips** all currency symbols
- **Converts** to decimal number
- **Applies** template currency format to result
- **Uses SUM** formula

**Resolution**:
```python
File 1: $1,000.00 → 1000
File 2: 1500 → 1500
File 3: €1,200 → 1200
Sum: 1000 + 1500 + 1200 = 3700
Final: $3,700.00
```

**Conflict Severity**: ✅ LOW (Auto-resolved)

---

#### 1.3 Mixed Format Types (Critical)
**Description**: Same cell coordinate has different data types across files

**Detection**:
- Template expects one format type
- Source files contain incompatible types

**Example**:
```
Template Cell B10: Currency format
File 1 Cell B10: $1,000 (Currency) ✓
File 2 Cell B10: "N/A" (Text) ✗
File 3 Cell B10: 85% (Percentage) ✗
```

**System Behavior**:
- **Attempts conversion** to template format
- **Skips invalid values** if conversion fails
- **Logs error** with file name and cell location
- **Continues or stops** based on validation settings

**Resolution Options**:
1. **Continue on Error**: Skip invalid cells, consolidate valid ones
2. **Stop on Error**: Halt and report first error

**Conflict Severity**: 🔴 HIGH (May cause data loss if not resolved)

---

### **2. DATA TYPE CONFLICTS**

#### 2.1 Text in Numeric Cell
**Description**: Text values in cells expected to contain numbers

**Detection**:
- Cell value is string type
- Cannot be converted to number
- Auto-convert setting enabled

**Example**:
```
Template Cell C5: Number format
File 1: 100 (Number) ✓
File 2: "N/A" (Text) ✗
File 3: "TBD" (Text) ✗
```

**System Behavior**:
```python
if auto_convert_text_enabled:
    try:
        value = Decimal(text.strip().replace(",", ""))
    except:
        if stop_on_error:
            raise DataValidationError
        else:
            skip_cell()
```

**Error Message**:
```
Number Format Error

Cell C5 in file 'File2.xlsx' contains invalid numeric data:
'N/A'

Expected: Numeric values (e.g., 100, 100.50)

💡 Solution: Ensure the cell contains valid numeric data.
```

**Conflict Severity**: 🔴 HIGH

---

#### 2.2 Numeric Text vs True Numbers
**Description**: Numbers stored as text ("123") vs actual numbers (123)

**Detection**:
- Cell data type is string
- Content is parseable as number

**Example**:
```
File 1: 123 (Number)
File 2: "123" (Text)
File 3: '456 (Text with apostrophe)
```

**System Behavior**:
- **Auto-converts** if `auto_convert_text` is enabled
- **Strips** whitespace and commas
- **Parses** to Decimal

**Resolution**:
```python
# All converted to numbers and summed
Result: 123 + 123 + 456 = 702
```

**Conflict Severity**: ✅ LOW (Auto-resolved if setting enabled)

---

### **3. STRUCTURE CONFLICTS**

#### 3.1 Missing Cells/Worksheets
**Description**: Source file missing cells that exist in template

**Detection**:
- Template has cell at coordinate
- Source file missing that cell or worksheet

**Example**:
```
Template: Has cells A1:Z100
File 1: Has cells A1:Z100 ✓
File 2: Has cells A1:M50 (Missing N:Z and rows 51-100) ✗
```

**System Behavior**:
- **Treats missing cells as 0** (neutral for SUM)
- **Continues processing** available cells
- **Logs** missing cells if validation enabled

**Impact on Formulas**:
- **SUM**: Missing values = 0 (no impact)
- **AVERAGE**: Count only includes files with values

**Conflict Severity**: ⚠️ MEDIUM

---

#### 3.2 Extra Cells in Source
**Description**: Source files have cells not in template

**Detection**:
- Source file has data in cells
- Template doesn't have those cells defined

**Example**:
```
Template: A1:M100
File 1: A1:Z200 (Extra columns N:Z, rows 101-200)
```

**System Behavior**:
- **Ignores** cells not in template
- **Only processes** cells matching template coordinates
- **Skips** extra data silently

**Conflict Severity**: ✅ LOW (Expected behavior)

---

#### 3.3 Worksheet Name Mismatch
**Description**: Different worksheet names across files

**Detection**:
- Template has specific sheet name
- Source file has different sheet name(s)

**Example**:
```
Template: "Data" worksheet
File 1: "Data" worksheet ✓
File 2: "Sheet1" worksheet ✗
```

**System Behavior**:
- **Uses first/active sheet** if name mismatch
- **Validates structure** if setting enabled
- **Reports error** if strict validation enabled

**Conflict Severity**: ⚠️ MEDIUM

---

### **4. FORMULA CONFLICTS**

#### 4.1 Formula in Source File
**Description**: Source file has formula instead of static value

**Detection**:
- Cell data_type = 'f' (formula)
- Settings determine handling

**Example**:
```
Template Cell D10: Static value
File 1 Cell D10: 500 (Static) ✓
File 2 Cell D10: =SUM(A10:C10) (Formula) ?
```

**System Behavior**:
```python
if ignore_formulas_setting:
    skip_cell()
else:
    try:
        use_calculated_value()  # Read formula result
    except:
        skip_cell()
```

**Settings Impact**:
- **Include Formulas**: Uses calculated result value
- **Ignore Formulas**: Skips cells with formulas

**Conflict Severity**: ⚠️ MEDIUM (Configurable)

---

#### 4.2 Formula in Template (Output)
**Description**: Template cell contains formula that would be overwritten

**Detection**:
- Template cell has formula
- Consolidation would overwrite it

**Example**:
```
Template Cell E100: =SUM(E1:E99)
Consolidation wants to write: 12345
```

**System Behavior**:
```python
if overwrite_output_formulas_setting:
    replace_formula_with_consolidated_value()
else:
    preserve_formula()  # Skip consolidation for this cell
```

**Settings Impact**:
- **Overwrite Output Formulas = True**: Replaces formula with consolidated value
- **Overwrite Output Formulas = False**: Preserves template formula

**Conflict Severity**: 🔴 HIGH (Can lose important calculations)

---

#### 4.3 Total Row/Cell Detection
**Description**: Cells marked as "totals" that may duplicate data

**Detection**:
- Cell value contains: "total", "sum", "subtotal", "grand total"
- Position-based heuristics

**Example**:
```
Row 99: Individual values (consolidate normally)
Row 100: "Total" label and SUM formula
```

**System Behavior**:
```python
if include_totals_setting:
    process_all_cells()
else:
    if is_total_cell():
        skip_cell()
```

**Settings Impact**:
- **Include Totals = True**: Consolidates total rows (may cause double-counting)
- **Include Totals = False**: Skips total rows

**Conflict Severity**: 🔴 HIGH (Can cause incorrect sums)

---

### **5. MERGED CELL CONFLICTS**

#### 5.1 Merged Cells in Source
**Description**: Source file has merged cells

**Detection**:
- Cell is instance of MergedCell
- Cell.value access raises error

**Example**:
```
File 1:
  A1:B1 merged = "Header" → A1 has value, B1 is MergedCell
```

**System Behavior**:
- **Skips** MergedCell instances (only processes top-left cell)
- **Reads value** from top-left cell of merge range
- **May report error** if validation strict

**Error Message**:
```
🔗 Merged Cells in File

The file 'File1.xlsx' contains merged cells that prevent data consolidation.

💡 Solution: Open 'File1.xlsx' in Excel, select all cells (Ctrl+A), 
go to Home tab → Merge & Center → Unmerge Cells.
```

**Conflict Severity**: 🔴 HIGH (Blocks processing)

---

#### 5.2 Merged Cells in Template
**Description**: Template file has merged cells

**Detection**:
- Template cell is MergedCell
- Cannot write consolidated value

**Example**:
```
Template A1:C1 merged
System tries to write to B1 (MergedCell)
```

**System Behavior**:
- **Skips writing** to MergedCell instances
- **Only writes** to top-left cell of merged range
- **May cause "read-only" errors** if not handled

**Error Message**:
```
🔗 Merged Cell Conflict

Template contains merged cells that prevent consolidation.

💡 Solution: 
• In Excel: Select all cells (Ctrl+A) → Home tab → Merge & Center (to unmerge)
• Create a new template without any merged cells
```

**Conflict Severity**: 🔴 CRITICAL (Blocks output)

---

### **6. FILE ACCESS CONFLICTS**

#### 6.1 File Currently Open
**Description**: File is open in Excel or another program

**Detection**:
- Permission denied error
- Sharing violation error

**Example**:
```
File 'Report-2025.xlsx' is open in Excel
System tries to read/write → Error
```

**Error Message**:
```
📁 File Currently Open

The file 'Report-2025.xlsx' is currently open in Excel or another program.

💡 Solution: Close the file in Excel and try again. Make sure to save any changes first.
```

**Conflict Severity**: 🔴 HIGH (Blocks processing)

---

#### 6.2 File Permission Denied
**Description**: No read/write permissions on file

**Detection**:
- Permission denied error
- Access denied error

**Error Message**:
```
🔒 Permission Denied

You don't have permission to access this file or folder.

💡 Solution: 
• Check file permissions in Windows Explorer
• Run the application as Administrator
• Ensure the file is not marked as read-only
```

**Conflict Severity**: 🔴 HIGH

---

#### 6.3 Corrupted File
**Description**: File is corrupted or invalid Excel format

**Detection**:
- BadZipFile error
- Invalid file format error

**Error Message**:
```
❌ Corrupted File

The file 'Data.xlsx' is corrupted or not a valid Excel file.

💡 Solution: Try opening the file in Excel to repair it using 'File > Open and Repair', 
or exclude this file from consolidation.
```

**Conflict Severity**: 🔴 HIGH

---

#### 6.4 Password Protected File
**Description**: File is encrypted with password

**Detection**:
- Password error
- Encrypted file error

**Error Message**:
```
🔒 Password Protected

The file 'Secure.xlsx' is password protected and cannot be opened.

💡 Solution: Remove the password protection from the file before consolidation.
```

**Conflict Severity**: 🔴 HIGH

---

### **7. VALIDATION CONFLICTS**

#### 7.1 Out of Range Values
**Description**: Values outside configured min/max range

**Detection**:
- Validation settings define min/max
- Cell value < min or > max

**Example**:
```
Settings: min=0, max=100
File 1 Cell A1: 50 ✓
File 2 Cell A1: 150 ✗ (exceeds max)
File 3 Cell A1: -10 ✗ (below min)
```

**System Behavior**:
```python
if validate_ranges:
    if value < min_value or value > max_value:
        if stop_on_error:
            raise ValidationError
        else:
            skip_cell()
```

**Error Message**:
```
Data Validation Error

Value 150 at cell A1 in file 'File2.xlsx' is outside the allowed range.

Please check the data in this file or adjust the validation settings.
```

**Conflict Severity**: ⚠️ MEDIUM (Configurable)

---

#### 7.2 Data Type Validation
**Description**: Value doesn't match expected data type

**Detection**:
- Template expects number
- Source has text/date/etc.

**Example**:
```
Template expects: Number
File contains: "2025-01-15" (Date)
```

**System Behavior**:
- **Attempts conversion** based on settings
- **Validates** against expected type
- **Reports error** if validation fails

**Conflict Severity**: ⚠️ MEDIUM

---

#### 7.3 Structure Validation
**Description**: File structure doesn't match template

**Detection**:
- Different row/column counts
- Different worksheet names
- Missing headers

**Example**:
```
Template: 10 columns, "Data" sheet
File: 15 columns, "Sheet1" sheet
```

**System Behavior**:
```python
if validate_structure:
    if source_structure != template_structure:
        if stop_on_error:
            raise StructureError
        else:
            log_warning()
            use_available_cells()
```

**Error Message**:
```
📋 Structure Mismatch

The file 'File1.xlsx' has a different structure than the template.

💡 Solution: Ensure all files have the same column headers and data layout as the template.
```

**Conflict Severity**: ⚠️ MEDIUM

---

### **8. PERCENTAGE-SPECIFIC CONFLICTS**

#### 8.1 Mixed Percentage Representations
**Description**: Different files use different percentage formats

**Detection**:
- Inconsistent percentage notation across files
- Template has percentage format

**Example**:
```
Template Cell: 0.00% format
File 1: 82.5 (represents 82.5%)
File 2: 0.825 (represents 82.5% as decimal)
File 3: "82.5%" (text)
File 4: 82.5% (formatted percentage)
```

**System Normalization**:
```python
def _process_percentage_value(value):
    if isinstance(value, (int, float)):
        if 0 <= value <= 1:
            # Decimal format: convert to percentage points
            return value * 100  # 0.825 → 82.5
        else:
            # Already in percentage points
            return value  # 82.5 → 82.5
    elif isinstance(value, str):
        if value.endswith('%'):
            return float(value[:-1])  # "82.5%" → 82.5
        else:
            numeric = float(value)
            if 0 <= numeric <= 1:
                return numeric * 100
            else:
                return numeric
```

**Consolidation**:
```python
# All normalized to percentage points:
File 1: 82.5 → 82.5
File 2: 0.825 → 82.5
File 3: "82.5%" → 82.5
File 4: 82.5% → 82.5

# Calculate average:
Average = (82.5 + 82.5 + 82.5 + 82.5) / 4 = 82.5

# Convert to decimal for Excel:
Result in Excel = 82.5 / 100 = 0.825 (displays as 82.5%)
```

**Conflict Severity**: ✅ LOW (Auto-normalized)

---

#### 8.2 Percentage vs Number Conflict
**Description**: Template expects percentage but source has regular numbers (or vice versa)

**Detection**:
- Template has percentage format
- Source files have large numbers (>1) or very small decimals

**Example**:
```
Template Cell B5: 0.00% (Percentage format)
File 1: 5000 (Large number - likely NOT a percentage)
File 2: 75 (Could be 75% or just 75)
File 3: 0.85 (Likely 85%)
```

**System Behavior**:
- **Applies normalization rules**
- **May produce unexpected results** if data interpretation is wrong
- **Logs warning** for suspicious values

**Potential Issue**:
```python
# If File 1's 5000 is actually a regular number but template is %:
File 1: 5000 → Treated as 5000% (wrong!)
File 2: 75 → Treated as 75%
File 3: 0.85 → Treated as 85%

Average = (5000 + 75 + 85) / 3 = 1720% (INCORRECT!)
```

**Conflict Severity**: 🔴 CRITICAL (Can produce wrong results)

**Recommendation**: Ensure all source files match template format expectations

---

### **9. ENCODING & CHARACTER CONFLICTS**

#### 9.1 Character Encoding Issues
**Description**: File uses non-UTF-8 encoding

**Detection**:
- Decode error
- Encoding error

**Example**:
```
File with special characters: café, naïve, €, 中文
Wrong encoding: caf├®, na├»ve, ΓÇú, ä¸­æ–‡
```

**Error Message**:
```
📝 File Encoding Issue

One or more files have text encoding problems that prevent proper reading.

💡 Solution: Try opening the files in Excel and saving them again, 
or ensure they are saved with UTF-8 encoding.
```

**Conflict Severity**: ⚠️ MEDIUM

---

#### 9.2 Special Characters in Numbers
**Description**: Numbers contain special characters

**Example**:
```
"1,234.56" (comma separator)
"$1,234" (currency symbol)
"€1.234,56" (European format)
```

**System Behavior**:
- **Strips** common separators: `,` and spaces
- **Strips** currency symbols
- **Parses** remaining string as number

**Conflict Severity**: ✅ LOW (Auto-handled)

---

### **10. EMPTY/NULL VALUE CONFLICTS**

#### 10.1 Empty Cells
**Description**: Cells have no value (None, empty string)

**Example**:
```
File 1 Cell A1: 100
File 2 Cell A1: (empty)
File 3 Cell A1: 200
```

**System Behavior**:
```python
if value is None or value == "":
    return None  # Skip this cell

# SUM: 100 + 200 = 300 (empty treated as non-existent)
# AVERAGE for %: (100 + 200) / 2 = 150 (only counts non-empty)
```

**Conflict Severity**: ✅ LOW (Expected behavior)

---

#### 10.2 Zero vs Empty
**Description**: Distinction between 0 and empty cell

**Example**:
```
File 1: 100
File 2: 0 (explicit zero)
File 3: (empty)
File 4: 200
```

**System Behavior**:
- **Empty**: Not included in count
- **Zero**: Included in count

**Impact**:
```python
# SUM: 100 + 0 + 200 = 300
# AVERAGE for %: (100 + 0 + 200) / 3 = 100  (includes zero in count)

# If File 2 was empty instead:
# AVERAGE: (100 + 200) / 2 = 150  (excludes empty from count)
```

**Conflict Severity**: ⚠️ MEDIUM (Can affect average calculations)

---

## 🔧 CONFLICT RESOLUTION STRATEGIES

### Auto-Resolution (System Handles)
1. ✅ Format standardization (percentage, currency, number)
2. ✅ Text-to-number conversion
3. ✅ Empty cell handling
4. ✅ Extra cells ignored
5. ✅ MergedCell instances skipped
6. ✅ Character stripping (commas, currency symbols)

### User Configuration Required
1. ⚙️ Stop on error vs Continue on error
2. ⚙️ Include formulas vs Ignore formulas
3. ⚙️ Include totals vs Exclude totals
4. ⚙️ Overwrite output formulas vs Preserve
5. ⚙️ Validation strictness levels
6. ⚙️ Range validation (min/max)

### Manual Intervention Required
1. 🛠️ File access issues (close files, fix permissions)
2. 🛠️ Corrupted files (repair or exclude)
3. 🛠️ Password protected files (remove protection)
4. 🛠️ Structure mismatches (fix file structure)
5. 🛠️ Merged cells (unmerge in source)
6. 🛠️ Wrong data types (fix data in source)

---

## 📈 CONFLICT PRIORITY MATRIX

| Conflict Type | Severity | Auto-Fix | User Action | Impact on Results |
|--------------|----------|----------|-------------|-------------------|
| File Open | 🔴 CRITICAL | ❌ No | Close file | Blocks processing |
| Corrupted File | 🔴 CRITICAL | ❌ No | Repair/exclude | Blocks processing |
| Password Protected | 🔴 CRITICAL | ❌ No | Remove password | Blocks processing |
| Merged Cells | 🔴 CRITICAL | ⚠️ Partial | Unmerge cells | Blocks/skips cells |
| Mixed Formats (Critical) | 🔴 HIGH | ⚠️ Partial | Fix source data | Data loss/incorrect |
| Formula in Template | 🔴 HIGH | ⚙️ Configurable | Review settings | May lose formulas |
| Total Row Duplication | 🔴 HIGH | ⚙️ Configurable | Review settings | Incorrect sums |
| Percentage Representation | ⚠️ MEDIUM | ✅ Yes | Verify results | May misinterpret |
| Structure Mismatch | ⚠️ MEDIUM | ⚠️ Partial | Standardize files | Missing data |
| Out of Range | ⚠️ MEDIUM | ⚙️ Configurable | Fix source data | Excluded values |
| Text in Numbers | ⚠️ MEDIUM | ⚙️ Configurable | Fix source data | Excluded values |
| Currency Mismatch | ✅ LOW | ✅ Yes | None | Auto-resolved |
| Empty Cells | ✅ LOW | ✅ Yes | None | Expected behavior |
| Extra Cells | ✅ LOW | ✅ Yes | None | Ignored |

---

## 🔍 DEBUGGING CHECKLIST

When consolidation produces unexpected results, check:

### For SUM Issues (Numbers/Currency):
- [ ] Are all source files using consistent number formats?
- [ ] Are there text values that look like numbers?
- [ ] Are formulas being included when they shouldn't be?
- [ ] Are total rows being double-counted?
- [ ] Are empty cells being treated as zeros?

### For AVERAGE Issues (Percentages):
- [ ] Are all source files using consistent percentage notation?
- [ ] Are values in percentage points (82.5) or decimals (0.825)?
- [ ] Are large numbers being misinterpreted as percentages?
- [ ] Is the count including or excluding empty cells?
- [ ] Are zeros being included in the average calculation?

### For Format Issues:
- [ ] Does template cell format match source cell formats?
- [ ] Are there mixed data types in the same cell coordinate?
- [ ] Are percentage cells clearly marked with % format?
- [ ] Are currency cells using consistent symbols?

### For File Issues:
- [ ] Are any files currently open in Excel?
- [ ] Are there permission/access issues?
- [ ] Are files corrupted or password-protected?
- [ ] Do all files have the same structure?

---

## 📝 RECOMMENDATIONS

### For Template Design:
1. **Use explicit formats**: Always apply clear number formats (0.00%, $#,##0.00)
2. **Avoid merged cells**: Use centering instead
3. **Document formulas**: Mark formula cells clearly
4. **Separate totals**: Put total rows in distinct locations

### For Source Files:
1. **Standardize formats**: All files should match template
2. **Use consistent notation**: All percentages as 82.5% or all as 0.825
3. **Avoid text**: Use actual numbers, not text that looks like numbers
4. **Unmerge cells**: Remove all merged cells
5. **Close before processing**: Always close files before consolidation

### For Settings Configuration:
1. **Enable auto-convert**: For flexible text-to-number conversion
2. **Set appropriate ranges**: Define min/max for validation
3. **Choose error handling**: Stop vs Continue based on data quality needs
4. **Review formula settings**: Include/exclude based on requirements
5. **Enable logging**: For troubleshooting issues

---

## END OF DOCUMENT
Version: 1.0
Last Updated: 2025-09-30
