# Phase 4: Data Import & History Quick Start

**Status:** Ready to Implement  
**Duration:** 2-3 hours  
**Goal:** Persist imported data and track user ingestion history

---

## 30-Second Overview

Phase 4 adds:
1. Database persistence for imported data
2. User ingestion history tracking
3. Data retrieval API endpoints
4. Advanced business rule validation

---

## Quick Reference

```powershell
# 1. Apply migration
psql -U postgres -d survey_chat -f backend\migrations\004_add_data_storage.sql

# 2. Create files (see Implementation)
# - backend/ingestion/importers.py
# - backend/ingestion/advanced_validators.py
# - Update backend/app/api/ingestion.py
# - Update backend/app/models/__init__.py

# 3. Test
python -m pytest backend/tests/test_ingestion.py::TestDataImporter -v

# 4. Start server
python -m uvicorn app.main:app --reload

# 5. Upload and view history
curl -X POST http://localhost:8000/api/ingestion/start \
  -F "file=@survey.xlsx"

curl -X GET "http://localhost:8000/api/ingestion/list?token=YOUR_TOKEN"
```

---

## Step-by-Step Implementation

### Step 1: Database Migration (10 minutes)

Create `backend/migrations/004_add_data_storage.sql`:

Adds:
- `data_rows` table for storing individual rows
- Column updates to `data_files` for metadata
- JSONB support for flexible row storage
- Indexes for performance

Apply:
```powershell
psql -U postgres -d survey_chat -f backend\migrations\004_add_data_storage.sql
```

### Step 2: Create Data Importer (20 minutes)

Create `backend/ingestion/importers.py`:

```python
class DataImporter:
    """Import validated DataTable objects to database"""
    
    def __init__(self, session: Session, user_id: int):
        self.session = session
        self.user_id = user_id
    
    def import_tables(self, 
                     tables: List[DataTable],
                     file_name: str) -> IngestionRun:
        """Import all tables and return run status"""
        pass
```

Key methods:
- `import_tables()` - Main orchestrator
- `_import_table()` - Single table
- `_import_rows()` - Store individual rows

### Step 3: Create Advanced Validators (15 minutes)

Create `backend/ingestion/advanced_validators.py`:

Validators:
- `ReferenceValidator` - Cross-table relationships
- `RangeValidator` - Numeric constraints
- `DuplicateValidator` - Find duplicates

### Step 4: Update Processor (10 minutes)

Modify `backend/ingestion/processors.py`:

Change `_store_tables()` to:
```python
def _store_tables(self) -> List[DataTable]:
    """Store validated tables using DataImporter"""
    with get_db_context() as session:
        importer = DataImporter(session, self.user_id)
        run = importer.import_tables(valid_tables, file_name)
        return run
```

### Step 5: Update API Routes (20 minutes)

Extend `backend/app/api/ingestion.py`:

New/Updated Endpoints:
```
GET  /api/ingestion/list              - List user's ingestions
GET  /api/ingestion/status/{id}       - Get ingestion details
GET  /api/ingestion/data/{table_id}   - Get imported data
DELETE /api/ingestion/{id}            - Delete ingestion
POST /api/ingestion/start             - Updated to call importer
```

### Step 6: Update Models (10 minutes)

Modify `backend/app/models/__init__.py`:

Add `DataRow` model:
```python
class DataRow(Base):
    __tablename__ = "data_rows"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    data_table_id: Mapped[int] = mapped_column(ForeignKey("data_tables.id"))
    row_index: Mapped[int]
    row_data: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime]
```

### Step 7: Update Tests (20 minutes)

Extend `backend/tests/test_ingestion.py`:

Add test classes:
- `TestDataImporter` - Import functionality
- `TestHistoryAPI` - API endpoints
- `TestAdvancedValidators` - Business rules

### Step 8: Test Integration (30 minutes)

```powershell
# Unit tests
pytest backend/tests/test_ingestion.py::TestDataImporter -v

# Manual API test
$response = curl -X POST http://localhost:8000/api/ingestion/start `
  -F "file=@test.csv"

$ingestionId = $response.ingestion_id

# Check status
curl -X GET "http://localhost:8000/api/ingestion/status/$ingestionId"

# Get data
curl -X GET "http://localhost:8000/api/ingestion/list"
```

---

## Files to Create

| File | Lines | Time |
|------|-------|------|
| 004_add_data_storage.sql | 60 | 10 min |
| ingestion/importers.py | 150 | 20 min |
| ingestion/advanced_validators.py | 100 | 15 min |
| app/api/ingestion.py (updated) | +80 | 20 min |
| app/models/__init__.py (updated) | +30 | 10 min |
| tests/test_ingestion.py (updated) | +100 | 20 min |
| **Total** | **520** | **~2 hours** |

---

## API Usage

### Upload File (Phase 3 - Enhanced)
```bash
curl -X POST http://localhost:8000/api/ingestion/start \
  -F "file=@survey.xlsx" \
  -H "Authorization: Bearer JWT_TOKEN"

# New Response - includes ingestion ID
{
    "success": true,
    "ingestion_id": 42,
    "file_name": "survey.xlsx",
    "tables_parsed": 2,
    "tables_stored": 2,
    "records_stored": 150
}
```

### List Ingestions (NEW)
```bash
curl -X GET "http://localhost:8000/api/ingestion/list?token=JWT_TOKEN&limit=10"

{
    "total": 5,
    "ingestions": [
        {
            "id": 42,
            "file_name": "survey.xlsx",
            "tables": 2,
            "rows": 150,
            "status": "completed",
            "created": "2026-01-31T10:30:00Z"
        }
    ]
}
```

### Get Ingestion Details (NEW)
```bash
curl -X GET "http://localhost:8000/api/ingestion/status/42?token=JWT_TOKEN"

{
    "id": 42,
    "file_name": "survey.xlsx",
    "status": "completed",
    "tables_stored": 2,
    "records_stored": 150,
    "tables": [
        {
            "id": 101,
            "name": "Survey Data",
            "rows": 100,
            "columns": 5
        },
        {
            "id": 102,
            "name": "Metadata",
            "rows": 50,
            "columns": 3
        }
    ]
}
```

### Get Table Data (NEW)
```bash
curl -X GET "http://localhost:8000/api/ingestion/data/101?token=JWT_TOKEN&limit=20&offset=0"

{
    "total_rows": 100,
    "limit": 20,
    "offset": 0,
    "rows": [
        {"Region": "NE", "Year": 2024, "GDP": 3.2, "Employment": 92.3},
        {"Region": "SE", "Year": 2024, "GDP": 2.8, "Employment": 91.8}
    ]
}
```

### Delete Ingestion (NEW)
```bash
curl -X DELETE "http://localhost:8000/api/ingestion/42?token=JWT_TOKEN"

{
    "success": true,
    "deleted_id": 42,
    "rows_deleted": 150
}
```

---

## Data Model

### New Table: data_rows
```
id (BIGSERIAL)           - Primary key
data_table_id (INTEGER)  - Reference to data_tables
row_index (INTEGER)      - Row position (0-based)
row_data (JSONB)         - {"col1": val1, "col2": val2, ...}
created_at (TIMESTAMP)   - When inserted
```

### Updated Table: data_files
```
+ tables_found (INTEGER)   - How many tables detected
+ tables_valid (INTEGER)   - How many passed validation
+ tables_stored (INTEGER)  - How many persisted
+ rows_stored (INTEGER)    - Total rows persisted
```

---

## Database Queries

### Find User's Recent Ingestions
```sql
SELECT ir.id, df.file_name, ir.status, ir.records_stored, ir.created_at
FROM ingestion_runs ir
JOIN data_files df ON ir.data_file_id = df.id
WHERE ir.user_id = 5
ORDER BY ir.created_at DESC
LIMIT 10;
```

### Get Data from Imported Table
```sql
SELECT row_data->>'Region' as Region,
       row_data->>'Year' as Year,
       row_data->>'GDP' as GDP
FROM data_rows
WHERE data_table_id = 101
LIMIT 20;
```

### Find Duplicates
```sql
SELECT row_data, COUNT(*) as count
FROM data_rows
WHERE data_table_id = 101
GROUP BY row_data
HAVING COUNT(*) > 1;
```

---

## Testing

### Unit Tests
```powershell
pytest backend/tests/test_ingestion.py::TestDataImporter -v
pytest backend/tests/test_ingestion.py::TestHistoryAPI -v
pytest backend/tests/test_ingestion.py::TestAdvancedValidators -v
```

### Manual Integration Test
```powershell
# 1. Create test file
$csv = @"
Region,Year,GDP
NE,2024,3.2
SE,2024,2.8
"@
$csv | Out-File test.csv

# 2. Upload
$response = curl -X POST http://localhost:8000/api/ingestion/start `
  -F "file=@test.csv"

# 3. Check result
$response | ConvertFrom-Json | Format-Table

# 4. List ingestions
curl -X GET "http://localhost:8000/api/ingestion/list" | ConvertFrom-Json
```

---

## Success Criteria

- [ ] Migration applied successfully
- [ ] DataImporter class created
- [ ] Data persists in data_rows table
- [ ] User can list their ingestions
- [ ] User can view imported data
- [ ] Cascade delete working
- [ ] Tests passing
- [ ] API endpoints tested

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| "JSONB type not supported" | Update PostgreSQL to 9.4+ |
| "Foreign key violation" | Ensure data_table_id exists |
| "Out of memory" | Use bulk_insert_mappings for large files |
| "Permission denied" | Check database user permissions |

---

## Next Phase: Phase 5

Phase 5 will query Phase 4 data:
- Extract key insights
- Generate summaries
- Create briefing documents
- Train embeddings

---

*Phase 4 Quick Start - January 31, 2026*
