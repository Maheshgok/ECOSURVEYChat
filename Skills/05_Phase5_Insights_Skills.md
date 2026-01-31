# Phase 5: Insights & Summaries Skills Guide

**Status:** Ready to Implement  
**Estimated Duration:** 2-3 hours  
**Goal:** Extract insights and generate summaries from imported data

---

## Phase Overview

Phase 5 transforms raw imported data into actionable insights:

1. **Insight Extraction** - Identify patterns, trends, and anomalies
2. **Summary Generation** - Create human-readable text summaries
3. **Embedding Creation** - Build searchable representations
4. **Briefing Templates** - Structure insights into documents
5. **Trend Analysis** - Detect temporal patterns

---

## Architecture

```
Phase 4 Output
     ↓
[Data stored in data_rows - by user/table]
     ↓
InsightExtractor
├── Statistical Analysis
├── Pattern Detection
├── Anomaly Detection
└── Trend Analysis
     ↓
SummaryGenerator
├── Natural language generation
├── Context-aware templates
└── Hierarchical organization
     ↓
EmbeddingService
├── Vector representation
├── Semantic search
└── Similarity matching
     ↓
BriefingBuilder
├── Document assembly
├── Formatting
└── Output generation
     ↓
Database & API
```

---

## Key Concepts

### InsightExtractor Pattern

```python
class InsightExtractor:
    """Extract insights from imported data"""
    
    def __init__(self, data_table_id: int, session: Session):
        self.data_table_id = data_table_id
        self.session = session
    
    def extract_statistics(self) -> dict:
        """Get basic statistics (mean, median, std dev)"""
        pass
    
    def detect_patterns(self) -> List[Pattern]:
        """Find repeating patterns in data"""
        pass
    
    def detect_anomalies(self) -> List[Anomaly]:
        """Find outliers and unusual values"""
        pass
    
    def analyze_trends(self) -> List[Trend]:
        """Identify temporal patterns"""
        pass
```

### Insight Types

```python
@dataclass
class Insight:
    """Single extracted insight"""
    type: str  # 'statistic', 'pattern', 'anomaly', 'trend'
    metric: str  # What is being measured
    value: Any  # The insight value
    confidence: float  # 0.0-1.0 confidence score
    description: str  # Human-readable description
    supporting_data: dict  # Evidence

class Statistics:
    """Table-level statistics"""
    count: int
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    quartiles: dict

class Pattern:
    """Detected pattern"""
    type: str  # 'correlation', 'sequence', 'grouping'
    elements: List[str]  # Involved columns/values
    frequency: int  # How many times observed
    strength: float  # 0.0-1.0

class Trend:
    """Temporal trend"""
    metric: str
    direction: str  # 'increasing', 'decreasing', 'stable'
    rate: float  # Change per period
    confidence: float
```

### SummaryGenerator Pattern

```python
class SummaryGenerator:
    """Generate human-readable summaries"""
    
    def __init__(self, insights: List[Insight]):
        self.insights = insights
    
    def generate_executive_summary(self) -> str:
        """2-3 sentence high-level summary"""
        pass
    
    def generate_detailed_summary(self) -> str:
        """Multi-paragraph detailed analysis"""
        pass
    
    def generate_section_summary(self, section: str) -> str:
        """Summarize specific section/metric"""
        pass
```

### Embedding Service Pattern

```python
class EmbeddingService:
    """Create vector embeddings for search"""
    
    def __init__(self, model: str = 'sentence-transformers'):
        self.model = model  # Can use OpenAI, Sentence Transformers, etc
    
    def embed_text(self, text: str) -> List[float]:
        """Convert text to vector (e.g., 384 or 1536 dims)"""
        pass
    
    def embed_insight(self, insight: Insight) -> List[float]:
        """Create embedding from insight"""
        pass
    
    def similarity_search(self, query: str, 
                        embeddings: List[List[float]]) -> List[tuple]:
        """Find most relevant insights"""
        pass
```

---

## Implementation Steps

### Step 1: Database Updates

Create new migration or update existing:

```sql
-- Storage for insights
CREATE TABLE IF NOT EXISTS insights (
    id BIGSERIAL PRIMARY KEY,
    data_table_id INTEGER NOT NULL REFERENCES data_tables(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    insight_type VARCHAR(50),  -- 'statistic', 'pattern', 'anomaly', 'trend'
    metric VARCHAR(255),
    value JSONB,
    confidence FLOAT,
    description TEXT,
    supporting_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Storage for embeddings
CREATE TABLE IF NOT EXISTS insight_embeddings (
    id BIGSERIAL PRIMARY KEY,
    insight_id BIGINT NOT NULL REFERENCES insights(id),
    embedding VECTOR(384),  -- Or 1536 for OpenAI
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Storage for summaries
CREATE TABLE IF NOT EXISTS summaries (
    id BIGSERIAL PRIMARY KEY,
    data_table_id INTEGER NOT NULL REFERENCES data_tables(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    summary_type VARCHAR(50),  -- 'executive', 'detailed', 'section'
    content TEXT,
    key_points TEXT[],
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_insights_table_id ON insights(data_table_id);
CREATE INDEX idx_insights_user_id ON insights(user_id);
CREATE INDEX idx_summaries_table_id ON summaries(data_table_id);
```

### Step 2: Create InsightExtractor

Create `backend/insights/extractors.py`:

```python
from typing import List, Dict
import statistics
from datetime import datetime

class InsightExtractor:
    """Extract insights from data tables"""
    
    def __init__(self, data_table_id: int, session: Session):
        self.data_table_id = data_table_id
        self.session = session
        self.rows = self._load_rows()
        self.headers = self._load_headers()
    
    def _load_rows(self) -> List[dict]:
        """Load all rows for table from data_rows"""
        stmt = text("""
            SELECT row_data FROM data_rows
            WHERE data_table_id = :table_id
            ORDER BY row_index
        """)
        result = self.session.execute(stmt, {'table_id': self.data_table_id})
        return [row[0] for row in result.all()]
    
    def _load_headers(self) -> List[str]:
        """Load headers from data_tables"""
        stmt = text("""
            SELECT headers FROM data_tables
            WHERE id = :table_id
        """)
        result = self.session.execute(stmt, {'table_id': self.data_table_id})
        headers_json = result.scalar()
        return json.loads(headers_json)
    
    def extract_statistics(self) -> Dict:
        """Calculate basic statistics for numeric columns"""
        stats = {}
        
        for header in self.headers:
            values = [self._safe_float(row.get(header)) 
                     for row in self.rows]
            valid_values = [v for v in values if v is not None]
            
            if not valid_values:
                continue
            
            stats[header] = {
                'count': len(valid_values),
                'mean': statistics.mean(valid_values),
                'median': statistics.median(valid_values),
                'std_dev': statistics.stdev(valid_values) if len(valid_values) > 1 else 0,
                'min': min(valid_values),
                'max': max(valid_values),
            }
        
        return stats
    
    def detect_patterns(self) -> List[Dict]:
        """Find repeating patterns"""
        patterns = []
        
        # Find value distributions
        for header in self.headers:
            value_counts = {}
            for row in self.rows:
                val = row.get(header)
                if val:
                    value_counts[str(val)] = value_counts.get(str(val), 0) + 1
            
            # Find frequent values
            for value, count in value_counts.items():
                if count > len(self.rows) * 0.1:  # >10% frequency
                    patterns.append({
                        'type': 'frequent_value',
                        'metric': header,
                        'value': value,
                        'frequency': count,
                        'percentage': 100 * count / len(self.rows),
                    })
        
        return patterns
    
    def detect_anomalies(self) -> List[Dict]:
        """Find outliers using IQR method"""
        anomalies = []
        
        for header in self.headers:
            values = [self._safe_float(row.get(header)) 
                     for row in self.rows]
            valid_values = sorted([v for v in values if v is not None])
            
            if len(valid_values) < 4:
                continue
            
            # Calculate IQR
            q1 = valid_values[len(valid_values)//4]
            q3 = valid_values[3*len(valid_values)//4]
            iqr = q3 - q1
            
            # Find outliers
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            for i, row in enumerate(self.rows):
                val = self._safe_float(row.get(header))
                if val and (val < lower_bound or val > upper_bound):
                    anomalies.append({
                        'type': 'outlier',
                        'metric': header,
                        'row_index': i,
                        'value': val,
                        'reason': f"Outside IQR bounds [{lower_bound}, {upper_bound}]",
                    })
        
        return anomalies
    
    @staticmethod
    def _safe_float(value) -> float:
        """Safely convert to float"""
        try:
            return float(value) if value else None
        except (ValueError, TypeError):
            return None
```

### Step 3: Create SummaryGenerator

Create `backend/insights/generators.py`:

```python
class SummaryGenerator:
    """Generate human-readable summaries from insights"""
    
    def __init__(self, insights: List[Dict], table_name: str):
        self.insights = insights
        self.table_name = table_name
    
    def generate_executive_summary(self) -> str:
        """Generate 2-3 sentence high-level summary"""
        lines = [f"Summary of {self.table_name}:"]
        
        # Add count
        if 'statistics' in self.insights:
            stats = self.insights['statistics']
            first_stat = next(iter(stats.values()))
            lines.append(f"Contains {first_stat['count']} records.")
        
        # Add key finding
        if 'patterns' in self.insights and self.insights['patterns']:
            pattern = self.insights['patterns'][0]
            lines.append(
                f"Notable pattern: {pattern['value']} appears in "
                f"{pattern['percentage']:.0f}% of records."
            )
        
        # Add anomalies warning
        if 'anomalies' in self.insights and self.insights['anomalies']:
            count = len(self.insights['anomalies'])
            lines.append(f"Detected {count} anomalous values.")
        
        return " ".join(lines)
    
    def generate_detailed_summary(self) -> str:
        """Generate multi-paragraph detailed summary"""
        sections = []
        
        # Statistics section
        if 'statistics' in self.insights:
            sections.append(self._format_statistics())
        
        # Patterns section
        if 'patterns' in self.insights:
            sections.append(self._format_patterns())
        
        # Anomalies section
        if 'anomalies' in self.insights:
            sections.append(self._format_anomalies())
        
        return "\n\n".join(sections)
    
    def _format_statistics(self) -> str:
        """Format statistics section"""
        lines = ["## Statistical Summary"]
        
        for metric, stats in self.insights['statistics'].items():
            lines.append(f"\n### {metric}")
            lines.append(f"- Count: {stats['count']}")
            lines.append(f"- Mean: {stats['mean']:.2f}")
            lines.append(f"- Range: {stats['min']:.2f} to {stats['max']:.2f}")
        
        return "\n".join(lines)
    
    def _format_patterns(self) -> str:
        """Format patterns section"""
        lines = ["## Key Patterns"]
        
        for pattern in self.insights['patterns']:
            lines.append(
                f"- {pattern['metric']}: '{pattern['value']}' "
                f"appears {pattern['frequency']} times "
                f"({pattern['percentage']:.0f}%)"
            )
        
        return "\n".join(lines)
    
    def _format_anomalies(self) -> str:
        """Format anomalies section"""
        lines = ["## Anomalies Detected"]
        
        for anomaly in self.insights['anomalies'][:5]:  # Limit to 5
            lines.append(
                f"- Row {anomaly['row_index']}: "
                f"{anomaly['metric']}={anomaly['value']} "
                f"({anomaly['reason']})"
            )
        
        return "\n".join(lines)
```

### Step 4: Create Embedding Service

Create `backend/insights/embeddings.py`:

```python
import numpy as np
from typing import List

class EmbeddingService:
    """Create and manage embeddings for semantic search"""
    
    def __init__(self, model_type: str = 'simple'):
        """
        Initialize embedding service
        
        Args:
            model_type: 'simple' (TF-IDF) or 'transformer' (requires additional packages)
        """
        self.model_type = model_type
        if model_type == 'simple':
            self._init_simple_embedder()
    
    def _init_simple_embedder(self):
        """Initialize simple TF-IDF embedder"""
        self.vocab = {}
        self.idf_scores = {}
    
    def embed_text(self, text: str) -> List[float]:
        """
        Create embedding from text
        
        For MVP: Use simple TF-IDF
        For production: Use sentence-transformers or OpenAI
        
        Returns:
            Vector representation (384 or 1536 dimensions)
        """
        words = text.lower().split()
        
        # TF-IDF based embedding
        term_frequencies = {}
        for word in words:
            term_frequencies[word] = term_frequencies.get(word, 0) + 1
        
        # Build vocabulary if needed
        for word in term_frequencies:
            if word not in self.vocab:
                self.vocab[word] = len(self.vocab)
        
        # Create vector
        vector = [0.0] * len(self.vocab)
        for word, tf in term_frequencies.items():
            idx = self.vocab[word]
            idf = self.idf_scores.get(word, 1.0)
            vector[idx] = tf * idf
        
        # Normalize
        norm = sum(v**2 for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    def embed_insight(self, insight: Dict) -> List[float]:
        """Create embedding from insight"""
        text = f"{insight['metric']} {insight['value']} {insight['description']}"
        return self.embed_text(text)
    
    @staticmethod
    def similarity_search(query: str, embeddings: List[Dict]) -> List[tuple]:
        """
        Find most relevant embeddings
        
        Returns:
            List of (embedding_id, similarity_score) sorted by relevance
        """
        # Simple cosine similarity
        results = []
        
        for embedding in embeddings:
            similarity = np.dot(query, embedding['vector'])
            results.append((embedding['id'], similarity))
        
        return sorted(results, key=lambda x: x[1], reverse=True)
```

### Step 5: Update Models & API

Add to `backend/app/models/__init__.py`:

```python
class Insight(Base):
    __tablename__ = "insights"
    id: Mapped[int] = mapped_column(primary_key=True)
    data_table_id: Mapped[int] = mapped_column(ForeignKey("data_tables.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    insight_type: Mapped[str]  # statistic, pattern, anomaly, trend
    metric: Mapped[str]
    value: Mapped[dict] = mapped_column(JSONB)
    confidence: Mapped[float]
    description: Mapped[str]
    supporting_data: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime]

class Summary(Base):
    __tablename__ = "summaries"
    id: Mapped[int] = mapped_column(primary_key=True)
    data_table_id: Mapped[int] = mapped_column(ForeignKey("data_tables.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    summary_type: Mapped[str]  # executive, detailed, section
    content: Mapped[str]
    key_points: Mapped[list] = mapped_column(ARRAY(String))
    metadata: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime]
```

### Step 6: Create API Endpoints

Create `backend/app/api/insights.py`:

```python
@router.post("/api/insights/extract/{table_id}")
async def extract_insights(
    table_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """Extract insights from imported data"""
    # Verify access
    session_data = verify_session_token(token)
    user_id = session_data['user_id']
    
    # Extract
    extractor = InsightExtractor(table_id, db)
    
    results = {
        'statistics': extractor.extract_statistics(),
        'patterns': extractor.detect_patterns(),
        'anomalies': extractor.detect_anomalies(),
    }
    
    return results

@router.post("/api/summaries/generate/{table_id}")
async def generate_summary(
    table_id: int,
    summary_type: str = Query('executive'),
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """Generate summary from extracted insights"""
    # Get insights
    insights = get_insights_for_table(table_id, db)
    
    # Generate
    generator = SummaryGenerator(insights, table_name)
    
    if summary_type == 'executive':
        content = generator.generate_executive_summary()
    else:
        content = generator.generate_detailed_summary()
    
    return {'summary': content}
```

---

## Data Processing Example

```python
# 1. Load imported data
data = query_data_rows(table_id)
# → 100 rows of economic survey data

# 2. Extract insights
extractor = InsightExtractor(table_id, session)
stats = extractor.extract_statistics()
# → {'GDP': {mean: 3.1, median: 3.0, ...}, ...}

patterns = extractor.detect_patterns()
# → [{metric: 'Region', value: 'NE', frequency: 45, %: 45%}, ...]

anomalies = extractor.detect_anomalies()
# → [{metric: 'GDP', value: 10.5, reason: "Outlier"}, ...]

# 3. Generate summary
generator = SummaryGenerator({
    'statistics': stats,
    'patterns': patterns,
    'anomalies': anomalies
}, 'Economic Survey')

summary = generator.generate_executive_summary()
# → "Summary of Economic Survey: Contains 100 records. 
#    Notable pattern: NE appears in 45% of records. 
#    Detected 2 anomalous values."

# 4. Store results
store_insights(insights, table_id, user_id)
store_summary(summary, table_id, user_id)
```

---

## Testing Strategy

### Unit Tests
```python
class TestInsightExtractor:
    def test_statistics_calculation()
    def test_pattern_detection()
    def test_anomaly_detection()

class TestSummaryGenerator:
    def test_executive_summary()
    def test_detailed_summary()

class TestEmbeddings:
    def test_text_embedding()
    def test_similarity_search()
```

### Integration Tests
```python
class TestInsightPipeline:
    def test_full_extraction_pipeline()
    def test_insight_storage()
    def test_api_endpoints()
```

---

## Performance Considerations

1. **Caching**
   - Cache extracted insights (don't re-extract)
   - Cache generated summaries

2. **Batch Processing**
   - Extract insights for multiple tables
   - Batch store results

3. **Incremental Updates**
   - Only process new rows
   - Update summary when data changes

---

## Success Criteria

✅ Extract statistics (mean, median, std dev)  
✅ Detect patterns (frequent values)  
✅ Find anomalies (IQR-based outliers)  
✅ Generate natural language summaries  
✅ Create embeddings for search  
✅ Store insights in database  
✅ Query insights by table/user  
✅ API endpoints working  
✅ Tests passing  

---

## Files to Create/Modify

| File | Lines | Purpose |
|------|-------|---------|
| 005_add_insights.sql | 80 | New tables |
| insights/extractors.py | 150 | Statistics & patterns |
| insights/generators.py | 120 | Summary generation |
| insights/embeddings.py | 100 | Vector embeddings |
| app/api/insights.py | 150 | API endpoints |
| app/models/__init__.py | +40 | Insight/Summary models |
| tests/test_insights.py | 200 | Unit & integration tests |

---

*Phase 5 Skills Guide - January 31, 2026*
