"""Ingestion processor - orchestrates parsing, validation, and storage"""

import tempfile
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

from sqlalchemy import text
from app.core.database import get_db_context

from .parsers import BaseParser, DataTable, ExcelParser, CSVParser, ParsingError
from .validators import DataValidator
from .importers import DataImporter


class IngestionProcessor:
    """Process file ingestion: parse, validate, and store in database"""
    
    # Supported file extensions and their parsers
    PARSERS = {
        '.xlsx': ExcelParser,
        '.xls': ExcelParser,
        '.csv': CSVParser,
    }
    
    def __init__(self, file_path: str, user_id: int = None):
        """
        Initialize processor
        
        Args:
            file_path: Path to file to process
            user_id: User ID for tracking ingestion
        """
        self.file_path = file_path
        self.user_id = user_id
        self.parser = None
        self.tables: List[DataTable] = []
        self.validation_results = {}
        self.ingestion_id = None  # Set by DataImporter
        self.errors = []
        self.warnings = []
    
    def process(self) -> Dict:
        """
        Full ingestion pipeline
        
        Returns:
            Dict with results and status
        """
        results = {
            'success': False,
            'errors': [],
            'warnings': [],
            'tables_parsed': 0,
            'tables_valid': 0,
            'tables_stored': 0,
            'records_stored': 0,
        }
        
        try:
            # Step 1: Parse file
            if not self._parse_file():
                results['errors'] = self.errors
                return results
            
            results['tables_parsed'] = len(self.tables)
            
            # Step 2: Validate tables
            self._validate_tables()
            valid_tables = [t for name, valid, _ in self.validation_results.values() 
                          if valid for t in [name]]
            results['tables_valid'] = len(valid_tables)
            
            # Step 3: Store in database
            stored = self._store_tables()
            results['tables_stored'] = len(stored)
            
            # Calculate total records
            for table in stored:
                results['records_stored'] += table.row_count
            
            results['success'] = True
            results['warnings'] = self.warnings
            
        except Exception as e:
            self.errors.append(f"Ingestion failed: {str(e)}")
            results['errors'] = self.errors
        
        return results
    
    def _parse_file(self) -> bool:
        """
        Parse file using appropriate parser
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine file type
            file_ext = Path(self.file_path).suffix.lower()
            if file_ext not in self.PARSERS:
                self.errors.append(
                    f"Unsupported file type: {file_ext} "
                    f"(supported: {', '.join(self.PARSERS.keys())})"
                )
                return False
            
            # Get appropriate parser
            parser_class = self.PARSERS[file_ext]
            self.parser = parser_class(self.file_path)
            
            # Parse file
            self.tables = self.parser.parse()
            
            # Collect parser warnings
            if self.parser.warnings:
                self.warnings.extend(self.parser.warnings)
            
            if not self.tables:
                self.errors.append("No tables found in file")
                return False
            
            return True
        
        except ParsingError as e:
            self.errors.append(str(e))
            return False
        except Exception as e:
            self.errors.append(f"Parsing error: {str(e)}")
            return False
    
    def _validate_tables(self) -> None:
        """Validate all parsed tables"""
        
        for table in self.tables:
            validator = DataValidator(table)
            is_valid = validator.validate()
            
            summary = validator.summary()
            self.validation_results[table.name] = (
                table.name,
                is_valid,
                summary
            )
            
            # Collect warnings
            for warning in summary.get('warnings', []):
                msg = f"Table '{table.name}' - {warning['message']}"
                self.warnings.append(msg)
    
    def _store_tables(self) -> List[DataTable]:
        """Store validated tables using DataImporter"""
        stored = []
        
        # Get valid tables only
        valid_tables = [
            table for table in self.tables 
            if table.name in self.validation_results and 
               self.validation_results[table.name][1]  # is_valid flag
        ]
        
        if not valid_tables:
            return stored
        
        # Use DataImporter to persist to database
        with get_db_context() as session:
            try:
                importer = DataImporter(session, user_id=self.user_id)
                result = importer.import_tables(
                    valid_tables,
                    Path(self.file_path).name
                )
                
                # Collect results
                if result['success']:
                    self.ingestion_id = result.get('ingestion_id')
                    stored = valid_tables
                    if result.get('warnings'):
                        self.warnings.extend(result['warnings'])
                else:
                    self.errors.append(result.get('error', 'Import failed'))
                    if result.get('errors'):
                        self.errors.extend(result['errors'])
            
            except Exception as e:
                self.errors.append(f"Storage error: {str(e)}")
        
        return stored
    
    def _insert_table(self, table: DataTable) -> None:
        """
        (Deprecated) Insert table data into database
        
        Note: This method is kept for backward compatibility.
        New code should use DataImporter instead.
        
        """
        with get_db_context() as session:
            try:
                # Metadata insertion (kept for reference, but DataImporter is preferred)
                now = datetime.utcnow()
                
                # Insert metadata
                stmt = text("""
                    INSERT INTO data_tables (table_name, row_count, col_count, created_at)
                    VALUES (:table_name, :row_count, :col_count, :created_at)
                """)
                
                session.execute(stmt, {
                    'table_name': table.name,
                    'row_count': table.row_count,
                    'col_count': table.col_count,
                    'created_at': now,
                })
                
                session.commit()
            
            except Exception as e:
                session.rollback()
                raise e
    
    def summary(self) -> Dict:
        """Get processing summary"""
        return {
            'file': self.file_path,
            'user_id': self.user_id,
            'tables_parsed': len(self.tables),
            'validation_results': self.validation_results,
            'errors': self.errors,
            'warnings': self.warnings,
        }
