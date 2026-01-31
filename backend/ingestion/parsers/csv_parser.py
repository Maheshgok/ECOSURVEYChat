"""CSV file parser"""

import csv
from pathlib import Path
from typing import List

from .base_parser import BaseParser, DataTable, ParsingError


class CSVParser(BaseParser):
    """Parse CSV files into data tables"""
    
    def __init__(self, file_path: str, encoding: str = 'utf-8'):
        """
        Initialize CSV parser
        
        Args:
            file_path: Path to CSV file
            encoding: File encoding (default: utf-8)
        """
        super().__init__(file_path)
        self.encoding = encoding
    
    def parse(self) -> List[DataTable]:
        """
        Parse CSV file
        
        Returns:
            List with single DataTable object
            
        Raises:
            ParsingError: If file doesn't exist or can't be parsed
        """
        try:
            # Check file exists
            path = Path(self.file_path)
            if not path.exists():
                raise ParsingError(f"File not found: {self.file_path}")
            
            # Try to read with specified encoding
            try:
                with open(self.file_path, 'r', encoding=self.encoding) as f:
                    reader = csv.reader(f)
                    rows = list(reader)
            except UnicodeDecodeError:
                # Try alternative encodings
                for encoding in ['latin-1', 'iso-8859-1', 'cp1252']:
                    try:
                        with open(self.file_path, 'r', encoding=encoding) as f:
                            reader = csv.reader(f)
                            rows = list(reader)
                        self.add_warning(f"File decoded with {encoding} instead of {self.encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ParsingError("Could not decode CSV file with any encoding")
            
            if not rows:
                raise ParsingError("CSV file is empty")
            
            # Extract headers and data
            headers = [h.strip() if h else f"Column_{i}" for i, h in enumerate(rows[0])]
            data_rows = rows[1:]
            
            # Remove trailing empty rows
            while data_rows and not any(cell.strip() for cell in data_rows[-1]):
                data_rows.pop()
            
            if not data_rows:
                self.add_warning("CSV file contains only headers (no data)")
                data_rows = []
            
            # Create data table
            table = DataTable(
                name=path.stem,  # Filename without extension
                headers=headers,
                rows=data_rows,
            )
            
            return [table]
        
        except ParsingError:
            raise
        except Exception as e:
            raise ParsingError(f"Unexpected error parsing CSV: {str(e)}")
