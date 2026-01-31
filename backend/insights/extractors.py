"""Insight extraction from imported data tables"""

import json
import statistics
from typing import List, Dict, Optional
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


class InsightExtractor:
    """Extract insights from data tables stored in database"""
    
    def __init__(self, data_table_id: int, session: Session):
        """
        Initialize extractor
        
        Args:
            data_table_id: ID of data_tables record
            session: SQLAlchemy database session
        """
        self.data_table_id = data_table_id
        self.session = session
        self.rows = self._load_rows()
        self.headers = self._load_headers()
    
    def _load_rows(self) -> List[dict]:
        """Load all rows for table from data_rows"""
        try:
            stmt = text("""
                SELECT row_data FROM data_rows
                WHERE data_table_id = :table_id
                ORDER BY row_index
            """)
            result = self.session.execute(stmt, {'table_id': self.data_table_id})
            return [row[0] for row in result.all()]
        except Exception:
            return []
    
    def _load_headers(self) -> List[str]:
        """Load column headers from data_tables"""
        try:
            stmt = text("""
                SELECT headers FROM data_tables
                WHERE id = :table_id
            """)
            result = self.session.execute(stmt, {'table_id': self.data_table_id})
            headers_json = result.scalar()
            if headers_json:
                return json.loads(headers_json)
            return []
        except Exception:
            return []
    
    def extract_statistics(self) -> Dict[str, dict]:
        """
        Calculate statistics for numeric columns
        
        Returns:
            Dict with stats per column {column: {mean, median, std_dev, min, max, ...}}
        """
        stats = {}
        
        for header in self.headers:
            # Extract values for this column
            values = []
            for row in self.rows:
                val = self._safe_float(row.get(header))
                if val is not None:
                    values.append(val)
            
            if not values:
                continue
            
            # Calculate statistics
            try:
                stats[header] = {
                    'count': len(values),
                    'mean': round(statistics.mean(values), 2),
                    'median': round(statistics.median(values), 2),
                    'std_dev': round(statistics.stdev(values) if len(values) > 1 else 0, 2),
                    'min': round(min(values), 2),
                    'max': round(max(values), 2),
                }
            except Exception:
                continue
        
        return stats
    
    def detect_patterns(self) -> List[Dict]:
        """
        Find repeating patterns (frequent values)
        
        Returns:
            List of pattern dicts with metric, value, frequency, percentage
        """
        patterns = []
        
        for header in self.headers:
            value_counts = {}
            
            # Count occurrences
            for row in self.rows:
                val = row.get(header)
                if val is not None:
                    str_val = str(val).strip()
                    if str_val:
                        value_counts[str_val] = value_counts.get(str_val, 0) + 1
            
            # Find frequent values (>10% of rows)
            total_rows = len(self.rows)
            for value, count in value_counts.items():
                percentage = 100 * count / total_rows if total_rows > 0 else 0
                
                if percentage > 10:  # At least 10%
                    patterns.append({
                        'type': 'frequent_value',
                        'metric': header,
                        'value': value,
                        'frequency': count,
                        'percentage': round(percentage, 1),
                    })
        
        return sorted(patterns, key=lambda x: x['frequency'], reverse=True)
    
    def detect_anomalies(self) -> List[Dict]:
        """
        Find outliers using Interquartile Range (IQR) method
        
        Returns:
            List of anomaly dicts with metric, row_index, value, reason
        """
        anomalies = []
        
        for header in self.headers:
            # Extract numeric values with indices
            values_with_idx = []
            for i, row in enumerate(self.rows):
                val = self._safe_float(row.get(header))
                if val is not None:
                    values_with_idx.append((i, val))
            
            if len(values_with_idx) < 4:
                continue  # Need at least 4 values
            
            # Sort for quartile calculation
            values_only = sorted([v for _, v in values_with_idx])
            
            # Calculate quartiles
            q1_idx = len(values_only) // 4
            q3_idx = 3 * len(values_only) // 4
            q1 = values_only[q1_idx]
            q3 = values_only[q3_idx]
            iqr = q3 - q1
            
            if iqr == 0:
                continue
            
            # Find outliers
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            for row_idx, val in values_with_idx:
                if val < lower_bound or val > upper_bound:
                    anomalies.append({
                        'type': 'outlier',
                        'metric': header,
                        'row_index': row_idx,
                        'value': round(val, 2),
                        'reason': f"Outside IQR bounds ({lower_bound:.2f}, {upper_bound:.2f})",
                    })
        
        return anomalies[:10]  # Limit to 10 most extreme
    
    def analyze_trends(self) -> List[Dict]:
        """
        Detect temporal trends (if data has date/time column)
        
        Returns:
            List of trend dicts
        """
        trends = []
        
        # Look for columns that might be time-based
        date_columns = [h for h in self.headers 
                       if 'date' in h.lower() or 'time' in h.lower() or 'year' in h.lower()]
        
        if not date_columns:
            return trends
        
        # For MVP, just identify if data is time-series
        for col in date_columns:
            trends.append({
                'type': 'temporal',
                'metric': col,
                'data_type': 'date_column',
                'note': 'Time-series column detected - detailed trend analysis in Phase 6',
            })
        
        return trends
    
    @staticmethod
    def _safe_float(value: any) -> Optional[float]:
        """Safely convert value to float, return None if not convertible"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def get_all_insights(self) -> Dict:
        """Get all insights for table"""
        return {
            'statistics': self.extract_statistics(),
            'patterns': self.detect_patterns(),
            'anomalies': self.detect_anomalies(),
            'trends': self.analyze_trends(),
        }
