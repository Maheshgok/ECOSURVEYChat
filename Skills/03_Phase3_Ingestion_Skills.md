# Phase 3: Data Ingestion Skills

**Phase Duration:** 2-3 hours  
**Difficulty:** Medium-Hard  
**Prerequisites:** Phase 1-2 Complete + Sample Excel/CSV files  
**Objective:** Load economic data from Excel and CSV files into the database

---

## Table of Contents

1. [Data Ingestion Concepts](#data-ingestion-concepts)
2. [Architecture Overview](#architecture-overview)
3. [Excel Parser Implementation](#excel-parser-implementation)
4. [CSV Parser Implementation](#csv-parser-implementation)
5. [Data Validation](#data-validation)
6. [Ingestion API Endpoints](#ingestion-api-endpoints)
7. [Testing & Validation](#testing--validation)

---

## Data Ingestion Concepts

### What is Data Ingestion?

Data ingestion is the process of loading raw data from files into a structured database. For economic surveys:

```
Excel File (Survey Data)
    ↓
Parser (Extract rows/columns)
    ↓
Validator (Check data quality)
    ↓
Transformer (Format for database)
    ↓
Database Insert
    ↓
Indexing (Search optimization)
```

### Key Concepts

**Data File:** The source (Excel, CSV, PDF)  
**Data Sheet:** A worksheet within Excel or CSV section  
**Data Table:** A logical table within a sheet (e.g., Table1, Table2)  
**Data Row:** Individual record from the data  
**Ingestion Run:** A single import operation with status tracking

### Expected Data Formats

**Excel File Structure:**
```
Survey_2024.xlsx
├── Sheet1 (General Information)
│   └── Metadata: Title, Date, Source
├── Sheet2 (Data Table 1)
│   ├── Headers: Column1, Column2, Column3
│   └── Rows: Data values
└── Sheet3 (Data Table 2)
    ├── Headers: IndicatorA, IndicatorB
    └── Rows: Values by year
```

**CSV Structure:**
```
csv_file.csv
Header1,Header2,Header3
Value1,Value2,Value3
Value4,Value5,Value6
```

---

## Architecture Overview

```
┌────────────────────────────────────────────────────┐
│           Ingestion Module Structure               │
├────────────────────────────────────────────────────┤
│                                                    │
│  ingestion/                                        │
│  ├── __init__.py                                  │
│  ├── parsers/                                     │
│  │   ├── __init__.py                              │
│  │   ├── base_parser.py      (Abstract base)      │
│  │   ├── excel_parser.py     (Excel specific)     │
│  │   └── csv_parser.py       (CSV specific)       │
│  ├── validators.py            (Data validation)   │
│  ├── processors.py            (Data processing)   │
│  └── tasks.py                 (Background tasks)  │
│                                                    │
│  api/ingestion.py             (Endpoints)         │
│                                                    │
└────────────────────────────────────────────────────┘
```

### Data Flow

```
User Upload Request
    ↓
Endpoint (/api/ingestion/start)
    ↓
Parser Factory (detect file type)
    ├─→ ExcelParser
    └─→ CSVParser
    ↓
Parse File
    ↓
Validate Data
    ├─ Check data types
    ├─ Check required fields
    └─ Check business rules
    ↓
Transform Data
    ├─ Normalize column names
    ├─ Parse dates
    └─ Calculate derived fields
    ↓
Insert into Database
    ├─ Create DataFile record
    ├─ Create DataSheet records
    ├─ Create DataTable records
    └─ Create data rows
    ↓
Update Ingestion Status
    └─ Store summary: rows_imported, errors, warnings
```

---

## Excel Parser Implementation

### Using openpyxl Library

```python
# openpyxl is already in requirements.txt
from openpyxl import load_workbook
```

### Parser Interface

```python
class ExcelParser(BaseParser):
    """
    Parse Excel files and extract data into tables
    """
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.workbook = None
        self.errors = []
        self.warnings = []
    
    def parse(self) -> List[DataTable]:
        """
        Parse Excel file and return list of data tables
        
        Returns:
            List of DataTable objects with extracted data
        """
        self.workbook = load_workbook(self.file_path)
        data_tables = []
        
        for sheet_name in self.workbook.sheetnames:
            worksheet = self.workbook[sheet_name]
            
            # Detect tables in sheet
            tables = self._detect_tables(worksheet)
            
            for table in tables:
                data_table = self._parse_table(worksheet, table)
                data_tables.append(data_table)
        
        return data_tables
    
    def _detect_tables(self, worksheet) -> List[dict]:
        """
        Detect data tables within a worksheet
        
        A table is a contiguous block of data with:
        - Header row with column names
        - Data rows below header
        - Empty rows as separators
        """
        tables = []
        current_table = None
        
        for row_idx, row in enumerate(worksheet.iter_rows(min_row=1, values_only=False), 1):
            # Check if row has data
            has_data = any(cell.value is not None for cell in row)
            
            if has_data:
                if current_table is None:
                    # Start new table
                    current_table = {
                        'start_row': row_idx,
                        'headers': [cell.value for cell in row if cell.value]
                    }
            else:
                if current_table is not None:
                    # End current table
                    current_table['end_row'] = row_idx - 1
                    tables.append(current_table)
                    current_table = None
        
        # Handle last table if file ends with data
        if current_table is not None:
            current_table['end_row'] = worksheet.max_row
            tables.append(current_table)
        
        return tables
    
    def _parse_table(self, worksheet, table_def: dict):
        """
        Parse a single table from worksheet
        
        Returns:
            DataTable object with headers and rows
        """
        headers = table_def['headers']
        start_row = table_def['start_row']
        end_row = table_def['end_row']
        
        rows = []
        for row_idx in range(start_row + 1, end_row + 1):
            row_data = {}
            for col_idx, header in enumerate(headers, 1):
                cell = worksheet.cell(row=row_idx, column=col_idx)
                row_data[header] = cell.value
            rows.append(row_data)
        
        return DataTable(
            name=f"{worksheet.title}_table",
            headers=headers,
            rows=rows
        )
```

---

## CSV Parser Implementation

### Using Standard csv Library

```python
import csv
from typing import List

class CSVParser(BaseParser):
    """
    Parse CSV files and extract data
    """
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.encoding = 'utf-8'
        self.delimiter = ','
        self.errors = []
        self.warnings = []
    
    def parse(self) -> List[DataTable]:
        """
        Parse CSV file
        
        Returns:
            List with single DataTable object
        """
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                
                if reader.fieldnames is None:
                    raise ValueError("CSV file has no headers")
                
                headers = reader.fieldnames
                rows = []
                
                for row_num, row in enumerate(reader, 1):
                    try:
                        rows.append(dict(row))
                    except Exception as e:
                        self.errors.append(f"Row {row_num}: {str(e)}")
                
                return [DataTable(
                    name="csv_data",
                    headers=headers,
                    rows=rows
                )]
        
        except UnicodeDecodeError:
            # Try latin-1 encoding
            self.encoding = 'latin-1'
            return self.parse()
```

---

## Data Validation

### Validation Framework

```python
class DataValidator:
    """
    Validate data before inserting into database
    """
    
    def __init__(self, data_table: DataTable):
        self.data_table = data_table
        self.errors = []
        self.warnings = []
    
    def validate(self) -> bool:
        """
        Run all validations
        
        Returns:
            True if all validations pass, False otherwise
        """
        self._validate_headers()
        self._validate_rows()
        self._validate_data_types()
        
        return len(self.errors) == 0
    
    def _validate_headers(self):
        """Check headers are valid column names"""
        required_headers = []  # Can be customized per file type
        
        for header in self.data_table.headers:
            # Check for empty headers
            if not header or str(header).strip() == '':
                self.errors.append("Empty column header found")
            
            # Check for duplicate headers
            if self.data_table.headers.count(header) > 1:
                self.errors.append(f"Duplicate header: {header}")
    
    def _validate_rows(self):
        """Check rows have correct structure"""
        for row_num, row in enumerate(self.data_table.rows, 1):
            # Check row has expected number of columns
            if len(row) != len(self.data_table.headers):
                self.warnings.append(f"Row {row_num}: Column count mismatch")
            
            # Check no empty rows
            if all(v is None or str(v).strip() == '' for v in row.values()):
                self.warnings.append(f"Row {row_num}: Completely empty")
    
    def _validate_data_types(self):
        """Validate data types for known columns"""
        type_rules = {
            'year': int,
            'value': float,
            'date': str,  # Will parse to datetime
        }
        
        for row in self.data_table.rows:
            for column, expected_type in type_rules.items():
                if column in row and row[column] is not None:
                    try:
                        if expected_type == int:
                            int(row[column])
                        elif expected_type == float:
                            float(row[column])
                    except (ValueError, TypeError):
                        self.warnings.append(
                            f"Column '{column}' has invalid {expected_type.__name__}: {row[column]}"
                        )
```

---

## Ingestion API Endpoints

### Endpoint 1: Start Ingestion

```python
@router.post("/api/ingestion/start")
async def start_ingestion(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(SessionLocal)
):
    """
    Start data ingestion from uploaded file
    
    Request: Form data with file upload
    
    Response:
    {
        "ingestion_id": 123,
        "file_name": "survey_2024.xlsx",
        "status": "processing",
        "message": "Ingestion started"
    }
    """
    try:
        # 1. Save uploaded file
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        # 2. Create ingestion run
        ingestion_run = IngestionRun(
            file_name=file.filename,
            user_id=user.id,
            status="processing",
            started_at=datetime.utcnow()
        )
        db.add(ingestion_run)
        db.commit()
        db.refresh(ingestion_run)
        
        # 3. Start background task
        # (Or process synchronously for Phase 3)
        process_ingestion(file_path, ingestion_run.id, db)
        
        return {
            "ingestion_id": ingestion_run.id,
            "file_name": file.filename,
            "status": "processing"
        }
    
    except Exception as e:
        logger.error(f"Ingestion start error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Endpoint 2: Get Status

```python
@router.get("/api/ingestion/status/{ingestion_id}")
async def get_ingestion_status(
    ingestion_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(SessionLocal)
):
    """
    Get status of an ingestion run
    
    Response:
    {
        "id": 123,
        "file_name": "survey_2024.xlsx",
        "status": "completed",
        "rows_imported": 1500,
        "errors": [],
        "warnings": ["Column 'date' has invalid format in row 45"],
        "started_at": "2026-01-31T10:00:00",
        "completed_at": "2026-01-31T10:05:30"
    }
    """
    ingestion = db.query(IngestionRun).filter(
        IngestionRun.id == ingestion_id,
        IngestionRun.user_id == user.id
    ).first()
    
    if not ingestion:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    
    return {
        "id": ingestion.id,
        "file_name": ingestion.file_name,
        "status": ingestion.status,
        "rows_imported": ingestion.rows_imported,
        "errors": ingestion.errors or [],
        "warnings": ingestion.warnings or [],
        "started_at": ingestion.started_at.isoformat(),
        "completed_at": ingestion.completed_at.isoformat() if ingestion.completed_at else None
    }
```

---

## Testing & Validation

### Test 1: Create Sample Data Files

**test_data/survey_2024.xlsx:**
```
Sheet: Metadata
Title,Year,Source
Annual Economic Survey,2024,Bureau of Statistics

Sheet: Indicators
Indicator,2024Q1,2024Q2,2024Q3,2024Q4
GDP Growth,3.2,3.1,3.4,3.3
Inflation Rate,2.1,2.2,2.0,2.3
Unemployment,4.5,4.4,4.3,4.2
```

**test_data/survey_2024.csv:**
```
Region,Year,EmploymentRate,GDPGrowth
Northeast,2024,92.3,3.2
Southeast,2024,91.8,3.1
Midwest,2024,93.1,3.4
West,2024,92.8,3.3
```

### Test 2: Unit Tests

```python
import pytest
from backend.ingestion.parsers.excel_parser import ExcelParser
from backend.ingestion.validators import DataValidator

def test_excel_parser():
    """Test Excel parsing"""
    parser = ExcelParser("test_data/survey_2024.xlsx")
    tables = parser.parse()
    
    assert len(tables) == 2
    assert tables[0].name == "Metadata_table"
    assert len(tables[0].headers) == 3
    assert len(tables[0].rows) > 0

def test_csv_parser():
    """Test CSV parsing"""
    parser = CSVParser("test_data/survey_2024.csv")
    tables = parser.parse()
    
    assert len(tables) == 1
    assert "Region" in tables[0].headers
    assert len(tables[0].rows) == 4

def test_data_validation():
    """Test data validation"""
    parser = ExcelParser("test_data/survey_2024.xlsx")
    tables = parser.parse()
    
    validator = DataValidator(tables[0])
    assert validator.validate()
    assert len(validator.errors) == 0
```

### Test 3: Integration Test

```python
def test_end_to_end_ingestion():
    """Test complete ingestion pipeline"""
    # 1. Upload file
    with open("test_data/survey_2024.xlsx", "rb") as f:
        response = client.post(
            "/api/ingestion/start",
            files={"file": f},
            headers={"Authorization": f"Bearer {session_token}"}
        )
    
    assert response.status_code == 200
    ingestion_id = response.json()["ingestion_id"]
    
    # 2. Check status
    status_response = client.get(
        f"/api/ingestion/status/{ingestion_id}",
        headers={"Authorization": f"Bearer {session_token}"}
    )
    
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"
    
    # 3. Verify data in database
    db_session = SessionLocal()
    files = db_session.query(DataFile).filter(
        DataFile.file_name == "survey_2024.xlsx"
    ).all()
    
    assert len(files) > 0
```

---

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "openpyxl not found" | Dependency missing | `pip install openpyxl` |
| "UnicodeDecodeError" | Wrong file encoding | Try latin-1: `encoding='latin-1'` |
| "No tables detected" | File structure wrong | Check data has headers + rows |
| "Type mismatch" | String instead of number | Cast in validator |
| "Duplicate headers" | Column names repeated | Rename duplicate columns |

---

## Resources

- [openpyxl Documentation](https://openpyxl.readthedocs.io/)
- [CSV Module](https://docs.python.org/3/library/csv.html)
- [Data Validation Best Practices](https://en.wikipedia.org/wiki/Data_validation)
- [Excel File Format Specification](https://www.ecma-international.org/publications-and-standards/standards/ecma-376/)

---

*Phase 3 Skills Guide*  
*Created: January 31, 2026*  
*Status: Ready for Implementation*
