"""Integration tests for data ingestion"""

import pytest
import tempfile
from pathlib import Path
import csv

from app.ingestion.parsers import ExcelParser, CSVParser, DataTable
from app.ingestion.validators import DataValidator
from app.ingestion.processors import IngestionProcessor
from app.ingestion.importers import DataImporter
from app.ingestion.advanced_validators import DuplicateValidator, RangeValidator, ConsistencyValidator


@pytest.fixture
def temp_csv_file():
    """Create a temporary CSV file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        writer = csv.writer(f)
        writer.writerow(['Region', 'Year', 'GDP', 'Employment'])
        writer.writerow(['NE', '2024', '3.2', '92.3'])
        writer.writerow(['SE', '2024', '2.8', '91.8'])
        writer.writerow(['MW', '2024', '3.4', '93.1'])
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink()


class TestCSVParser:
    """Test CSV file parsing"""
    
    def test_parse_valid_csv(self, temp_csv_file):
        """Test parsing valid CSV file"""
        parser = CSVParser(temp_csv_file)
        tables = parser.parse()
        
        assert len(tables) == 1
        table = tables[0]
        
        assert table.headers == ['Region', 'Year', 'GDP', 'Employment']
        assert table.row_count == 3
        assert table.col_count == 4
        
        # Check sample row
        assert table.rows[0][0] == 'NE'
        assert table.rows[0][2] == '3.2'
    
    def test_csv_to_dict_rows(self, temp_csv_file):
        """Test converting CSV rows to dictionaries"""
        parser = CSVParser(temp_csv_file)
        tables = parser.parse()
        table = tables[0]
        
        dict_rows = table.to_dict_rows()
        assert len(dict_rows) == 3
        
        first_row = dict_rows[0]
        assert first_row['Region'] == 'NE'
        assert first_row['GDP'] == '3.2'
    
    def test_csv_nonexistent_file(self):
        """Test parsing non-existent file"""
        from app.ingestion.parsers.base_parser import ParsingError
        
        parser = CSVParser('/nonexistent/file.csv')
        with pytest.raises(ParsingError):
            parser.parse()


class TestDataValidator:
    """Test data validation"""
    
    def test_validate_good_data(self, temp_csv_file):
        """Test validation of good data"""
        parser = CSVParser(temp_csv_file)
        tables = parser.parse()
        
        validator = DataValidator(tables[0])
        is_valid = validator.validate()
        
        assert is_valid is True
        assert len(validator.errors) == 0
    
    def test_validate_numeric_columns(self, temp_csv_file):
        """Test numeric column detection"""
        parser = CSVParser(temp_csv_file)
        tables = parser.parse()
        
        validator = DataValidator(tables[0])
        validator._validate_data_types()
        
        # GDP and Employment should be numeric
        col_types = validator._detect_column_types()
        assert col_types[2] == 'numeric'  # GDP
        assert col_types[3] == 'numeric'  # Employment
    
    def test_validation_summary(self, temp_csv_file):
        """Test validation summary"""
        parser = CSVParser(temp_csv_file)
        tables = parser.parse()
        
        validator = DataValidator(tables[0])
        validator.validate()
        summary = validator.summary()
        
        assert summary['valid'] is True
        assert summary['error_count'] == 0
        assert 'warnings' in summary


class TestIngestionProcessor:
    """Test full ingestion pipeline"""
    
    def test_process_csv_file(self, temp_csv_file):
        """Test full ingestion process"""
        processor = IngestionProcessor(temp_csv_file, user_id=None)
        result = processor.process()
        
        assert result['success'] is True
        assert result['tables_parsed'] == 1
        assert result['tables_valid'] == 1
        assert result['tables_stored'] == 1
        assert result['records_stored'] == 3
    
    def test_parser_selection(self):
        """Test correct parser selection by file type"""
        assert IngestionProcessor.PARSERS['.csv'] == CSVParser
        assert IngestionProcessor.PARSERS['.xlsx'] == ExcelParser
    
    def test_unsupported_file_type(self):
        """Test handling of unsupported file types"""
        processor = IngestionProcessor('/tmp/file.txt', user_id=None)
        result = processor.process()
        
        assert result['success'] is False
        assert len(result['errors']) > 0


class TestDataTable:
    """Test DataTable class"""
    
    def test_data_table_properties(self):
        """Test DataTable properties"""
        table = DataTable(
            name='test',
            headers=['A', 'B', 'C'],
            rows=[
                [1, 2, 3],
                [4, 5, 6],
            ]
        )
        
        assert table.row_count == 2
        assert table.col_count == 3
        assert len(table.to_dict_rows()) == 2
        
        first_row = table.to_dict_rows()[0]
        assert first_row['A'] == 1
        assert first_row['C'] == 3


class TestAdvancedValidators:
    """Test advanced validation rules"""
    
    def test_duplicate_finder(self, temp_csv_file):
        """Test finding duplicate rows"""
        # Create table with duplicates
        table = DataTable(
            name='test',
            headers=['Region', 'Year'],
            rows=[
                ['NE', 2024],
                ['SE', 2024],
                ['NE', 2024],  # Duplicate of row 1
            ]
        )
        
        validator = DuplicateValidator(table)
        duplicates = validator.find_duplicates()
        
        assert len(duplicates) == 1
        assert duplicates[0] == (1, 3)  # 1-based row indices
    
    def test_range_validator(self):
        """Test numeric range validation"""
        table = DataTable(
            name='test',
            headers=['Region', 'Score'],
            rows=[
                ['NE', 85],
                ['SE', 92],
                ['MW', 101],  # Out of range
            ]
        )
        
        validator = RangeValidator(table)
        errors = validator.validate_range('Score', 0, 100)
        
        # Should find 1 error for value 101
        assert any(e.message.find('101') >= 0 for e in errors)
    
    def test_consistency_validator_unique(self):
        """Test uniqueness validation"""
        table = DataTable(
            name='test',
            headers=['ID', 'Name'],
            rows=[
                [1, 'Alice'],
                [2, 'Bob'],
                [1, 'Charlie'],  # Duplicate ID
            ]
        )
        
        validator = ConsistencyValidator(table)
        errors = validator.validate_unique('ID')
        
        # Should find warning about duplicate
        assert len(errors) > 0
        assert any('Duplicate' in e.message for e in errors)
    
    def test_consistency_validator_no_nulls(self):
        """Test null checking"""
        table = DataTable(
            name='test',
            headers=['ID', 'Name'],
            rows=[
                [1, 'Alice'],
                [2, ''],  # Empty
                [3, 'Charlie'],
            ]
        )
        
        validator = ConsistencyValidator(table)
        errors = validator.validate_no_nulls('Name')
        
        # Should find error for empty name
        assert len(errors) == 1
        assert errors[0].row == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
