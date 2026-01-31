# Phase 4: Data Import & History Skills Guide

**Status:** Ready to Implement  
**Estimated Duration:** 2-3 hours  
**Goal:** Persist ingested data and track user's file upload history

---

## Phase Overview

Phase 4 extends Phase 3 by:

1. **Data Persistence** - Moving validated data from temp objects to database
2. **History Tracking** - Recording all ingestion operations
3. **User Queries** - Allowing users to view and manage their ingestions
4. **Advanced Validation** - Business rules and cross-column constraints

---

## Architecture

```
Phase 3 Output (DataTable objects)
         ↓
    Processor.validate()
         ↓
    [Valid Tables Only]
         ↓
    Phase 4: DataImporter
         ├── Insert to data_tables
         ├── Insert to data_columns
         ├── Create data_files record
         ├── Create ingestion_runs record
         ├── Store metadata
         └── Return success/failure
         ↓
    Database (Permanent Storage)
         ↓
    Phase 4: HistoryQueries
         ├── GET /api/ingestion/list
         ├── GET /api/ingestion/status/{id}
         ├── GET /api/ingestion/data/{id}
         └── DELETE /api/ingestion/{id}
```

---

## Key Concepts

### Data Importer Pattern

```python
class DataImporter:
    """Imports validated DataTable objects into database"""
    
    def import_table(self, 
                    data_table: DataTable,
                    data_file_id: int,
                    user_id: int) -> IngestionRun:
        """
        Import single table to database
        
        Steps:
        1. Create data_files record
        2. Create data_tables record
        3. Create data_columns records
        4. Store raw data (new)
        5. Create ingestion_runs record
        6. Return status
        """
        pass
```

### Row Storage Pattern

Problem: Phase 3 has DataTable objects, but no way to store individual rows.

Solution: Create `data_rows` table:

```sql
CREATE TABLE data_rows (
    id BIGSERIAL PRIMARY KEY,
    data_table_id INTEGER NOT NULL,
    row_index INTEGER,
    row_data JSONB,  -- Store entire row as JSON
    created_at TIMESTAMP
)
```

Benefits:
- ✅ Flexible schema (different tables have different columns)
- ✅ Preserve original data exactly
- ✅ Queryable with PostgreSQL JSONB operators
- ✅ Easy data inspection and validation

### History Query Pattern

```python
@router.get("/api/ingestion/list")
async def list_ingestions(
    user_id: int,
    limit: int = 10,
    offset: int = 0
):
    """List user's ingestions"""
    query = session.query(IngestionRun)\
        .filter(IngestionRun.user_id == user_id)\
        .order_by(IngestionRun.created_at.desc())\
        .limit(limit)\
        .offset(offset)
    
    return [{
        'id': run.id,
        'file_name': run.data_file.file_name,
        'tables': run.data_file.data_tables.count(),
        'rows': run.records_stored,
        'status': run.status,
        'created': run.created_at
    } for run in query.all()]
```

### Advanced Validation

```python
class AdvancedValidator:
    """Business rule validation"""
    
    def validate_references(self, table: DataTable) -> List[ValidationError]:
        """Check cross-column references"""
        # Example: Region code must exist in regions table
        pass
    
    def validate_duplicates(self, table: DataTable) -> List[ValidationError]:
        """Check for duplicate rows"""
        pass
    
    def validate_ranges(self, table: DataTable) -> List[ValidationError]:
        """Check numeric ranges (e.g., 0-100 for percentages)"""
        pass
```

---

## Implementation Steps

### Step 1: Database Migration

Create `backend/migrations/004_add_data_storage.sql`:

```sql
-- Store individual data rows
CREATE TABLE data_rows (
    id BIGSERIAL PRIMARY KEY,
    data_table_id INTEGER NOT NULL REFERENCES data_tables(id),
    row_index INTEGER NOT NULL,
    row_data JSONB NOT NULL,  -- {col1: val1, col2: val2, ...}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Update data_files to track detailed status
ALTER TABLE data_files 
ADD COLUMN tables_found INTEGER,
ADD COLUMN tables_valid INTEGER,
ADD COLUMN tables_stored INTEGER,
ADD COLUMN rows_stored INTEGER;

-- Create indexes
CREATE INDEX idx_data_rows_table_id ON data_rows(data_table_id);
CREATE INDEX idx_data_rows_data ON data_rows USING GIN (row_data);
```

### Step 2: Create DataImporter

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
        """
        Import all tables
        
        Process:
        1. Create data_files record
        2. For each table:
           - Create data_tables record
           - Create data_columns records
           - Insert rows into data_rows
           - Update success count
        3. Create ingestion_runs record
        4. Commit transaction
        
        Returns: IngestionRun with final status
        """
        pass
    
    def _import_table(self, table: DataTable, 
                     data_file_id: int) -> DataTable:
        """Import single table"""
        pass
    
    def _import_rows(self, table: DataTable,
                    data_table_id: int) -> int:
        """Import individual rows"""
        pass
```

### Step 3: Update Processor

Modify `backend/ingestion/processors.py`:

```python
def _store_tables(self) -> List[DataTable]:
    """Store validated tables with data importer"""
    
    with get_db_context() as session:
        importer = DataImporter(session, self.user_id)
        
        # Import all valid tables
        ingestion_run = importer.import_tables(
            [t for t in self.tables 
             if self.validation_results[t.name][1]],  # valid tables only
            file_name=Path(self.file_path).name
        )
        
        # Update processor results
        self.ingestion_run = ingestion_run
        return self.tables
```

### Step 4: Create History Endpoints

Extend `backend/app/api/ingestion.py`:

```python
@router.get("/api/ingestion/list")
async def list_ingestions(
    token: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List user's ingestions"""
    # Verify token
    session_data = verify_session_token(token)
    user_id = session_data['user_id']
    
    # Query ingestions
    runs = db.query(IngestionRun)\
        .filter(IngestionRun.user_id == user_id)\
        .order_by(IngestionRun.created_at.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()
    
    return {
        'total': count_total,
        'ingestions': [{
            'id': run.id,
            'file_name': run.data_file.file_name,
            'tables': len(run.data_file.data_tables),
            'rows': run.records_stored,
            'status': run.status,
            'created': run.created_at.isoformat()
        } for run in runs]
    }

@router.get("/api/ingestion/status/{ingestion_id}")
async def get_status(
    ingestion_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get detailed status of ingestion"""
    # Verify access and return details
    pass

@router.get("/api/ingestion/data/{table_id}")
async def get_table_data(
    table_id: int,
    token: str = Query(...),
    limit: int = Query(100),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Get imported data from table"""
    # Return rows with pagination
    pass

@router.delete("/api/ingestion/{ingestion_id}")
async def delete_ingestion(
    ingestion_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """Delete ingestion and associated data"""
    # Cascade delete with proper cleanup
    pass
```

### Step 5: Update Models

Add to `backend/app/models/__init__.py`:

```python
# Import required
from sqlalchemy import Column, String, Integer, Float, DateTime, JSONB, ForeignKey

class DataRow(Base):
    __tablename__ = "data_rows"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    data_table_id: Mapped[int] = mapped_column(ForeignKey("data_tables.id"))
    row_index: Mapped[int]
    row_data: Mapped[dict] = mapped_column(JSONB)  # {"col1": val1, "col2": val2}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationship
    data_table: Mapped["DataTable"] = relationship(back_populates="rows")

# Update DataTable model
class DataTable(Base):
    __tablename__ = "data_tables"
    # ... existing columns ...
    
    # New relationship
    rows: Mapped[List["DataRow"]] = relationship(back_populates="data_table", cascade="all, delete-orphan")
```

### Step 6: Update Tests

Extend `backend/tests/test_ingestion.py`:

```python
class TestDataImporter:
    """Test data import functionality"""
    
    def test_import_table(self, temp_csv_file):
        """Test importing table to database"""
        # Parse file
        parser = CSVParser(temp_csv_file)
        tables = parser.parse()
        
        # Import to database
        importer = DataImporter(session, user_id=1)
        run = importer.import_tables(tables, "test.csv")
        
        assert run.status == "completed"
        assert run.records_stored == 3
    
    def test_list_ingestions(self):
        """Test listing user's ingestions"""
        # Create sample ingestion
        # Query list
        # Verify results
        pass

class TestHistoryAPI:
    """Test history endpoints"""
    
    def test_get_list(self):
        """Test GET /api/ingestion/list"""
        pass
    
    def test_get_status(self):
        """Test GET /api/ingestion/status/{id}"""
        pass
    
    def test_get_data(self):
        """Test GET /api/ingestion/data/{table_id}"""
        pass
    
    def test_delete_ingestion(self):
        """Test DELETE /api/ingestion/{id}"""
        pass
```

### Step 7: Create Advanced Validator

Create `backend/ingestion/advanced_validators.py`:

```python
class ReferenceValidator:
    """Validate cross-table references"""
    
    def validate_references(self, 
                           table: DataTable,
                           reference_table: str,
                           ref_column: str) -> List[ValidationError]:
        """Check column values exist in reference table"""
        pass

class RangeValidator:
    """Validate numeric ranges"""
    
    def validate_ranges(self,
                       table: DataTable,
                       column: str,
                       min_val: float,
                       max_val: float) -> List[ValidationError]:
        """Check numeric values in range"""
        pass

class DuplicateValidator:
    """Find duplicate rows"""
    
    def find_duplicates(self, table: DataTable) -> List[Tuple[int, int]]:
        """Return pairs of duplicate row indices"""
        pass
```

---

## Detailed Implementation: Data Import Flow

### 1. Receive Validated Tables
```python
# From Phase 3 processor
tables = [
    DataTable(name="Survey", headers=[...], rows=[...]),
    DataTable(name="Regions", headers=[...], rows=[...]),
]
```

### 2. Create File Record
```python
data_file = DataFile(
    user_id=user_id,
    file_name="survey_2024.xlsx",
    file_type=".xlsx",
    status="processing"
)
session.add(data_file)
session.flush()  # Get ID
```

### 3. For Each Table
```python
for table in tables:
    # Create table record
    data_table = DataTable(
        data_file_id=data_file.id,
        table_name=table.name,
        row_count=table.row_count,
        col_count=table.col_count,
        headers=json.dumps(table.headers),
        is_valid=True
    )
    session.add(data_table)
    session.flush()
    
    # Create column records
    for col_idx, col_name in enumerate(table.headers):
        col = DataColumn(
            data_table_id=data_table.id,
            column_name=col_name,
            column_index=col_idx
        )
        session.add(col)
    
    # Insert rows as JSONB
    for row_idx, row in enumerate(table.rows):
        data_row = DataRow(
            data_table_id=data_table.id,
            row_index=row_idx,
            row_data=dict(zip(table.headers, row))  # {col: val, ...}
        )
        session.add(data_row)
    
    session.flush()
```

### 4. Create Ingestion Run Record
```python
run = IngestionRun(
    user_id=user_id,
    data_file_id=data_file.id,
    status="completed",
    tables_parsed=len(tables),
    tables_valid=len(tables),
    tables_stored=len(tables),
    records_stored=sum(t.row_count for t in tables)
)
session.add(run)
session.commit()
```

### 5. Return Summary
```python
return {
    'success': True,
    'ingestion_id': run.id,
    'tables_stored': run.tables_stored,
    'records_stored': run.records_stored,
    'file_url': f'/api/ingestion/data/{data_table.id}'
}
```

---

## Query Examples

### List All Ingestions
```sql
SELECT id, file_name, status, records_stored, created_at
FROM ingestion_runs ir
JOIN data_files df ON ir.data_file_id = df.id
WHERE ir.user_id = ?
ORDER BY created_at DESC
LIMIT 10;
```

### Get Single Ingestion Details
```sql
SELECT ir.id, df.file_name, df.upload_path,
       count(dt.id) as tables,
       sum(ir.records_stored) as rows,
       ir.status, ir.created_at
FROM ingestion_runs ir
JOIN data_files df ON ir.data_file_id = df.id
LEFT JOIN data_tables dt ON df.id = dt.data_file_id
WHERE ir.id = ?
GROUP BY ir.id, df.id;
```

### Get Data from Imported Table
```sql
SELECT row_data
FROM data_rows
WHERE data_table_id = ?
ORDER BY row_index
LIMIT ? OFFSET ?;
```

### Find Duplicate Rows
```sql
SELECT row_data, count(*)
FROM data_rows
WHERE data_table_id = ?
GROUP BY row_data
HAVING count(*) > 1;
```

---

## Error Handling

### Import Failures
```python
try:
    importer.import_tables(tables, file_name)
except IntegrityError as e:
    # Duplicate key, missing reference, etc.
    return {'success': False, 'error': 'Data conflict'}
except Exception as e:
    session.rollback()
    return {'success': False, 'error': str(e)}
```

### Transaction Rollback
```python
# If any step fails, entire import fails
session.begin_nested()
try:
    # Insert operations
    session.commit()
except:
    session.rollback()
    raise
```

---

## Testing Strategy

### Unit Tests
- ✅ Data importer with sample tables
- ✅ Row storage as JSONB
- ✅ History queries

### Integration Tests
- ✅ Full flow: parse → validate → import
- ✅ Multi-table import
- ✅ User isolation (can't see other user's data)

### Manual Tests
- ✅ Upload file through API
- ✅ View ingestion list
- ✅ Query imported data
- ✅ Delete ingestion with cascade

---

## Performance Considerations

### Bulk Insertion
```python
# Use bulk_insert_mappings for speed
rows_data = [
    {'data_table_id': id, 'row_index': i, 'row_data': dict(zip(headers, row))}
    for i, row in enumerate(table.rows)
]
session.bulk_insert_mappings(DataRow, rows_data)
```

### Indexing
- ✅ Index on data_table_id (query by table)
- ✅ GIN index on row_data JSONB (search within rows)
- ✅ Index on created_at (sort by date)

### Pagination
- ✅ Always use LIMIT/OFFSET in list endpoints
- ✅ Default limit 10, max 100
- ✅ Return total count for UI

---

## Migration Path

### Phase 3 → Phase 4 Data
Existing Phase 3 data (validated but not stored) flows to Phase 4:

```
Phase 3: IngestionProcessor.process()
    ↓ returns {tables_parsed, tables_valid, ...}
    
Phase 4: IngestionProcessor._store_tables()
    ↓ calls DataImporter.import_tables()
    
Database: data_rows table now contains all imported data
    ↓
Phase 5: Can query historical data for processing
```

---

## Success Criteria

✅ Data from files persists in database  
✅ Users can list their ingestions  
✅ Users can view imported data  
✅ Ingestion history tracked  
✅ Advanced validation working  
✅ API endpoints responding  
✅ Tests passing  
✅ Performance acceptable (bulk insert)  

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| 004_add_data_storage.sql | Create | New tables and columns |
| ingestion/importers.py | Create | DataImporter class |
| app/api/ingestion.py | Update | History endpoints |
| app/models/__init__.py | Update | DataRow model |
| ingestion/advanced_validators.py | Create | Business rules |
| tests/test_ingestion.py | Update | Importer tests |

---

## Next Phase: Phase 5

Phase 5 will use Phase 4 data:
- Extract insights from stored data
- Generate automated summaries
- Train embeddings for search
- Create briefing document templates

---

*Phase 4 Skills Guide - January 31, 2026*
