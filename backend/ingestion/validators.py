"""Data validation framework"""

from typing import List, Tuple, Dict, Any
from .parsers import DataTable


class ValidationError:
    """Represents a single validation error"""
    
    def __init__(self, row: int, col: str, message: str, severity: str = 'error'):
        self.row = row
        self.col = col
        self.message = message
        self.severity = severity  # 'error' or 'warning'
    
    def __repr__(self):
        return f"<ValidationError row={self.row} col='{self.col}' severity='{self.severity}': {self.message}>"


class DataValidator:
    """Validate data tables for quality and correctness"""
    
    def __init__(self, data_table: DataTable):
        """
        Initialize validator
        
        Args:
            data_table: DataTable to validate
        """
        self.table = data_table
        self.errors: List[ValidationError] = []
    
    def validate(self) -> bool:
        """
        Run all validations
        
        Returns:
            True if no critical errors, False otherwise
        """
        self._validate_headers()
        self._validate_rows()
        self._validate_data_types()
        
        # Critical errors are those with severity='error'
        return not any(e.severity == 'error' for e in self.errors)
    
    def _validate_headers(self) -> None:
        """Validate headers"""
        
        # Check headers not empty
        if not self.table.headers:
            self.errors.append(ValidationError(
                row=0, col='*',
                message="No headers found",
                severity='error'
            ))
            return
        
        # Check for duplicate headers
        seen = set()
        for i, header in enumerate(self.table.headers):
            if header in seen:
                self.errors.append(ValidationError(
                    row=0, col=str(i),
                    message=f"Duplicate header: '{header}'",
                    severity='warning'
                ))
            seen.add(header)
    
    def _validate_rows(self) -> None:
        """Validate data rows"""
        
        if not self.table.rows:
            self.errors.append(ValidationError(
                row=1, col='*',
                message="No data rows found",
                severity='warning'
            ))
            return
        
        col_count = len(self.table.headers)
        
        for row_idx, row in enumerate(self.table.rows, start=1):
            # Check row length
            if len(row) != col_count:
                self.errors.append(ValidationError(
                    row=row_idx, col='*',
                    message=f"Row has {len(row)} columns, expected {col_count}",
                    severity='warning'
                ))
            
            # Check for completely empty rows
            if not any(cell is not None and str(cell).strip() for cell in row):
                self.errors.append(ValidationError(
                    row=row_idx, col='*',
                    message="Row is completely empty",
                    severity='warning'
                ))
    
    def _validate_data_types(self) -> None:
        """Validate data types in columns"""
        
        # Detect likely type for each column
        col_types = self._detect_column_types()
        
        for row_idx, row in enumerate(self.table.rows, start=1):
            for col_idx, (cell, expected_type) in enumerate(zip(row, col_types)):
                if cell is None or not str(cell).strip():
                    continue
                
                if expected_type == 'numeric' and not self._is_numeric(cell):
                    header = self.table.headers[col_idx]
                    self.errors.append(ValidationError(
                        row=row_idx, col=header,
                        message=f"Expected numeric value, got '{cell}'",
                        severity='warning'
                    ))
    
    def _detect_column_types(self) -> List[str]:
        """
        Detect likely data type for each column
        
        Returns:
            List of type names ('numeric', 'text', 'mixed')
        """
        col_types = ['text'] * len(self.table.headers)
        
        if not self.table.rows:
            return col_types
        
        # Sample up to 100 rows
        sample_rows = self.table.rows[:100]
        
        for col_idx in range(len(self.table.headers)):
            numeric_count = 0
            non_empty_count = 0
            
            for row in sample_rows:
                if col_idx < len(row):
                    cell = row[col_idx]
                    if cell is not None and str(cell).strip():
                        non_empty_count += 1
                        if self._is_numeric(cell):
                            numeric_count += 1
            
            # If 80%+ are numeric, mark as numeric
            if non_empty_count > 0:
                numeric_ratio = numeric_count / non_empty_count
                if numeric_ratio >= 0.8:
                    col_types[col_idx] = 'numeric'
        
        return col_types
    
    @staticmethod
    def _is_numeric(value: Any) -> bool:
        """Check if value is numeric"""
        if isinstance(value, (int, float)):
            return True
        
        try:
            str_val = str(value).strip()
            float(str_val)
            return True
        except (ValueError, TypeError):
            return False
    
    def get_errors(self, severity: str = None) -> List[ValidationError]:
        """
        Get validation errors
        
        Args:
            severity: Filter by 'error' or 'warning' (None for all)
            
        Returns:
            List of ValidationError objects
        """
        if severity:
            return [e for e in self.errors if e.severity == severity]
        return self.errors
    
    def summary(self) -> Dict[str, Any]:
        """Get validation summary"""
        errors = [e for e in self.errors if e.severity == 'error']
        warnings = [e for e in self.errors if e.severity == 'warning']
        
        return {
            'valid': len(errors) == 0,
            'error_count': len(errors),
            'warning_count': len(warnings),
            'errors': [
                {'row': e.row, 'col': e.col, 'message': e.message}
                for e in errors
            ],
            'warnings': [
                {'row': e.row, 'col': e.col, 'message': e.message}
                for e in warnings
            ],
        }
