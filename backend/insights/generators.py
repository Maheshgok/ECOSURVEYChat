"""Summary generation from extracted insights"""

from typing import Dict, List, Optional


class SummaryGenerator:
    """Generate human-readable summaries from insights"""
    
    def __init__(self, insights: Dict, table_name: str):
        """
        Initialize generator
        
        Args:
            insights: Dict with 'statistics', 'patterns', 'anomalies', 'trends'
            table_name: Name of data table for context
        """
        self.insights = insights
        self.table_name = table_name
    
    def generate_executive_summary(self) -> str:
        """
        Generate 2-3 sentence high-level summary
        
        Returns:
            Concise summary string
        """
        lines = []
        
        # Introduction
        lines.append(f"Summary of {self.table_name}:")
        
        # Record count
        stats = self.insights.get('statistics', {})
        if stats:
            first_stat = next(iter(stats.values()))
            if first_stat.get('count'):
                lines.append(f"Contains {first_stat['count']} records.")
        
        # Key pattern
        patterns = self.insights.get('patterns', [])
        if patterns:
            pattern = patterns[0]
            lines.append(
                f"Key finding: {pattern['metric']} = '{pattern['value']}' "
                f"({pattern['percentage']:.0f}% of records)."
            )
        
        # Anomaly warning
        anomalies = self.insights.get('anomalies', [])
        if anomalies:
            count = len(anomalies)
            lines.append(f"Detected {count} anomalous values requiring attention.")
        
        return " ".join(lines)
    
    def generate_detailed_summary(self) -> str:
        """
        Generate multi-paragraph detailed summary
        
        Returns:
            Detailed summary with sections
        """
        sections = []
        
        # Overview
        sections.append(self._section_overview())
        
        # Statistics
        stats_section = self._section_statistics()
        if stats_section:
            sections.append(stats_section)
        
        # Patterns
        patterns_section = self._section_patterns()
        if patterns_section:
            sections.append(patterns_section)
        
        # Anomalies
        anomalies_section = self._section_anomalies()
        if anomalies_section:
            sections.append(anomalies_section)
        
        # Trends
        trends_section = self._section_trends()
        if trends_section:
            sections.append(trends_section)
        
        return "\n\n".join([s for s in sections if s])
    
    def _section_overview(self) -> str:
        """Overview section"""
        lines = ["## Overview"]
        
        stats = self.insights.get('statistics', {})
        if stats:
            count = next(iter(stats.values())).get('count', 0)
            cols = len(stats)
            lines.append(f"This dataset contains {count} records across {cols} numeric variables.")
        
        return "\n".join(lines)
    
    def _section_statistics(self) -> Optional[str]:
        """Statistics section"""
        stats = self.insights.get('statistics', {})
        if not stats:
            return None
        
        lines = ["## Statistical Summary"]
        
        for metric, values in stats.items():
            if values:
                lines.append(f"\n**{metric}:**")
                lines.append(f"  - Mean: {values.get('mean', 'N/A')}")
                lines.append(f"  - Median: {values.get('median', 'N/A')}")
                lines.append(f"  - Range: {values.get('min', 'N/A')} to {values.get('max', 'N/A')}")
        
        return "\n".join(lines)
    
    def _section_patterns(self) -> Optional[str]:
        """Patterns section"""
        patterns = self.insights.get('patterns', [])
        if not patterns:
            return None
        
        lines = ["## Key Patterns Detected"]
        
        for pattern in patterns[:5]:  # Top 5 patterns
            lines.append(
                f"- **{pattern['metric']}**: Value '{pattern['value']}' "
                f"appears {pattern['frequency']} times ({pattern['percentage']:.0f}%)"
            )
        
        return "\n".join(lines)
    
    def _section_anomalies(self) -> Optional[str]:
        """Anomalies section"""
        anomalies = self.insights.get('anomalies', [])
        if not anomalies:
            return None
        
        lines = ["## Anomalies & Outliers"]
        lines.append(f"Found {len(anomalies)} anomalous values:")
        
        for anomaly in anomalies[:5]:  # Top 5 anomalies
            lines.append(
                f"- **Row {anomaly['row_index']}**: {anomaly['metric']} = {anomaly['value']} "
                f"({anomaly['reason']})"
            )
        
        return "\n".join(lines)
    
    def _section_trends(self) -> Optional[str]:
        """Trends section"""
        trends = self.insights.get('trends', [])
        if not trends:
            return None
        
        lines = ["## Temporal Patterns"]
        
        for trend in trends:
            if trend['data_type'] == 'date_column':
                lines.append(f"- Time-series column detected: {trend['metric']}")
        
        if len(lines) == 1:
            return None
        
        return "\n".join(lines)
    
    def get_key_points(self) -> List[str]:
        """Extract key bullet points from insights"""
        points = []
        
        # Add patterns
        for pattern in self.insights.get('patterns', [])[:3]:
            points.append(
                f"{pattern['metric']} '{pattern['value']}' is "
                f"{pattern['percentage']:.0f}% of values"
            )
        
        # Add anomalies
        if self.insights.get('anomalies'):
            points.append(f"{len(self.insights['anomalies'])} outlier values detected")
        
        # Add statistic highlights
        stats = self.insights.get('statistics', {})
        for metric, values in list(stats.items())[:2]:
            if values.get('mean'):
                points.append(
                    f"{metric} averages {values['mean']} "
                    f"(range {values['min']}-{values['max']})"
                )
        
        return points
