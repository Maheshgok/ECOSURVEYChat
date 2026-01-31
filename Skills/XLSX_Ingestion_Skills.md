# XLSX Ingestion Skills (Phase 3)

**Goal:** Deterministic multi-table, multi-panel detection for Economic Survey datasets

---

## 📋 Prerequisites

- Phase 1 (Database) completed
- Economic Survey XLSX files available
- Understanding of openpyxl library
- Test files: `tabchart1.xlsx`, `tab1.1.xlsx`

---

## 🎯 Critical Requirements

**This is the most complex phase. Must handle:**
1. Multi-sheet workbooks (PACK style: 20-50 sheets)
2. Multi-panel sheets (single sheet with Growth + Inflation sections)
3. Big-table workbooks (single huge time-series table)
4. Multi-row headers (up to 6 rows)
5. Mid-sheet terminators (Source, Note rows)
6. Number parsing (commas, percentages, negatives, NA values)

**STOP CONDITION:** `tabchart1.xlsx` Table I.1 MUST split into 2 panels

---

## 🎯 Tasks Breakdown

### **Task 3.1: Create Data Models**

Already in Phase 1, but verify:
- `data_files` table
- `data_sheets` table
- `data_tables` table with `table_json` and `table_long` JSONB fields

---

### **Task 3.2: Workbook Classifier**

**File: `ingestion/xlsx_ingest.py`**

```python
import openpyxl
from enum import Enum

class WorkbookType(Enum):
    PACK = "pack"  # Multiple charts/tables per workbook
    BIG_TABLE = "big_table"  # Single large time-series table

def classify_workbook(wb: openpyxl.Workbook) -> WorkbookType:
    """
    Classify workbook as PACK or BIG_TABLE.
    
    PACK indicators:
    - ≥5 sheets
    - Sheet names contain "Chart" or "Table"
    
    BIG_TABLE indicators:
    - Large used range (>100 rows)
    - Column A contains time keys (FY pattern)
    """
    sheet_count = len(wb.sheetnames)
    
    # Check for PACK indicators
    if sheet_count >= 5:
        return WorkbookType.PACK
    
    chart_table_sheets = [
        name for name in wb.sheetnames 
        if 'chart' in name.lower() or 'table' in name.lower()
    ]
    if len(chart_table_sheets) >= 3:
        return WorkbookType.PACK
    
    # Check for BIG_TABLE indicators
    for sheet in wb.worksheets:
        used_range = sheet.calculate_dimension()
        max_row = sheet.max_row
        
        if max_row > 100:
            # Check if col A has time patterns
            time_patterns = 0
            for row in range(1, min(20, max_row + 1)):
                cell_value = sheet.cell(row, 1).value
                if cell_value and is_time_key(str(cell_value)):
                    time_patterns += 1
            
            if time_patterns >= 5:
                return WorkbookType.BIG_TABLE
    
    # Default to PACK
    return WorkbookType.PACK

def is_time_key(text: str) -> bool:
    """Check if text matches time patterns like FY2023, 2023-24, Q1 2023"""
    import re
    patterns = [
        r'FY\s?\d{4}',
        r'\d{4}-\d{2,4}',
        r'Q[1-4]\s?\d{4}',
        r'[A-Z][a-z]{2}-\d{2}',  # Jan-23
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)
```

---

### **Task 3.3: BIG_TABLE Region Detector**

**File: `ingestion/xlsx_ingest.py`**

For workbooks classified as BIG_TABLE (single large time-series table), implement a single-region detector:

```python
def detect_big_table(sheet) -> List[TableRegion]:
    """
    Detect single large table in sheet.
    Assumes format:
    - Title row (row 1 or 2)
    - Header row (multi-row possible)
    - Data rows with time keys in column A
    - Terminators: Source/Note rows
    
    Returns: List with one TableRegion
    """
    max_row = sheet.max_row
    max_col = sheet.max_column
    
    # Find title row (first non-empty row)
    title_row = None
    for row in range(1, min(10, max_row + 1)):
        if get_cell_value(sheet, row, 1):
            title_row = row
            break
    
    if not title_row:
        return []
    
    title = get_row_text(sheet, title_row)
    
    # Find header start (row with column labels, typically after title)
    header_row = None
    for row in range(title_row + 1, min(title_row + 10, max_row + 1)):
        row_data = get_row_values(sheet, row)
        # Header row has mostly text values (not numbers/dates)
        text_count = sum(1 for v in row_data if isinstance(v, str) and v.strip())
        if text_count >= 2:  # At least 2 column headers
            header_row = row
            break
    
    if not header_row:
        return []
    
    # Detect time column (usually column A or B)
    time_col = None
    for col in range(1, min(5, max_col + 1)):  # Check first 4 columns
        # Look at first 10 data rows after header
        time_pattern_count = 0
        for row in range(header_row + 1, min(header_row + 11, max_row + 1)):
            val = get_cell_value(sheet, row, col)
            if val and is_time_key(str(val)):
                time_pattern_count += 1
        
        if time_pattern_count >= 5:
            time_col = col
            break
    
    if not time_col:
        # No time column found, use column A
        time_col = 1
    
    # Find data start (first row after header)
    data_start = header_row + 1
    
    # Find data end (row with terminator keywords or blank rows)
    data_end = data_start
    for row in range(data_start, max_row + 1):
        row_text = get_row_text(sheet, row).lower()
        
        # Stop at terminator keywords
        if any(kw in row_text for kw in ['source:', 'note:', 'notes:']):
            data_end = row - 1
            break
        
        # Stop at blank rows (3 consecutive)
        if is_blank_row(sheet, row) and is_blank_row(sheet, row + 1) and is_blank_row(sheet, row + 2):
            data_end = row - 1
            break
        
        data_end = row
    
    # Detect column range (first to last non-empty column in header)
    col_start = 1
    col_end = max_col
    for col in range(1, max_col + 1):
        val = get_cell_value(sheet, header_row, col)
        if val:
            col_start = col
            break
    
    for col in range(max_col, 0, -1):
        val = get_cell_value(sheet, header_row, col)
        if val:
            col_end = col
            break
    
    # Extract notes/source
    notes = []
    source = None
    for row in range(data_end + 1, min(data_end + 10, max_row + 1)):
        row_text = get_row_text(sheet, row)
        if row_text:
            if 'source:' in row_text.lower():
                source = row_text
            elif 'note' in row_text.lower():
                notes.append(row_text)
    
    return [TableRegion(
        title=title,
        sheet_name=sheet.title,
        title_row=title_row,
        header_row=header_row,
        data_start_row=data_start,
        data_end_row=data_end,
        col_start=col_start,
        col_end=col_end,
        notes=notes,
        source=source
    )]

def is_blank_row(sheet, row: int) -> bool:
    """Check if row is entirely blank"""
    for col in range(1, sheet.max_column + 1):
        if get_cell_value(sheet, row, col):
            return False
    return True
```

---

### **Task 3.4: PACK Sheet Detector (Multi-Panel)**

**Critical: Must detect and split panels**

```python
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class TableRegion:
    title: str
    sheet_name: str
    title_row: int
    header_row: int
    data_start_row: int
    data_end_row: int
    col_start: int
    col_end: int
    notes: List[str]
    source: Optional[str]

def detect_pack_tables(sheet) -> List[TableRegion]:
    """
    Detect one or more tables in a PACK sheet.
    
    Key logic:
    1. Find title row (contains "Chart" or "Table")
    2. Find header row (next non-empty row)
    3. Find data region (until blank/Source/Note)
    4. Check for mid-sheet panel splits
    """
    regions = []
    max_row = sheet.max_row
    max_col = sheet.max_column
    
    current_row = 1
    while current_row <= max_row:
        # Look for title row
        title_row = find_title_row(sheet, current_row, max_row)
        if not title_row:
            break
        
        title = get_row_text(sheet, title_row)
        
        # Find header row
        header_row = find_header_row(sheet, title_row + 1, max_row)
        if not header_row:
            current_row = title_row + 1
            continue
        
        # Find data region
        data_start = header_row + 1
        data_end, terminator_rows = find_data_end(sheet, data_start, max_row)
        
        # Extract notes/source from terminator rows
        notes, source = extract_metadata(sheet, terminator_rows)
        
        # Detect column range
        col_start, col_end = detect_column_range(sheet, header_row, data_end)
        
        # Check for mid-sheet panel split
        panels = detect_panels(sheet, header_row, data_start, data_end, col_start, col_end)
        
        if panels:
            # Split into multiple regions
            for panel_title, panel_start, panel_end in panels:
                regions.append(TableRegion(
                    title=f"{title} - {panel_title}",
                    sheet_name=sheet.title,
                    title_row=title_row,
                    header_row=header_row,
                    data_start_row=panel_start,
                    data_end_row=panel_end,
                    col_start=col_start,
                    col_end=col_end,
                    notes=notes,
                    source=source
                ))
        else:
            # Single region
            regions.append(TableRegion(
                title=title,
                sheet_name=sheet.title,
                title_row=title_row,
                header_row=header_row,
                data_start_row=data_start,
                data_end_row=data_end,
                col_start=col_start,
                col_end=col_end,
                notes=notes,
                source=source
            ))
        
        # Move to next potential table
        current_row = data_end + len(terminator_rows) + 1
    
    return regions

def find_title_row(sheet, start_row: int, max_row: int) -> Optional[int]:
    """Find row containing 'Chart' or 'Table'"""
    for row in range(start_row, max_row + 1):
        text = get_row_text(sheet, row).lower()
        if 'chart' in text or 'table' in text:
            return row
    return None

def find_header_row(sheet, start_row: int, max_row: int) -> Optional[int]:
    """Find first non-empty row after title"""
    for row in range(start_row, min(start_row + 10, max_row + 1)):
        if not is_empty_row(sheet, row):
            return row
    return None

def find_data_end(sheet, start_row: int, max_row: int) -> Tuple[int, List[int]]:
    """
    Find end of data region.
    Terminates on: blank row, Source, Note, or next title.
    Returns: (last_data_row, list of terminator row numbers)
    """
    terminator_rows = []
    for row in range(start_row, max_row + 1):
        text = get_row_text(sheet, row).lower()
        
        if is_empty_row(sheet, row):
            return row - 1, terminator_rows
        
        if any(keyword in text for keyword in ['source:', 'note:', 'chart', 'table']):
            if 'chart' in text or 'table' in text:
                # Next table starting
                return row - 1, terminator_rows
            else:
                # Source/Note row
                terminator_rows.append(row)
                # Check if more terminators follow
                continue
        
        # If we've collected terminators and now hit data again, we're done
        if terminator_rows and not any(kw in text for kw in ['source:', 'note:']):
            return row - 1, terminator_rows
    
    return max_row, terminator_rows

def detect_panels(sheet, header_row: int, data_start: int, data_end: int, 
                  col_start: int, col_end: int) -> Optional[List[Tuple[str, int, int]]]:
    """
    Detect if data region contains multiple panels.
    
    Panel indicators:
    - Repeated header pattern mid-data
    - Section labels like "Growth", "Inflation"
    - Blank row followed by new header
    
    Returns: [(panel_name, start_row, end_row), ...] or None
    """
    panels = []
    header_pattern = get_row_pattern(sheet, header_row, col_start, col_end)
    
    current_panel_start = data_start
    panel_name = None
    
    for row in range(data_start, data_end + 1):
        row_text = get_row_text(sheet, row, col_start, col_end).lower()
        
        # Check for section label (single cell with text, rest empty)
        if is_section_label(sheet, row, col_start, col_end):
            if panel_name:
                # End previous panel
                panels.append((panel_name, current_panel_start, row - 1))
            
            panel_name = get_cell_value(sheet, row, col_start)
            current_panel_start = row + 1
            continue
        
        # Check for repeated header
        if row > data_start and get_row_pattern(sheet, row, col_start, col_end) == header_pattern:
            if panel_name:
                panels.append((panel_name, current_panel_start, row - 1))
            else:
                panels.append(("Panel 1", data_start, row - 1))
            
            panel_name = "Panel " + str(len(panels) + 1)
            current_panel_start = row + 1
    
    # Close last panel
    if panel_name and current_panel_start <= data_end:
        panels.append((panel_name, current_panel_start, data_end))
    
    return panels if len(panels) > 1 else None

def is_section_label(sheet, row: int, col_start: int, col_end: int) -> bool:
    """Check if row is a section label (one cell with text, rest empty)"""
    non_empty_count = 0
    first_value = None
    
    for col in range(col_start, col_end + 1):
        val = get_cell_value(sheet, row, col)
        if val:
            non_empty_count += 1
            if not first_value:
                first_value = val
    
    # Section label if: exactly 1 non-empty cell, and it's text (not number)
    if non_empty_count == 1 and first_value:
        return isinstance(first_value, str) and not is_numeric(first_value)
    
    return False
```

---

### **Task 3.4: Multi-Row Header Detection**

```python
def detect_multi_row_header(sheet, header_start_row: int, max_rows: int = 6) -> Tuple[int, List[List[str]]]:
    """
    Detect multi-row headers (cap at 6 rows).
    
    Returns: (num_header_rows, header_matrix)
    """
    header_rows = []
    
    for i in range(max_rows):
        row_num = header_start_row + i
        row_data = get_row_values(sheet, row_num)
        
        # Stop if row looks like data (mostly numbers)
        if is_data_row(row_data):
            break
        
        header_rows.append(row_data)
    
    if not header_rows:
        return 0, []
    
    return len(header_rows), header_rows

def flatten_multi_row_header(header_matrix: List[List[str]]) -> List[str]:
    """
    Flatten multi-row header into single row.
    
    Strategy:
    - Merge columns vertically with " - "
    - Handle merged cells (forward-fill)
    """
    if not header_matrix:
        return []
    
    num_cols = max(len(row) for row in header_matrix)
    flattened = []
    
    for col in range(num_cols):
        col_values = []
        for row in header_matrix:
            if col < len(row) and row[col]:
                val = str(row[col]).strip()
                if val and val not in col_values:
                    col_values.append(val)
        
        flattened.append(" - ".join(col_values) if col_values else f"Column{col}")
    
    return flattened
```

---

### **Task 3.5: Number Parsing**

```python
import re
from typing import Union, Optional

def parse_number(value: any) -> Optional[Union[int, float]]:
    """
    Parse number with rules:
    - Remove commas: "1,234.56" → 1234.56
    - Parse percentages: "5.2%" → 5.2
    - Parse negatives: "(1.2)" → -1.2
    - Handle NA: "NA", "-", "…" → None
    """
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        return value
    
    text = str(value).strip()
    
    # Handle NA values
    if text.lower() in ['na', 'n/a', '-', '…', '', 'nil']:
        return None
    
    # Remove commas
    text = text.replace(',', '')
    
    # Handle percentages
    is_percent = '%' in text
    text = text.replace('%', '')
    
    # Handle parentheses as negative
    if text.startswith('(') and text.endswith(')'):
        text = '-' + text[1:-1]
    
    # Try to parse
    try:
        num = float(text)
        return num
    except ValueError:
        return None  # Unparseable, keep as string
```

---

### **Task 3.5a: Value Typing Rules**

**CRITICAL:** Define exactly what becomes numeric, null, or string to prevent garbage in indicator registry.

**Typing Decision Tree:**

| Input Example | Type Result | Rule |
|---------------|-------------|------|
| `12.3` | `float` | Parseable number |
| `(12.3)` | `float` (-12.3) | Parentheses = negative |
| `5.2%` | `float` (5.2) | Strip % sign |
| `1,234.56` | `float` (1234.56) | Remove commas |
| `NA`, `-`, `…`, `n.a.` | `null` | NA tokens |
| `12.3*` | `float` (12.3) + footnote marker | Strip footnote, flag marker |
| `10–12`, `10-12` | `string` | Range → keep as string, tag as range |
| `<5`, `>100` | `string` | Inequality → keep as string |
| Empty cell | `null` | No value |
| Text like "India" | `string` | Non-numeric text |

**Implementation:**

```python
def parse_value_with_type(val) -> dict:
    """
    Parse cell value with explicit type tagging.
    
    Returns:
    {
        "value": <typed_value>,
        "type": "numeric" | "null" | "string" | "range" | "inequality",
        "footnote_marker": "*" | "†" | None,
        "original": <original_value>
    }
    """
    if val is None or val == '':
        return {"value": None, "type": "null", "footnote_marker": None, "original": val}
    
    if isinstance(val, (int, float)):
        return {"value": float(val), "type": "numeric", "footnote_marker": None, "original": val}
    
    text = str(val).strip()
    
    # Check for NA tokens
    na_tokens = ['na', 'n.a.', 'n.a', '-', '…', '—', 'nil', 'not available']
    if text.lower() in na_tokens:
        return {"value": None, "type": "null", "footnote_marker": None, "original": val}
    
    # Check for footnote markers
    footnote_marker = None
    for marker in ['*', '†', '‡', '§', '¶', '**']:
        if text.endswith(marker):
            footnote_marker = marker
            text = text[:-len(marker)].strip()
            break
    
    # Check for ranges (10–12, 10-12)
    if '–' in text or (text.count('-') == 1 and not text.startswith('-')):
        return {"value": text, "type": "range", "footnote_marker": footnote_marker, "original": val}
    
    # Check for inequalities (<5, >100, ≤10, ≥20)
    if any(text.startswith(op) for op in ['<', '>', '≤', '≥', '<=', '>=']):
        return {"value": text, "type": "inequality", "footnote_marker": footnote_marker, "original": val}
    
    # Try numeric parsing
    parsed_num = parse_number(text)
    if parsed_num is not None:
        return {"value": parsed_num, "type": "numeric", "footnote_marker": footnote_marker, "original": val}
    
    # Default: string
    return {"value": text, "type": "string", "footnote_marker": footnote_marker, "original": val}
```

**Usage in extraction:**

```python
def extract_table_json_typed(sheet, region: TableRegion) -> dict:
    """Extract table with explicit type annotations"""
    headers = flatten_multi_row_header(...)
    
    rows = []
    for row_num in range(region.data_start_row, region.data_end_row + 1):
        row_data = []
        for col in range(region.col_start, region.col_end + 1):
            val = get_cell_value(sheet, row_num, col)
            parsed = parse_value_with_type(val)
            row_data.append(parsed)
        rows.append(row_data)
    
    return {"headers": headers, "rows": rows}
```

**Why this matters:**
- Indicator registry expects numeric values only
- Ranges/inequalities need special handling (don't compute YoY on ">100")
- Footnotes must be preserved for evidence context
- Without explicit typing, you'll get SQL type errors or wrong computations

---

### **Task 3.6: Table Normalization to JSON**

```python
def extract_table_json(sheet, region: TableRegion) -> dict:
    """
    Extract table as nested JSON structure.
    
    Returns:
    {
        "headers": [...],
        "rows": [[...], [...], ...]
    }
    """
    # Detect multi-row header
    num_header_rows, header_matrix = detect_multi_row_header(
        sheet, region.header_row
    )
    
    headers = flatten_multi_row_header(header_matrix)
    
    # Extract data rows
    rows = []
    for row_num in range(region.data_start_row, region.data_end_row + 1):
        row_data = []
        for col in range(region.col_start, region.col_end + 1):
            val = get_cell_value(sheet, row_num, col)
            parsed = parse_number(val)
            row_data.append(parsed if parsed is not None else val)
        rows.append(row_data)
    
    return {
        "headers": headers,
        "rows": rows
    }
```

---

### **Task 3.7: Table Normalization to Long Format**

```python
def extract_table_long(sheet, region: TableRegion, table_json: dict, 
                       corpus_id: int, file_id: int) -> List[dict]:
    """
    Convert table to long format records.
    
    Each record:
    {
        "time": "FY2023",
        "geo": "India",
        "indicator": "GDP Growth",
        "measure": "YoY %",
        "value": 7.2,
        "unit": "percent",
        "provenance": {...}
    }
    """
    headers = table_json["headers"]
    rows = table_json["rows"]
    
    records = []
    
    # Detect column roles
    time_col = detect_time_column(headers, rows)
    geo_col = detect_geo_column(headers, rows)
    indicator_cols = [i for i in range(len(headers)) 
                      if i not in [time_col, geo_col]]
    
    for row_idx, row in enumerate(rows):
        time_val = row[time_col] if time_col is not None else None
        geo_val = row[geo_col] if geo_col is not None else "All India"
        
        for col_idx in indicator_cols:
            value = row[col_idx]
            if value is None or value == '':
                continue
            
            record = {
                "time": time_val,
                "geo": geo_val,
                "indicator": headers[col_idx],
                "measure": detect_measure(headers[col_idx]),
                "value": value,
                "unit": detect_unit(headers[col_idx], value),
                "provenance": {
                    "corpus_id": corpus_id,
                    "file_id": file_id,
                    "sheet": region.sheet_name,
                    "table": region.title,
                    "row": row_idx,
                    "col": col_idx
                }
            }
            records.append(record)
    
    return records
```

---

### **Task 3.8: Main Ingestion Script**

```python
# ingestion/xlsx_ingest.py

import sys
from pathlib import Path
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.data import DataFile, DataSheet, DataTable

def ingest_xlsx_file(file_path: str, corpus_id: int):
    """Main ingestion entry point"""
    wb = openpyxl.load_workbook(file_path, data_only=True)
    db = SessionLocal()
    
    try:
        # Create data_file record
        file_record = DataFile(
            corpus_id=corpus_id,
            filename=Path(file_path).name,
            path=file_path
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)
        
        # Classify workbook
        wb_type = classify_workbook(wb)
        print(f"Workbook type: {wb_type.value}")
        
        # Process sheets
        for sheet in wb.worksheets:
            process_sheet(db, wb_type, sheet, corpus_id, file_record.id)
        
        print(f"✅ Ingested {file_path}")
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def process_sheet(db: Session, wb_type: WorkbookType, sheet, 
                  corpus_id: int, file_id: int):
    """Process single sheet"""
    # Create sheet record
    sheet_record = DataSheet(
        file_id=file_id,
        sheet_name=sheet.title,
        sheet_index=sheet._idx,
        metadata={}
    )
    db.add(sheet_record)
    db.commit()
    db.refresh(sheet_record)
    
    # Detect tables
    if wb_type == WorkbookType.PACK:
        regions = detect_pack_tables(sheet)
    else:
        regions = detect_big_table(sheet)
    
    # Process each region
    for region in regions:
        table_json = extract_table_json(sheet, region)
        table_long = extract_table_long(sheet, region, table_json, corpus_id, file_id)
        
        # Compute A1 range
        range_a1 = f"{region.sheet_name}!{get_cell_address(region.title_row, region.col_start)}:{get_cell_address(region.data_end_row, region.col_end)}"
        
        # Create data_table record
        table_record = DataTable(
            file_id=file_id,
            sheet_id=sheet_record.id,
            title=region.title,
            table_name=sanitize_table_name(region.title),
            range_a1=range_a1,
            header_rows=region.header_row - region.title_row,
            units=detect_unit_from_region(region),
            notes="\n".join(region.notes) if region.notes else None,
            table_json=table_json,
            table_long={"records": table_long},
            confidence=0.9
        )
        db.add(table_record)
    
    db.commit()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m ingestion.xlsx_ingest <file_path> <corpus_id>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    corpus_id = int(sys.argv[2])
    
    ingest_xlsx_file(file_path, corpus_id)
```

---

## ✅ Acceptance Criteria

### **Test 1: Panel Split (CRITICAL)**
```bash
python -m ingestion.xlsx_ingest tabchart1.xlsx 1
```

**Verify:**
```sql
SELECT title, range_a1 FROM data_tables 
WHERE file_id = (SELECT id FROM data_files WHERE filename = 'tabchart1.xlsx');
```

**Expected: 2 rows in data_tables where titles contain "Growth" and "Inflation"**
- Both tables must have non-null `range_a1` values
- Both tables must have `table_json` and `table_long` populated
- Example output (exact ranges will vary):
  - `Table I.1 - Growth | Sheet1!A1:F20`
  - `Table I.1 - Inflation | Sheet1!A21:F40`

**STOP CONDITION:** If panel split doesn't work (only 1 table returned), investigation required.

Table I.1 - Inflation | Sheet1!A21:F40
```

**STOP CONDITION:** If only 1 table returned → FIX panel detection

### **Test 2: Big Table**
```bash
python -m ingestion.xlsx_ingest tab1.1.xlsx 1
```

**Expected:** 1 data_table with >100 rows

### **Test 3: table_long Format**
```sql
SELECT table_long->'records'->0 FROM data_tables LIMIT 1;
```

**Expected:**
```json
{
  "time": "FY2023",
  "geo": "All India",
  "indicator": "GDP Growth",
  "measure": "YoY %",
  "value": 7.2,
  "unit": "percent",
  "provenance": {...}
}
```

---

## 🎯 Deliverables Checklist

- [ ] Workbook classifier (PACK vs BIG_TABLE)
- [ ] PACK detector with panel splitting
- [ ] BIG_TABLE detector
- [ ] Multi-row header detection (cap at 6)
- [ ] Number parser (commas, %, negatives, NA)
- [ ] Table JSON extractor
- [ ] Table long-format converter
- [ ] Main ingestion script
- [ ] `tabchart1.xlsx` splits into 2 tables
- [ ] `tab1.1.xlsx` imports correctly
- [ ] All tables have `range_a1`, `table_json`, `table_long`

---

## 🔗 Next Phase

Once all deliverables complete and stop condition verified:
- **Phase 4: Indicator Skills** (build indicators from table_long)
