# XLSX Ingestion Common Errors (Phase 3)

**Reference:** Skills/XLSX_Ingestion_Skills.md

---

## Error 1: Panel Split Fails (STOP CONDITION)

**Symptom:** Table I.1 in `tabchart1.xlsx` creates only 1 data_table instead of 2

**Cause:** `detect_panels()` not detecting mid-sheet section labels ("Growth", "Inflation")

**Fix:**
```python
# In detect_panels(), check for:
1. Row with exactly 1 non-empty cell (first column)
2. Cell value is string (not number)
3. Next row has data pattern

# Example:
def is_section_label(sheet, row, col_start, col_end):
    first_val = get_cell_value(sheet, row, col_start)
    if not first_val or not isinstance(first_val, str):
        return False
    
    # Rest of row should be empty
    for col in range(col_start + 1, col_end + 1):
        if get_cell_value(sheet, row, col):
            return False
    
    return True
```

**Verification:**
```sql
SELECT COUNT(*) FROM data_tables WHERE file_id = (SELECT id FROM data_files WHERE filename = 'tabchart1.xlsx');
```
Must return 2.

---

## Error 2: Multi-Row Header Fails

**Symptom:** Column headers like "GDP / Growth" appear as "GDP" (missing second row)

**Cause:** `detect_multi_row_header()` stops too early or doesn't flatten correctly

**Fix:**
```python
# Flatten with " - " separator
headers = []
for col_idx in range(len(header_matrix[0])):
    parts = [row[col_idx] for row in header_matrix if row[col_idx]]
    headers.append(" - ".join(parts))
```

---

## Error 3: Number Parsing Inconsistency

**Symptom:** "12.3*" stored as string, not parsed as 12.3

**Cause:** Footnote marker not stripped before parsing

**Fix:**
```python
# Strip footnote markers FIRST
for marker in ['*', '†', '‡']:
    if text.endswith(marker):
        footnote_marker = marker
        text = text[:-1].strip()
        break

# THEN parse number
parsed = parse_number(text)
```

---

## Error 4: BIG_TABLE Detector Missing

**Symptom:** `detect_big_table(sheet)` not defined, causes NameError

**Cause:** Function referenced but not implemented

**Fix:** See Task 3.3 in XLSX_Ingestion_Skills.md for full implementation

---

## Error 5: Value Type Confusion

**Symptom:** Indicator registry has mix of strings and numbers for same indicator

**Cause:** No explicit type tagging

**Fix:** Use `parse_value_with_type()` from Task 3.5a to explicitly tag numeric vs string vs range

---

## Error 6: Time Column Not Detected

**Symptom:** BIG_TABLE ingestion fails to find time column

**Cause:** `is_time_key()` patterns too strict

**Fix:**
```python
def is_time_key(text: str) -> bool:
    patterns = [
        r'FY\s?\d{4}',         # FY2023
        r'\d{4}-\d{2,4}',      # 2023-24
        r'Q[1-4]\s?\d{4}',     # Q1 2023
        r'[A-Z][a-z]{2}-\d{2}', # Jan-23
        r'^\d{4}$',            # 2023
    ]
    return any(re.search(p, text) for p in patterns)
```

---

## Error 7: Workbook Classification Wrong

**Symptom:** PACK workbook classified as BIG_TABLE (or vice versa)

**Cause:** Thresholds too rigid

**Fix:**
```python
# PACK if:
- sheet_count >= 5 OR
- >= 3 sheets with "Table"/"Chart" in name

# BIG_TABLE if:
- max_row > 100 AND
- >= 5 time patterns in column A
```

---

## Error 8: Idempotency Fails

**Symptom:** Re-running ingestion creates duplicate data_tables

**Cause:** No uniqueness check

**Fix:**
```python
# Before inserting, check:
existing = db.query(DataTable).filter(
    DataTable.file_id == file_id,
    DataTable.title == title
).first()

if existing:
    print(f"⚠️  Table {title} already exists, skipping")
    continue
```

---

## Error 9: Notes/Source Extraction Fails

**Symptom:** `notes` and `source` fields are null

**Cause:** Terminator detection not finding "Source:" or "Note:" rows

**Fix:**
```python
# Case-insensitive search
row_text = get_row_text(sheet, row).lower()
if 'source:' in row_text:
    source = get_row_text(sheet, row)
elif 'note' in row_text:
    notes.append(get_row_text(sheet, row))
```

---

## Error 10: Empty Cells Cause IndexError

**Symptom:** `IndexError: list index out of range` when accessing row_data

**Cause:** Row has fewer cells than expected

**Fix:**
```python
def get_cell_value(sheet, row, col):
    try:
        return sheet.cell(row, col).value
    except:
        return None
```

---

## Error 11: Table Long Format Has Duplicates

**Symptom:** indicator_series creation fails due to duplicate (time, geo, indicator) keys

**Cause:** Panel splitting creates overlapping rows

**Fix:** Add unique constraint validation:
```python
# In extract_table_long(), track seen keys
seen = set()
for record in records:
    key = (record['time'], record['geo'], record['indicator'])
    if key in seen:
        print(f"⚠️  Duplicate: {key}")
        continue
    seen.add(key)
```

---

## Error 12: Range A1 Incorrect

**Symptom:** `range_a1` like "Sheet1!A1:A1" (single cell)

**Cause:** col_end calculation wrong

**Fix:**
```python
# Detect last non-empty column in data region, not header
col_end = col_start
for row in range(data_start, data_end + 1):
    for col in range(col_start, max_col + 1):
        if get_cell_value(sheet, row, col):
            col_end = max(col_end, col)
```

---

## Debugging Checklist

- [ ] Panel split test passing (tabchart1.xlsx → 2 tables)
- [ ] Multi-row headers flattened correctly
- [ ] Footnote markers stripped before parsing
- [ ] BIG_TABLE detector implemented
- [ ] Value types explicitly tagged
- [ ] Time column detected for BIG_TABLE
- [ ] Workbook classification correct
- [ ] Idempotency working (no duplicates on re-run)
- [ ] Notes/source extracted
- [ ] No IndexError on empty cells
- [ ] Table long format has no duplicates
- [ ] Range A1 spans full table

---

## Escalation

If panel split still fails after fixes:
1. Print all rows in suspect region
2. Check `is_section_label()` returns True for "Growth"/"Inflation" rows
3. Verify `data_start` and `data_end` for each panel
4. Manually inspect `tabchart1.xlsx` to confirm expected structure
