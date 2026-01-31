"""Base parser class for all file parsers"""

from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass


@dataclass
class DataTable:
    """In-memory representation of a parsed data table"""
    name: str
    headers: List[str]
    rows: List[List]
    sheet_name: str = None
    
    @property
    def row_count(self) -> int:
        return len(self.rows)
    
    @property
    def col_count(self) -> int:
        return len(self.headers)
    
    def to_dict_rows(self) -> List[dict]:
        """Convert rows to list of dictionaries"""
        return [dict(zip(self.headers, row)) for row in self.rows]


class ParsingError(Exception):
    """Raised when file parsing fails"""
    pass


class BaseParser(ABC):
    """Abstract base class for all file parsers"""
    
    def __init__(self, file_path: str):
        """
        Initialize parser
        
        Args:
            file_path: Path to file to parse
        """
        self.file_path = file_path
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    @abstractmethod
    def parse(self) -> List[DataTable]:
        """
        Parse file and return list of data tables
        
        Returns:
            List of DataTable objects
            
        Raises:
            ParsingError: If parsing fails
        """
        pass
    
    def add_error(self, error: str) -> None:
        """Record parsing error"""
        self.errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """Record parsing warning"""
        self.warnings.append(warning)
    
    def has_errors(self) -> bool:
        """Check if parsing encountered errors"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if parsing encountered warnings"""
        return len(self.warnings) > 0
    
    def summary(self) -> dict:
        """Get parsing summary"""
        return {
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
        }
