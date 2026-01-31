"""Data importer - stores validated data in database"""

import json
from datetime import datetime
from typing import List

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db_context
from .parsers import DataTable


class DataImporter:
    """Import validated DataTable objects into database"""
    
    def __init__(self, session: Session, user_id: int = None):
        """
        Initialize importer
        
        Args:
            session: SQLAlchemy database session
            user_id: User ID for tracking ownership
        """
        self.session = session
        self.user_id = user_id
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def import_tables(self, 
                     tables: List[DataTable],
                     file_name: str) -> dict:
        """
        Import all tables to database
        
        Args:
            tables: List of validated DataTable objects
            file_name: Name of source file
            
        Returns:
            Dict with ingestion results {success, ingestion_id, tables_stored, records_stored}
        """
        try:
            # Create data_files record
            file_id = self._create_file_record(file_name)
            
            if not file_id:
                return {
                    'success': False,
                    'error': 'Failed to create file record',
                    'errors': self.errors
                }
            
            # Import tables and track results
            tables_stored = 0
            records_stored = 0
            
            for table in tables:
                try:
                    stored_count = self._import_table(table, file_id)
                    if stored_count >= 0:
                        tables_stored += 1
                        records_stored += stored_count
                except Exception as e:
                    self.warnings.append(f"Failed to import table '{table.name}': {str(e)}")
            
            # Create ingestion_runs record
            run_id = self._create_ingestion_run(
                file_id=file_id,
                tables_stored=tables_stored,
                records_stored=records_stored
            )
            
            # Update data_files with summary
            self._update_file_summary(
                file_id=file_id,
                tables_found=len(tables),
                tables_stored=tables_stored,
                rows_stored=records_stored
            )
            
            # Commit transaction
            self.session.commit()
            
            return {
                'success': True,
                'ingestion_id': run_id,
                'file_id': file_id,
                'tables_stored': tables_stored,
                'records_stored': records_stored,
                'errors': self.errors,
                'warnings': self.warnings,
            }
        
        except Exception as e:
            self.session.rollback()
            self.errors.append(f"Import failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'errors': self.errors,
                'warnings': self.warnings,
            }
    
    def _create_file_record(self, file_name: str) -> int:
        """
        Create data_files record
        
        Args:
            file_name: Name of uploaded file
            
        Returns:
            File ID or None if failed
        """
        try:
            # Get file extension
            file_ext = file_name.split('.')[-1].lower()
            if file_ext not in ['xlsx', 'xls', 'csv']:
                file_ext = 'unknown'
            
            stmt = text("""
                INSERT INTO data_files 
                (user_id, file_name, file_type, status, created_at)
                VALUES (:user_id, :file_name, :file_type, :status, :created_at)
                RETURNING id
            """)
            
            result = self.session.execute(stmt, {
                'user_id': self.user_id,
                'file_name': file_name,
                'file_type': f'.{file_ext}',
                'status': 'processing',
                'created_at': datetime.utcnow(),
            })
            
            file_id = result.scalar()
            return file_id
        
        except Exception as e:
            self.errors.append(f"Failed to create file record: {str(e)}")
            return None
    
    def _import_table(self, table: DataTable, file_id: int) -> int:
        """
        Import single table to database
        
        Args:
            table: DataTable object to import
            file_id: ID of parent data_files record
            
        Returns:
            Number of rows imported, or -1 if failed
        """
        try:
            # Create data_tables record
            table_id = self._create_table_record(table, file_id)
            if not table_id:
                return -1
            
            # Create data_columns records
            for col_idx, header in enumerate(table.headers):
                self._create_column_record(table_id, header, col_idx)
            
            # Import rows
            row_count = self._import_rows(table, table_id)
            
            return row_count
        
        except Exception as e:
            self.errors.append(f"Failed to import table '{table.name}': {str(e)}")
            return -1
    
    def _create_table_record(self, table: DataTable, file_id: int) -> int:
        """
        Create data_tables record
        
        Args:
            table: DataTable to import
            file_id: ID of parent data_files
            
        Returns:
            Table ID or None
        """
        try:
            stmt = text("""
                INSERT INTO data_tables
                (data_file_id, table_name, row_count, col_count, headers, is_valid, created_at)
                VALUES (:data_file_id, :table_name, :row_count, :col_count, :headers, :is_valid, :created_at)
                RETURNING id
            """)
            
            result = self.session.execute(stmt, {
                'data_file_id': file_id,
                'table_name': table.name,
                'row_count': table.row_count,
                'col_count': table.col_count,
                'headers': json.dumps(table.headers),
                'is_valid': True,
                'created_at': datetime.utcnow(),
            })
            
            table_id = result.scalar()
            return table_id
        
        except Exception as e:
            self.errors.append(f"Failed to create table record: {str(e)}")
            return None
    
    def _create_column_record(self, table_id: int, column_name: str, column_index: int) -> None:
        """Create data_columns record"""
        try:
            stmt = text("""
                INSERT INTO data_columns
                (data_table_id, column_name, column_index)
                VALUES (:data_table_id, :column_name, :column_index)
            """)
            
            self.session.execute(stmt, {
                'data_table_id': table_id,
                'column_name': column_name,
                'column_index': column_index,
            })
        
        except Exception as e:
            self.warnings.append(f"Failed to create column record: {str(e)}")
    
    def _import_rows(self, table: DataTable, table_id: int) -> int:
        """
        Import individual rows as JSONB
        
        Args:
            table: DataTable with rows to import
            table_id: ID of data_tables record
            
        Returns:
            Number of rows imported
        """
        if not table.rows:
            return 0
        
        try:
            # Prepare row data
            rows_data = []
            for row_idx, row in enumerate(table.rows):
                # Convert row to dict: {header: value}
                row_dict = dict(zip(table.headers, row))
                rows_data.append({
                    'data_table_id': table_id,
                    'row_index': row_idx,
                    'row_data': json.dumps(row_dict),  # JSONB
                    'created_at': datetime.utcnow(),
                })
            
            # Bulk insert rows
            stmt = text("""
                INSERT INTO data_rows
                (data_table_id, row_index, row_data, created_at)
                VALUES (:data_table_id, :row_index, :row_data::jsonb, :created_at)
            """)
            
            for row_data in rows_data:
                self.session.execute(stmt, row_data)
            
            return len(rows_data)
        
        except Exception as e:
            self.errors.append(f"Failed to import rows: {str(e)}")
            return -1
    
    def _create_ingestion_run(self, 
                            file_id: int,
                            tables_stored: int,
                            records_stored: int) -> int:
        """
        Create ingestion_runs record
        
        Args:
            file_id: ID of data_files
            tables_stored: Number of tables imported
            records_stored: Total rows imported
            
        Returns:
            Ingestion run ID
        """
        try:
            stmt = text("""
                INSERT INTO ingestion_runs
                (user_id, data_file_id, status, tables_parsed, tables_valid, 
                 tables_stored, records_stored, started_at, completed_at)
                VALUES (:user_id, :data_file_id, :status, :tables_parsed, :tables_valid,
                       :tables_stored, :records_stored, :started_at, :completed_at)
                RETURNING id
            """)
            
            result = self.session.execute(stmt, {
                'user_id': self.user_id,
                'data_file_id': file_id,
                'status': 'completed',
                'tables_parsed': 0,  # Would be updated if tracking
                'tables_valid': tables_stored,
                'tables_stored': tables_stored,
                'records_stored': records_stored,
                'started_at': datetime.utcnow(),
                'completed_at': datetime.utcnow(),
            })
            
            run_id = result.scalar()
            return run_id
        
        except Exception as e:
            self.errors.append(f"Failed to create ingestion run: {str(e)}")
            return None
    
    def _update_file_summary(self,
                           file_id: int,
                           tables_found: int,
                           tables_stored: int,
                           rows_stored: int) -> None:
        """Update data_files with summary statistics"""
        try:
            stmt = text("""
                UPDATE data_files
                SET tables_found = :tables_found,
                    tables_stored = :tables_stored,
                    rows_stored = :rows_stored,
                    status = 'completed',
                    completed_at = :completed_at
                WHERE id = :file_id
            """)
            
            self.session.execute(stmt, {
                'file_id': file_id,
                'tables_found': tables_found,
                'tables_stored': tables_stored,
                'rows_stored': rows_stored,
                'completed_at': datetime.utcnow(),
            })
        
        except Exception as e:
            self.warnings.append(f"Failed to update file summary: {str(e)}")
    
    def summary(self) -> dict:
        """Get import summary"""
        return {
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
        }
