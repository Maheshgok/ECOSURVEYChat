"""Ingestion API routes"""

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.auth_service import verify_session_token
from app.ingestion.processors import IngestionProcessor
from app.ingestion.parsers import ParsingError

router = APIRouter()


@router.post("/ingestion/start")
async def start_ingestion(
    file: UploadFile = File(...),
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Start data ingestion from uploaded file
    
    Supports: Excel (.xlsx, .xls) and CSV files
    
    Returns:
        Ingestion result with status and metadata
    """
    # Verify authentication if token provided
    user_id = None
    if token:
        try:
            session_data = verify_session_token(token)
            user_id = session_data.get('user_id')
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    supported = ['.xlsx', '.xls', '.csv']
    if file_ext not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. "
                   f"Supported: {', '.join(supported)}"
        )
    
    # Save file temporarily
    temp_dir = tempfile.gettempdir()
    temp_path = Path(temp_dir) / file.filename
    
    try:
        # Write uploaded file
        contents = await file.read()
        with open(temp_path, 'wb') as f:
            f.write(contents)
        
        # Process ingestion
        processor = IngestionProcessor(str(temp_path), user_id=user_id)
        result = processor.process()
        
        return {
            'success': result['success'],
            'ingestion_id': processor.ingestion_id,
            'file_name': file.filename,
            'tables_parsed': result['tables_parsed'],
            'tables_valid': result['tables_valid'],
            'tables_stored': result['tables_stored'],
            'records_stored': result['records_stored'],
            'errors': result['errors'],
            'warnings': result['warnings'],
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")
    
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


@router.get("/ingestion/status/{ingestion_id}")
async def get_ingestion_status(
    ingestion_id: int,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get status of a completed ingestion
    
    Args:
        ingestion_id: ID of ingestion run
        
    Returns:
        Ingestion status and results
    """
    # Verify authentication if token provided
    if token:
        try:
            verify_session_token(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    # In MVP, we don't store ingestion history
    # This would be implemented in Phase 3+ with database tracking
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.get("/ingestion/list")
async def list_ingestions(
    token: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List user's ingestion history
    
    Args:
        token: Session token
        limit: Max results to return
        offset: Pagination offset
        
    Returns:
        List of ingestion summaries
    """
    # Verify authentication if token provided
    user_id = None
    if token:
        try:
            session_data = verify_session_token(token)
            user_id = session_data.get('user_id')
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    # In MVP, we don't store ingestion history
    # This would be implemented in Phase 3+ with database tracking
    return {
        'total': 0,
        'limit': limit,
        'offset': offset,
        'ingestions': []
    }


@router.post("/ingestion/validate")
async def validate_file(
    file: UploadFile = File(...),
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Validate file without storing
    
    Useful for previewing data before full ingestion
    
    Returns:
        Validation results with parsed tables
    """
    # Verify authentication if token provided
    if token:
        try:
            verify_session_token(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    supported = ['.xlsx', '.xls', '.csv']
    if file_ext not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. "
                   f"Supported: {', '.join(supported)}"
        )
    
    # Save file temporarily
    temp_dir = tempfile.gettempdir()
    temp_path = Path(temp_dir) / file.filename
    
    try:
        # Write uploaded file
        contents = await file.read()
        with open(temp_path, 'wb') as f:
            f.write(contents)
        
        # Process without storing
        processor = IngestionProcessor(str(temp_path), user_id=None)
        
        # Parse only
        if not processor._parse_file():
            return {
                'valid': False,
                'errors': processor.errors,
                'tables': []
            }
        
        # Validate tables
        processor._validate_tables()
        
        # Return preview
        tables_preview = []
        for table in processor.tables:
            tables_preview.append({
                'name': table.name,
                'columns': table.headers,
                'rows': len(table.rows),
                'sample_rows': table.rows[:3] if table.rows else [],
            })
        
        return {
            'valid': all(
                valid for _, valid, _ in processor.validation_results.values()
            ),
            'tables': tables_preview,
            'errors': processor.errors,
            'warnings': processor.warnings,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")
    
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()
