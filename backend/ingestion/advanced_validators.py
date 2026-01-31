"""Advanced validation for business rules and data integrity"""

from typing import List, Set
from .parsers import DataTable
from .validators import ValidationError


class ReferenceValidator:
    """Validate cross-table references"""
    
    def __init__(self, table: DataTable, reference_data: dict = None):
        """
        Initialize reference validator
        
        Args:
            table: DataTable to validate
            reference_data: Dict of reference tables {ref_table: [valid_values]}
        """
        self.table = table
        self.reference_data = reference_data or {}
        self.errors: List[ValidationError] = []
    
    def validate_references(self, column: str, valid_values: Set) -> List[ValidationError]:
        """
        Validate that column values exist in reference set
        
        Args:
            column: Column name to validate
            valid_values: Set of valid values
            
        Returns:
            List of validation errors
        """
        if column not in self.table.headers:
            self.errors.append(ValidationError(
                row=0, col=column,
                message=f"Column '{column}' not found in table",
                severity='error'
            ))
            return self.errors
        
        col_idx = self.table.headers.index(column)
        invalid_values = set()
        
        for row_idx, row in enumerate(self.table.rows, start=1):
            if col_idx < len(row):
                value = row[col_idx]
                if value and str(value).strip() and value not in valid_values:
                    invalid_values.add(value)
                    self.errors.append(ValidationError(
                        row=row_idx, col=column,
                        message=f"Invalid value '{value}' not in reference data",
                        severity='warning'
                    ))
        
        return self.errors


class RangeValidator:
    """Validate numeric ranges"""
    
    def __init__(self, table: DataTable):
        """
        Initialize range validator
        
        Args:
            table: DataTable to validate
        """
        self.table = table
        self.errors: List[ValidationError] = []
    
    def validate_range(self, column: str, min_val: float, max_val: float) -> List[ValidationError]:
        """
        Validate column values are within range
        
        Args:
            column: Column name to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            List of validation errors
        """
        if column not in self.table.headers:
            self.errors.append(ValidationError(
                row=0, col=column,
                message=f"Column '{column}' not found",
                severity='error'
            ))
            return self.errors
        
        col_idx = self.table.headers.index(column)
        
        for row_idx, row in enumerate(self.table.rows, start=1):
            if col_idx < len(row):
                try:
                    value = float(row[col_idx])
                    if value < min_val or value > max_val:
                        self.errors.append(ValidationError(
                            row=row_idx, col=column,
                            message=f"Value {value} outside range [{min_val}, {max_val}]",
                            severity='warning'
                        ))
                except (ValueError, TypeError):
                    pass  # Non-numeric values handled by type validation
        
        return self.errors


class DuplicateValidator:
    """Find duplicate rows"""
    
    def __init__(self, table: DataTable):
        """
        Initialize duplicate validator
        
        Args:
            table: DataTable to validate
        """
        self.table = table
        self.duplicates: List[tuple] = []  # Pairs of row indices
    
    def find_duplicates(self) -> List[tuple]:
        """
        Find duplicate rows
        
        Returns:
            List of (row_idx1, row_idx2) tuples
        """
        # Convert rows to tuples for comparison
        row_tuples = [tuple(row) for row in self.table.rows]
        duplicates = []
        
        # Compare all pairs
        for i in range(len(row_tuples)):
            for j in range(i + 1, len(row_tuples)):
                if row_tuples[i] == row_tuples[j]:
                    duplicates.append((i + 1, j + 1))  # 1-based row numbers
        
        self.duplicates = duplicates
        return duplicates
    
    def get_errors(self) -> List[ValidationError]:
        """Convert duplicates to validation errors"""
        errors = []
        for row1, row2 in self.duplicates:
            errors.append(ValidationError(
                row=row1, col='*',
                message=f"Duplicate of row {row2}",
                severity='warning'
            ))
        return errors


class ConsistencyValidator:
    """Validate data consistency rules"""
    
    def __init__(self, table: DataTable):
        """
        Initialize consistency validator
        
        Args:
            table: DataTable to validate
        """
        self.table = table
        self.errors: List[ValidationError] = []
    
    def validate_no_nulls(self, column: str) -> List[ValidationError]:
        """
        Validate column has no null/empty values
        
        Args:
            column: Column name
            
        Returns:
            List of validation errors
        """
        if column not in self.table.headers:
            return []
        
        col_idx = self.table.headers.index(column)
        
        for row_idx, row in enumerate(self.table.rows, start=1):
            if col_idx < len(row):
                value = row[col_idx]
                if value is None or str(value).strip() == '':
                    self.errors.append(ValidationError(
                        row=row_idx, col=column,
                        message=f"Required field is empty",
                        severity='error'
                    ))
        
        return self.errors
    
    def validate_unique(self, column: str) -> List[ValidationError]:
        """
        Validate column has unique values
        
        Args:
            column: Column name
            
        Returns:
            List of validation errors
        """
        if column not in self.table.headers:
            return []
        
        col_idx = self.table.headers.index(column)
        seen = {}
        
        for row_idx, row in enumerate(self.table.rows, start=1):
            if col_idx < len(row):
                value = row[col_idx]
                if value is not None and str(value).strip():
                    if value in seen:
                        self.errors.append(ValidationError(
                            row=row_idx, col=column,
                            message=f"Duplicate value (also at row {seen[value]})",
                            severity='warning'
                        ))
                    else:
                        seen[value] = row_idx
        
        return self.errors


class SummaryValidator:
    """Composite validator combining multiple rules"""
    
    def __init__(self, table: DataTable):
        """
        Initialize summary validator
        
        Args:
            table: DataTable to validate
        """
        self.table = table
        self.rules: List[tuple] = []  # (name, validator, method, args)
    
    def add_rule(self, name: str, validator, method_name: str, *args) -> None:
        """
        Add validation rule
        
        Args:
            name: Rule name
            validator: Validator instance
            method_name: Method to call
            args: Arguments to pass
        """
        self.rules.append((name, validator, method_name, args))
    
    def validate(self) -> dict:
        """
        Run all validation rules
        
        Returns:
            Dict with results {rule_name: [errors]}
        """
        results = {}
        
        for name, validator, method_name, args in self.rules:
            try:
                method = getattr(validator, method_name)
                errors = method(*args) if args else method()
                results[name] = errors if isinstance(errors, list) else [errors]
            except Exception as e:
                results[name] = [ValidationError(
                    row=0, col='*',
                    message=f"Validation failed: {str(e)}",
                    severity='error'
                )]
        
        return results
