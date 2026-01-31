"""Excel file parser using openpyxl"""

from pathlib import Path
from typing import List
import openpyxl
from openpyxl.utils import get_column_letter

from .base_parser import BaseParser, DataTable, ParsingError


class ExcelParser(BaseParser):
    """Parse Excel files (.xlsx, .xls) into data tables"""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.workbook = None
    
    def parse(self) -> List[DataTable]:
        """
        Parse Excel file
        
        Returns:
            List of DataTable objects (one per sheet)
            
        Raises:
            ParsingError: If file doesn't exist or can't be parsed
        """
        tables = []
        
        try:
            # Check file exists
            path = Path(self.file_path)
            if not path.exists():
                raise ParsingError(f"File not found: {self.file_path}")
            
            # Load workbook
            try:
                self.workbook = openpyxl.load_workbook(self.file_path, data_only=True)
            except Exception as e:
                raise ParsingError(f"Failed to load Excel file: {str(e)}")
            
            # Process each sheet
            for sheet_name in self.workbook.sheetnames:
                try:
                    sheet = self.workbook[sheet_name]
                    table = self._parse_sheet(sheet, sheet_name)
                    if table:
                        tables.append(table)
                except Exception as e:
                    self.add_warning(f"Failed to parse sheet '{sheet_name}': {str(e)}")
            
            if not tables:
                raise ParsingError("No tables found in Excel file")
            
            return tables
        
        except ParsingError:
            raise
        except Exception as e:
            raise ParsingError(f"Unexpected error parsing Excel: {str(e)}")
    
    def _parse_sheet(self, sheet, sheet_name: str) -> DataTable:
        """
        Parse a single sheet into a data table
        
        Args:
            sheet: openpyxl worksheet
            sheet_name: Name of sheet
            
        Returns:
            DataTable object or None if sheet is empty
        """
        rows = []
        headers = None
        
        # Iterate through rows
        for row_idx, row in enumerate(sheet.iter_rows(values_only=True), 1):
            # Skip empty rows
            if not any(cell is not None for cell in row):
                continue
            
            # Extract headers from first row
            if headers is None:
                headers = [str(cell).strip() if cell else f"Column_{i}" 
                          for i, cell in enumerate(row)]
                continue
            
            # Add data rows
            rows.append(list(row))
        
        # Return None if only headers (no data)
        if not rows:
            self.add_warning(f"Sheet '{sheet_name}' contains only headers (no data)")
            return None
        
        # Create data table
        return DataTable(
            name=sheet_name,
            headers=headers,
            rows=rows,
            sheet_name=sheet_name,
        )
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close workbook on exit"""
        if self.workbook:
            self.workbook.close()
