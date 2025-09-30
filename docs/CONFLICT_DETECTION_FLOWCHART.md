# Conflict Detection Flowchart

## Overall Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    START CONSOLIDATION                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: LOAD TEMPLATE                                      │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Open template file                                  │     │
│  │ ├─❌ Not found → CRITICAL ERROR (Stop)            │     │
│  │ ├─❌ Password protected → CRITICAL ERROR (Stop)   │     │
│  │ ├─❌ Corrupted → CRITICAL ERROR (Stop)            │     │
│  │ └─✅ Success → Continue                            │     │
│  │                                                      │     │
│  │ Scan template cells                                 │     │
│  │ For each cell with value or formatting:            │     │
│  │   ├─ Detect format type:                            │     │
│  │   │   ├─ Contains '%' → IS_PERCENTAGE (AVG)        │     │
│  │   │   ├─ Contains '$€£¥' → IS_CURRENCY (SUM)       │     │
│  │   │   ├─ Has number format → IS_NUMBER (SUM)       │     │
│  │   │   └─ Else → UNFORMATTED (SUM)                  │     │
│  │   ├─ Check if formula → HAS_FORMULA                │     │
│  │   ├─ Store format info → coord_format_info[coord]  │     │
│  │   └─ Store coordinate → template_coords            │     │
│  └────────────────────────────────────────────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: DISCOVER SOURCE FILES                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Scan excel_folder for files                        │     │
│  │ ├─ Filter .xlsx, .xls files                        │     │
│  │ ├─ Skip temp files (~$*)                           │     │
│  │ └─❌ No files found → CRITICAL ERROR (Stop)       │     │
│  └────────────────────────────────────────────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 3: FORMAT STANDARDIZATION                             │
│  ┌────────────────────────────────────────────────────┐     │
│  │ For each source file:                              │     │
│  │   ├─ Try open file                                 │     │
│  │   │   ├─❌ File open → Skip file, log error       │     │
│  │   │   ├─❌ Password → Skip file, log error        │     │
│  │   │   ├─❌ Corrupted → Skip file, log error       │     │
│  │   │   └─✅ Success → Continue                     │     │
│  │   │                                                 │     │
│  │   ├─ For each coord in coord_format_info:         │     │
│  │   │   ├─ Get cell from source file                │     │
│  │   │   ├─ Check if formula                          │     │
│  │   │   │   └─ If formula → SKIP (preserve)         │     │
│  │   │   │                                             │     │
│  │   │   ├─ If IS_PERCENTAGE:                         │     │
│  │   │   │   ├─ Apply percentage format               │     │
│  │   │   │   └─ Normalize value:                      │     │
│  │   │   │       ├─ If value > 1 → value/100         │     │
│  │   │   │       └─ If 0-1 → keep as is              │     │
│  │   │   │                                             │     │
│  │   │   ├─ If IS_CURRENCY:                           │     │
│  │   │   │   └─ Apply currency format                 │     │
│  │   │   │                                             │     │
│  │   │   └─ If IS_NUMBER:                             │     │
│  │   │       └─ Apply number format                   │     │
│  │   │                                                 │     │
│  │   └─ Save updated file                             │     │
│  └────────────────────────────────────────────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 4: VALUE EXTRACTION & ACCUMULATION                    │
│  ┌────────────────────────────────────────────────────┐     │
│  │ For each source file:                              │     │
│  │   ├─ Open file (data_only mode for formulas)      │     │
│  │   │   └─❌ Error → Log, skip file, continue       │     │
│  │   │                                                 │     │
│  │   ├─ Validate structure (if enabled)               │     │
│  │   │   └─❌ Mismatch → Error or warn (setting)     │     │
│  │   │                                                 │     │
│  │   └─ For each cell in worksheet:                   │     │
│  │       │                                             │     │
│  │       ├─ Get cell coordinate                       │     │
│  │       ├─ Check if in template_coords               │     │
│  │       │   └─ Not in template → SKIP               │     │
│  │       │                                             │     │
│  │       ├─ Get format_info for this coord            │     │
│  │       │                                             │     │
│  │       ├─ Check if formula                          │     │
│  │       │   ├─ If formula & !include_totals:         │     │
│  │       │   │   └─ Check if total cell → SKIP       │     │
│  │       │   └─ Use calculated value                  │     │
│  │       │                                             │     │
│  │       ├─ Process value by format type:             │     │
│  │       │   │                                         │     │
│  │       │   ├─ IS_PERCENTAGE:                        │     │
│  │       │   │   ├─ Call _process_percentage_value()  │     │
│  │       │   │   │   ├─ Normalize to % points         │     │
│  │       │   │   │   │   ├─ 0-1 → multiply by 100    │     │
│  │       │   │   │   │   └─ >1 → keep as is          │     │
│  │       │   │   │   ├─❌ Error → Return None         │     │
│  │       │   │   │   │   └─ stop_on_error → HALT     │     │
│  │       │   │   │   └─✅ Return Decimal value        │     │
│  │       │   │   │                                     │     │
│  │       │   ├─ IS_CURRENCY:                          │     │
│  │       │   │   ├─ Call _process_currency_value()    │     │
│  │       │   │   │   ├─ Strip currency symbols        │     │
│  │       │   │   │   ├─❌ Error → Return None         │     │
│  │       │   │   │   │   └─ stop_on_error → HALT     │     │
│  │       │   │   │   └─✅ Return Decimal value        │     │
│  │       │   │   │                                     │     │
│  │       │   ├─ IS_NUMBER:                            │     │
│  │       │   │   ├─ Call _process_number_value()      │     │
│  │       │   │   │   ├─ Strip commas, spaces          │     │
│  │       │   │   │   ├─❌ Error → Return None         │     │
│  │       │   │   │   │   └─ stop_on_error → HALT     │     │
│  │       │   │   │   └─✅ Return Decimal value        │     │
│  │       │   │   │                                     │     │
│  │       │   └─ DEFAULT:                              │     │
│  │       │       ├─ Call _process_default_value()     │     │
│  │       │       │   ├─ Try parse as number           │     │
│  │       │       │   └─ Return Decimal or None        │     │
│  │       │                                             │     │
│  │       ├─ Validate value (if enabled)               │     │
│  │       │   ├─ Check min/max range                   │     │
│  │       │   └─❌ Out of range:                       │     │
│  │       │       ├─ stop_on_error → HALT             │     │
│  │       │       └─ else → SKIP value                │     │
│  │       │                                             │     │
│  │       ├─ Accumulate based on format:               │     │
│  │       │   │                                         │     │
│  │       │   ├─ If consolidation_method='average':    │     │
│  │       │   │   ├─ totals[coord] += value           │     │
│  │       │   │   └─ percent_counts[coord] += 1       │     │
│  │       │   │                                         │     │
│  │       │   └─ Else (sum):                           │     │
│  │       │       └─ totals[coord] += value           │     │
│  │       │                                             │     │
│  │       └─ Track contribution:                       │     │
│  │           └─ contributions[coord][file] = value    │     │
│  └────────────────────────────────────────────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 5: CONSOLIDATION & OUTPUT                             │
│  ┌────────────────────────────────────────────────────┐     │
│  │ For each coordinate in totals:                     │     │
│  │   ├─ Get cell from output template                 │     │
│  │   ├─ Check if merged cell → SKIP                  │     │
│  │   │                                                 │     │
│  │   ├─ Check if formula in template:                 │     │
│  │   │   ├─ If !overwrite_output_formulas:            │     │
│  │   │   │   └─ SKIP (preserve formula)              │     │
│  │   │   └─ Else → Overwrite with consolidated value │     │
│  │   │                                                 │     │
│  │   ├─ Get format_info for this coord                │     │
│  │   ├─ Calculate final value:                        │     │
│  │   │   │                                             │     │
│  │   │   ├─ If consolidation_method='average':        │     │
│  │   │   │   ├─ count = percent_counts[coord]        │     │
│  │   │   │   ├─ avg = totals[coord] / count          │     │
│  │   │   │   ├─ cell.value = avg / 100 (to decimal)  │     │
│  │   │   │   └─ cell.number_format = template format │     │
│  │   │   │       (e.g., "0.00%")                      │     │
│  │   │   │                                             │     │
│  │   │   └─ Else (sum):                               │     │
│  │   │       ├─ cell.value = totals[coord]           │     │
│  │   │       └─ Apply currency/number format          │     │
│  │   │                                                 │     │
│  │   ├─ Generate comment:                             │     │
│  │   │   ├─ List all contributing files               │     │
│  │   │   ├─ Show individual values                    │     │
│  │   │   └─ Show total/average                        │     │
│  │   │                                                 │     │
│  │   └─ Apply orange border (visual indicator)        │     │
│  │                                                      │     │
│  │ Create "Contributions" sheet                        │     │
│  │ Save consolidated file                              │     │
│  │   └─❌ Error saving → CRITICAL ERROR (Stop)       │     │
│  └────────────────────────────────────────────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     ✅ SUCCESS                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Format Detection Decision Tree

```
                    ┌─────────────┐
                    │  Cell Found │
                    └──────┬──────┘
                           │
                           ▼
                  ┌────────────────┐
                  │ Get cell format│
                  │ (number_format)│
                  └────────┬───────┘
                           │
                           ▼
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
      ┌───────────────┐         ┌─────────────┐
      │ Contains '%'? │         │ No '%'      │
      └───────┬───────┘         └──────┬──────┘
              │                        │
          ✅ YES                      │
              │                        │
              ▼                        ▼
    ┌──────────────────┐    ┌──────────────────┐
    │ IS_PERCENTAGE    │    │ Contains $€£¥?   │
    │ consolidation:   │    └────────┬─────────┘
    │ 'average'        │             │
    │ Formula: AVG     │         ┌───┴───┐
    └──────────────────┘         │       │
                             ✅ YES    ❌ NO
                                 │       │
                                 ▼       ▼
                     ┌──────────────┐ ┌─────────────┐
                     │ IS_CURRENCY  │ │Has # pattern?│
                     │ consolidation:│ └─────┬───────┘
                     │ 'sum'        │       │
                     │ Formula: SUM │   ┌───┴───┐
                     └──────────────┘   │       │
                                    ✅ YES    ❌ NO
                                        │       │
                                        ▼       ▼
                            ┌──────────────┐ ┌──────────────┐
                            │ IS_NUMBER    │ │ UNFORMATTED  │
                            │ consolidation:│ │ consolidation:│
                            │ 'sum'        │ │ 'sum'        │
                            │ Formula: SUM │ │ Formula: SUM │
                            └──────────────┘ └──────────────┘
```

---

## Percentage Value Normalization Flow

```
┌─────────────────────────────────────────┐
│ Input: Cell value for percentage cell   │
└────────────────┬────────────────────────┘
                 │
                 ▼
        ┌────────┴────────┐
        │ Check value type │
        └────────┬─────────┘
                 │
     ┌───────────┼───────────┐
     │           │           │
     ▼           ▼           ▼
┌─────────┐ ┌────────┐ ┌─────────┐
│int/float│ │ string │ │  other  │
└────┬────┘ └───┬────┘ └────┬────┘
     │          │           │
     │          │           └──→ Return None
     │          │
     │          ▼
     │    ┌──────────────┐
     │    │ Ends with '%'?│
     │    └──────┬────────┘
     │           │
     │       ┌───┴───┐
     │       │       │
     │      YES     NO
     │       │       │
     │       ▼       ▼
     │  ┌────────┐ ┌────────────┐
     │  │Remove %│ │ Parse as   │
     │  │Parse to│ │ number     │
     │  │number  │ │            │
     │  └───┬────┘ └─────┬──────┘
     │      │            │
     │      └────┬───────┘
     │           │
     └───────────┼──────────────┐
                 │              │
                 ▼              │
        ┌────────────────┐     │
        │ Is 0 <= n <= 1?│     │
        └────────┬───────┘     │
                 │              │
            ┌────┴────┐         │
            │         │         │
           YES       NO         │
            │         │         │
            ▼         ▼         │
      ┌──────────┐ ┌───────┐   │
      │ n * 100  │ │ n     │   │
      │(decimal  │ │(already│  │
      │to %)     │ │in %)  │   │
      └────┬─────┘ └───┬───┘   │
           │           │       │
           └─────┬─────┘       │
                 │             │
                 ▼             │
          ┌────────────┐       │
          │Return value│       │
          │in % points │       │
          └────────────┘       │
                               │
                              ❌ Error
                               │
                               ▼
                        ┌──────────────┐
                        │ stop_on_error?│
                        └──────┬────────┘
                               │
                          ┌────┴────┐
                          │         │
                         YES       NO
                          │         │
                          ▼         ▼
                    ┌─────────┐ ┌──────────┐
                    │  HALT   │ │Return None│
                    │processing│ │ (skip cell)│
                    └─────────┘ └──────────┘

Example Normalizations:
  82.5    → 82.5 (already in % points)
  0.825   → 82.5 (0.825 * 100)
  "82.5%" → 82.5 (remove %, parse)
  "0.825" → 82.5 (parse, multiply by 100)
```

---

## Error Handling Decision Tree

```
                    ┌──────────────┐
                    │  Error Occurs │
                    └───────┬───────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  Classify Error   │
                  │ (check error msg) │
                  └─────────┬─────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌──────────────┐   ┌──────────────┐
│ File Access   │   │ Data Format  │   │ Structure    │
│ Errors        │   │ Errors       │   │ Errors       │
└───────┬───────┘   └──────┬───────┘   └──────┬───────┘
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐   ┌──────────────┐   ┌──────────────┐
│• File open    │   │• Text in num │   │• Wrong sheet │
│• Password     │   │• Bad %format │   │• Missing cols│
│• Corrupted    │   │• Invalid curr│   │• Extra rows  │
│• Permission   │   │• Range error │   │              │
└───────┬───────┘   └──────┬───────┘   └──────┬───────┘
        │                  │                  │
        │                  │                  │
        └────────┬─────────┴─────────┬────────┘
                 │                   │
                 ▼                   ▼
        ┌─────────────────┐   ┌─────────────────┐
        │ CRITICAL ERROR  │   │  HANDLED ERROR  │
        │ (always stops)  │   │  (configurable) │
        └────────┬────────┘   └────────┬────────┘
                 │                     │
                 │                     ▼
                 │            ┌─────────────────┐
                 │            │ stop_on_error?  │
                 │            └────────┬────────┘
                 │                     │
                 │                ┌────┴────┐
                 │                │         │
                 │               YES       NO
                 │                │         │
                 └────────────────┼─────────┘
                                  │         │
                                  ▼         ▼
                         ┌──────────┐  ┌──────────┐
                         │   HALT   │  │   LOG    │
                         │processing│  │ CONTINUE │
                         │Show error│  │processing│
                         └──────────┘  └──────────┘

CRITICAL ERRORS (Always Stop):
  • Template not found
  • Template password protected
  • Template corrupted
  • No Excel files in folder
  • Cannot save output file

HANDLED ERRORS (Configurable):
  • Individual file access issues
  • Data format mismatches
  • Structure validation failures
  • Range validation errors
  • Formula evaluation errors
```

---

## Consolidation Method Selection

```
┌──────────────────────────────────┐
│  For each cell coordinate        │
└────────────────┬─────────────────┘
                 │
                 ▼
      ┌──────────────────────┐
      │ Get format_info      │
      │ for this coordinate  │
      └──────────┬───────────┘
                 │
                 ▼
      ┌──────────────────────┐
      │ is_percentage = True?│
      └──────────┬───────────┘
                 │
            ┌────┴────┐
            │         │
           YES       NO
            │         │
            ▼         ▼
   ┌────────────┐  ┌──────────────┐
   │CONSOLIDATE │  │ CONSOLIDATE  │
   │with AVERAGE│  │  with SUM    │
   └─────┬──────┘  └──────┬───────┘
         │                │
         ▼                ▼
┌─────────────────┐ ┌──────────────────┐
│Calculation:     │ │Calculation:      │
│                 │ │                  │
│total = Σ values │ │result = Σ values │
│count = N files  │ │                  │
│avg = total/count│ │Apply format:     │
│                 │ │├─ Currency: $fmt │
│Convert:         │ │├─ Number: #,##0  │
│result = avg/100 │ │└─ Default: value │
│                 │ │                  │
│Format: 0.00%    │ │                  │
└─────────────────┘ └──────────────────┘

EXAMPLE: Cell G867

Template Format: 0.00% (percentage)
├─ Detected as IS_PERCENTAGE = True
├─ consolidation_method = 'average'
└─ Process:

File 1: 82.5 (% points)
File 2: 75.0 (% points)  
File 3: 90.0 (% points)
           │
           ▼
    total = 247.5
    count = 3
    avg = 82.5
           │
           ▼
    Excel value = 0.825 (82.5/100)
    Display: 82.5%


EXAMPLE: Cell B10

Template Format: $#,##0.00 (currency)
├─ Detected as IS_CURRENCY = True
├─ consolidation_method = 'sum'
└─ Process:

File 1: 1000
File 2: 1500
File 3: 750
           │
           ▼
    result = 3250
           │
           ▼
    Excel value = 3250
    Display: $3,250.00
```

---

## Comment Generation Flow

```
┌────────────────────────────────┐
│ For consolidated cell at coord │
└───────────────┬────────────────┘
                │
                ▼
     ┌──────────────────────┐
     │ Get contributions    │
     │ contributions[coord] │
     └──────────┬───────────┘
                │
                ▼
     ┌──────────────────────┐
     │ Any contributions?   │
     └──────────┬───────────┘
                │
           ┌────┴────┐
           │         │
          YES       NO
           │         │
           │         └──→ No comment
           │
           ▼
┌──────────────────────────┐
│ Build comment header:    │
│                          │
│ "Consolidation Summary"  │
│ "Cell: G867"             │
│                          │
│ Check format type:       │
└────────┬─────────────────┘
         │
    ┌────┴────┐
    │         │
 PERCENTAGE  OTHER
    │         │
    ▼         ▼
┌─────────┐ ┌──────────┐
│"Average:│ │"Total:   │
│ 82.5%"  │ │$3,250.00"│
└────┬────┘ └────┬─────┘
     │           │
     └─────┬─────┘
           │
           ▼
┌──────────────────────────┐
│ Add contributor section: │
│                          │
│ "Contributors:"          │
│ "file | value"           │
│ "-------------------"    │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ For each file:           │
│                          │
│ Format value by type:    │
│ ├─ Percentage: "82.5%"   │
│ ├─ Currency: "$1,000.00" │
│ └─ Number: "1,000.00"    │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Create Excel Comment:    │
│                          │
│ • Set author             │
│ • Set dimensions         │
│ • Truncate if >32KB      │
│ • Attach to cell         │
└──────────────────────────┘

EXAMPLE OUTPUT:

┌─────────────────────────┐
│ Consolidation Summary   │
│ Cell: G867              │
│ Average: 82.5% (3 files)│
│                         │
│ Contributors:           │
│ ----------------------  │
│ File1.xlsx  |  82.5%   │
│ File2.xlsx  |  75.0%   │
│ File3.xlsx  |  90.0%   │
└─────────────────────────┘
     (Hover in Excel to see)
```

---

## Settings Impact Matrix

```
┌─────────────────────────────────────────────────────────────┐
│                      SETTINGS IMPACT                         │
└─────────────────────────────────────────────────────────────┘

Setting: auto_convert_text
├─ TRUE:  "123" → 123 (convert and process)
└─ FALSE: "123" → Skip (text not allowed)

Setting: handle_percentages
├─ TRUE:  "50%" → 0.5 (convert percentage text)
└─ FALSE: "50%" → Skip (process as-is or skip)

Setting: include_totals
├─ TRUE:  Process all cells including "Total" rows
└─ FALSE: Skip cells with total indicators

Setting: ignore_formulas
├─ TRUE:  Skip cells with formulas
└─ FALSE: Use calculated value from formulas

Setting: validate_structure
├─ TRUE:  Check file matches template structure
└─ FALSE: Process any cells available

Setting: validate_data_types
├─ TRUE:  Verify data types match expectations
└─ FALSE: Attempt conversion without validation

Setting: validate_ranges
├─ TRUE:  Check values within min/max bounds
└─ FALSE: Accept any numeric value

Setting: stop_on_error
├─ TRUE:  First error halts entire process
└─ FALSE: Log errors, continue with other cells/files

Setting: overwrite_output_formulas
├─ TRUE:  Replace template formulas with consolidated values
└─ FALSE: Preserve template formulas, skip consolidation

Setting: read_only_mode
├─ TRUE:  Faster loading, formulas not evaluated
└─ FALSE: Load fully, formulas calculated
```

---

## END OF FLOWCHART DOCUMENT
Version: 1.0
Last Updated: 2025-09-30
