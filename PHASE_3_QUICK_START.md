# Phase 3: Data Ingestion Quick Start

**Status:** Ready to Implement  
**Duration:** 2-3 hours  
**Goal:** Load economic data from Excel and CSV files

---

## 30-Second Overview

Phase 3 adds file upload endpoints that:
1. Accept Excel or CSV files
2. Parse data into tables
3. Validate data quality
4. Insert into database
5. Track ingestion status

---

## Quick Reference

```powershell
# 1. Create ingestion module structure
mkdir backend\ingestion\parsers

# 2. Create files (see Implementation)
# - backend/ingestion/__init__.py
# - backend/ingestion/parsers/base_parser.py
# - backend/ingestion/parsers/excel_parser.py
# - backend/ingestion/parsers/csv_parser.py
# - backend/ingestion/validators.py
# - backend/ingestion/processors.py
# - backend/app/api/ingestion.py

# 3. Create database migration
psql -U postgres -d survey_chat -f backend\migrations\003_add_ingestion_tables.sql

# 4. Test
python -m pytest backend/tests/test_ingestion.py

# 5. Start server
python -m uvicorn app.main:app --reload

# 6. Upload file
curl -X POST http://localhost:8000/api/ingestion/start \
  -F "file=@survey_2024.xlsx" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Step-by-Step Implementation

### Step 1: Create Ingestion Module Structure (5 minutes)

```powershell
mkdir backend\ingestion\parsers
mkdir backend\tests\ingestion

# Create __init__.py files
New-Item backend\ingestion\__init__.py
New-Item backend\ingestion\parsers\__init__.py
```

### Step 2: Create Base Parser (15 minutes)

Create `backend/ingestion/parsers/base_parser.py`:

```python
from abc import ABC, abstractmethod
from typing import List

class DataTable:
    """In-memory representation of a data table"""
    def __init__(self, name: str, headers: list, rows: list):
        self.name = name
        self.headers = headers
        self.rows = rows

class BaseParser(ABC):
    """Abstract base class for file parsers"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.errors = []
        self.warnings = []
    
    @abstractmethod
    def parse(self) -> List[DataTable]:
        """Parse file and return list of data tables"""
        pass
```

See: Skills/03_Phase3_Ingestion_Skills.md for full implementation

### Step 3: Create Excel Parser (15 minutes)

Create `backend/ingestion/parsers/excel_parser.py`:

Uses openpyxl to:
- Load workbook
- Detect tables in each sheet
- Extract headers and rows
- Return DataTable objects

See: Skills/03_Phase3_Ingestion_Skills.md for full code

### Step 4: Create CSV Parser (10 minutes)

Create `backend/ingestion/parsers/csv_parser.py`:

Uses csv library to:
- Read CSV file
- Parse headers and rows
- Handle encoding issues
- Return DataTable objects

See: Skills/03_Phase3_Ingestion_Skills.md for full code

### Step 5: Create Data Validator (15 minutes)

Create `backend/ingestion/validators.py`:

Validates:
- Header presence and uniqueness
- Row completeness
- Data type correctness
- Business rules

```python
class DataValidator:
    def __init__(self, data_table):
        self.data_table = data_table
        self.errors = []
        self.warnings = []
    
    def validate(self) -> bool:
        """Run all validations"""
        self._validate_headers()
        self._validate_rows()
        self._validate_data_types()
        return len(self.errors) == 0
```

### Step 6: Create Processor (15 minutes)

Create `backend/ingestion/processors.py`:

Handles:
- File parsing
- Data validation
- Database insertion
- Status tracking

### Step 7: Create Ingestion Routes (20 minutes)

Create `backend/app/api/ingestion.py`:

Endpoints:
- `POST /api/ingestion/start` - Upload and process file
- `GET /api/ingestion/status/{id}` - Get ingestion status
- `GET /api/ingestion/list` - List user's ingestions

### Step 8: Create Database Migration (10 minutes)

Create `backend/migrations/003_add_ingestion_tables.sql`:

Creates/modifies:
- data_files table
- data_sheets table
- data_tables table
- ingestion_runs table

### Step 9: Update Main App (2 minutes)

Update `backend/app/main.py`:

```python
from app.api import ingestion
app.include_router(ingestion.router, prefix="/api", tags=["Ingestion"])
```

### Step 10: Test (30 minutes)

```powershell
# Unit tests
python -m pytest backend/tests/test_ingestion.py

# Integration test
python -c "
from backend.ingestion.parsers.excel_parser import ExcelParser
parser = ExcelParser('test_data/survey.xlsx')
tables = parser.parse()
print(f'✓ Parsed {len(tables)} tables')
"

# API test
curl -X POST http://localhost:8000/api/ingestion/start \
  -F "file=@test_data/survey_2024.xlsx" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Success Criteria

- [ ] Ingestion module structure created
- [ ] Excel and CSV parsers working
- [ ] Data validation running without errors
- [ ] Database migration applied
- [ ] Ingestion endpoints responding
- [ ] Files uploadable and stored
- [ ] Data appearing in database
- [ ] Status tracking working
- [ ] Error reporting working
- [ ] Multiple file types supported

---

## Expected Test Data

### sample_survey.xlsx
```
Sheet1: General Info
Title | Year | Source
Survey | 2024 | Bureau

Sheet2: Data
Region | Q1 | Q2 | Q3 | Q4
NE | 3.2 | 3.1 | 3.4 | 3.3
SE | 2.8 | 2.9 | 3.0 | 3.1
```

### sample_data.csv
```
Region,Year,GDP,Employment
NE,2024,3.2,92.3
SE,2024,2.8,91.8
MW,2024,3.4,93.1
```

---

## Files to Create

| File | Lines | Time |
|------|-------|------|
| base_parser.py | 20 | 5 min |
| excel_parser.py | 80 | 15 min |
| csv_parser.py | 60 | 10 min |
| validators.py | 80 | 15 min |
| processors.py | 100 | 20 min |
| ingestion.py (routes) | 150 | 20 min |
| migration SQL | 50 | 10 min |
| tests | 200 | 30 min |
| **Total** | **740** | **2-3 hours** |

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| ImportError: openpyxl | `pip install openpyxl` |
| No tables detected | Check Excel has headers + data |
| UnicodeDecodeError | Try `encoding='latin-1'` |
| Database error | Run migration: `003_add_ingestion_tables.sql` |
| File not found | Check path matches upload location |

---

## Next Phase

After Phase 3 validation:
- **Phase 4:** PDF extraction
- **Phase 5:** Advanced data processing with LLM

---

*Phase 3 Quick Start - January 31, 2026*
