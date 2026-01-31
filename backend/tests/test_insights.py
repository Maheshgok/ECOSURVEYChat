"""Tests for Phase 5 insights and summaries"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import json

from app.core.database import Base
from app.models import (
    User, DataTable, DataColumn, DataRow,
    Insight, Summary, InsightEmbedding
)
from insights.extractors import InsightExtractor
from insights.generators import SummaryGenerator
from insights.embeddings import EmbeddingService


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def db_engine():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for each test"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create test user"""
    user = User(
        google_id="test123",
        email="test@example.com",
        name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_data_table(db_session: Session, test_user: User) -> DataTable:
    """Create test data table with sample data"""
    table = DataTable(
        user_id=test_user.id,
        name="Sales Data",
        row_count=100,
        file_id=1
    )
    db_session.add(table)
    db_session.flush()
    
    # Add columns
    col_amount = DataColumn(
        data_table_id=table.id,
        name="Amount",
        data_type="numeric"
    )
    col_product = DataColumn(
        data_table_id=table.id,
        name="Product",
        data_type="text"
    )
    db_session.add(col_amount)
    db_session.add(col_product)
    db_session.flush()
    
    # Add sample rows
    sample_data = [
        {"Amount": 100.0, "Product": "Widget"},
        {"Amount": 150.0, "Product": "Widget"},
        {"Amount": 200.0, "Product": "Gadget"},
        {"Amount": 100.0, "Product": "Widget"},
        {"Amount": 5000.0, "Product": "Device"},  # Outlier
    ]
    
    for row_data in sample_data:
        row = DataRow(
            data_table_id=table.id,
            row_index=len(table.rows),
            row_data=row_data
        )
        db_session.add(row)
    
    db_session.commit()
    return table


# ============================================================================
# Test InsightExtractor
# ============================================================================

class TestInsightExtractor:
    """Test insight extraction"""
    
    def test_extract_statistics(self, db_session: Session, test_data_table: DataTable):
        """Test statistical extraction"""
        extractor = InsightExtractor(test_data_table.id, db_session)
        stats = extractor.extract_statistics()
        
        assert "Amount" in stats
        assert "mean" in stats["Amount"]
        assert "median" in stats["Amount"]
        assert stats["Amount"]["count"] == 5
    
    def test_detect_patterns(self, db_session: Session, test_data_table: DataTable):
        """Test pattern detection"""
        extractor = InsightExtractor(test_data_table.id, db_session)
        patterns = extractor.detect_patterns()
        
        # Widget appears 3/5 times = 60% > 10%
        widget_patterns = [p for p in patterns if p["value"] == "Widget"]
        assert len(widget_patterns) > 0
        assert widget_patterns[0]["percentage"] >= 60
    
    def test_detect_anomalies(self, db_session: Session, test_data_table: DataTable):
        """Test anomaly detection"""
        extractor = InsightExtractor(test_data_table.id, db_session)
        anomalies = extractor.detect_anomalies()
        
        # Should detect 5000 as outlier
        assert len(anomalies) > 0
        assert any(a["value"] > 1000 for a in anomalies)
    
    def test_get_all_insights(self, db_session: Session, test_data_table: DataTable):
        """Test aggregated insights"""
        extractor = InsightExtractor(test_data_table.id, db_session)
        insights = extractor.get_all_insights()
        
        assert "statistics" in insights
        assert "patterns" in insights
        assert "anomalies" in insights
        assert "trends" in insights


# ============================================================================
# Test SummaryGenerator
# ============================================================================

class TestSummaryGenerator:
    """Test summary generation"""
    
    def test_executive_summary(self):
        """Test executive summary generation"""
        insights = {
            "statistics": {
                "Amount": {
                    "count": 100,
                    "mean": 150.5,
                    "median": 145.0,
                    "std_dev": 45.2,
                    "min": 10,
                    "max": 500
                }
            },
            "patterns": [
                {
                    "metric": "Product",
                    "value": "Widget",
                    "frequency": 60,
                    "percentage": 60.0
                }
            ],
            "anomalies": [
                {
                    "metric": "Amount",
                    "row_index": 50,
                    "value": 5000,
                    "reason": "Exceeds upper bound"
                }
            ],
            "trends": []
        }
        
        generator = SummaryGenerator(insights, "Sales Data")
        summary = generator.generate_executive_summary()
        
        assert "Sales Data" in summary
        assert "Widget" in summary or "records" in summary
        assert isinstance(summary, str)
    
    def test_detailed_summary(self):
        """Test detailed summary generation"""
        insights = {
            "statistics": {
                "Amount": {
                    "mean": 150.5,
                    "median": 145.0,
                    "min": 10,
                    "max": 500
                }
            },
            "patterns": [
                {
                    "metric": "Product",
                    "value": "Widget",
                    "frequency": 60,
                    "percentage": 60.0
                }
            ],
            "anomalies": [
                {
                    "metric": "Amount",
                    "row_index": 50,
                    "value": 5000,
                    "reason": "Exceeds upper bound"
                }
            ],
            "trends": []
        }
        
        generator = SummaryGenerator(insights, "Sales Data")
        summary = generator.generate_detailed_summary()
        
        assert "## " in summary  # Has markdown sections
        assert isinstance(summary, str)
        assert len(summary) > 50
    
    def test_key_points(self):
        """Test key points extraction"""
        insights = {
            "statistics": {
                "Amount": {
                    "mean": 150.5,
                    "median": 145.0,
                    "min": 10,
                    "max": 500
                }
            },
            "patterns": [
                {
                    "metric": "Product",
                    "value": "Widget",
                    "frequency": 60,
                    "percentage": 60.0
                }
            ],
            "anomalies": [
                {
                    "metric": "Amount",
                    "row_index": 50,
                    "value": 5000,
                    "reason": "Exceeds upper bound"
                }
            ],
            "trends": []
        }
        
        generator = SummaryGenerator(insights, "Sales Data")
        points = generator.get_key_points()
        
        assert isinstance(points, list)
        assert len(points) > 0
        assert all(isinstance(p, str) for p in points)


# ============================================================================
# Test EmbeddingService
# ============================================================================

class TestEmbeddingService:
    """Test embedding generation"""
    
    def test_embed_text(self):
        """Test text embedding"""
        service = EmbeddingService()
        embedding = service.embed_text("Sales data analysis")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 100
        assert all(isinstance(x, float) for x in embedding)
    
    def test_embed_insight(self):
        """Test insight embedding"""
        service = EmbeddingService()
        insight = {
            "metric": "Amount",
            "value": "150.5",
            "description": "Average sales amount"
        }
        embedding = service.embed_insight(insight)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 100
    
    def test_similarity(self):
        """Test similarity calculation"""
        service = EmbeddingService()
        embed1 = service.embed_text("sales data")
        embed2 = service.embed_text("sales information")
        
        similarity = service.similarity(embed1, embed2)
        
        assert 0 <= similarity <= 1
        assert similarity > 0  # Similar texts should have some similarity
    
    def test_similarity_search(self):
        """Test similarity search"""
        service = EmbeddingService()
        
        query = service.embed_text("sales amount")
        candidates = [
            ("insight1", service.embed_text("sales amount")),
            ("insight2", service.embed_text("product category")),
            ("insight3", service.embed_text("sales figure")),
        ]
        
        results = service.similarity_search(query, candidates, top_k=2)
        
        assert len(results) <= 2
        assert all(isinstance(r[0], str) for r in results)
        assert all(0 <= r[1] <= 1 for r in results)
    
    def test_batch_embed(self):
        """Test batch embedding"""
        service = EmbeddingService()
        texts = ["sales data", "product info", "customer feedback"]
        
        embeddings = service.batch_embed(texts)
        
        assert len(embeddings) == 3
        assert all(len(e) == 100 for e in embeddings)


# ============================================================================
# Test Model Relationships
# ============================================================================

class TestInsightModels:
    """Test database models"""
    
    def test_insight_creation(self, db_session: Session, test_user: User, test_data_table: DataTable):
        """Test creating insights"""
        insight = Insight(
            data_table_id=test_data_table.id,
            user_id=test_user.id,
            insight_type="statistic",
            metric="Amount",
            value="150.5",
            confidence=0.95,
            description="Average sales amount",
            supporting_data={"mean": 150.5, "count": 100}
        )
        db_session.add(insight)
        db_session.commit()
        
        retrieved = db_session.query(Insight).filter(
            Insight.id == insight.id
        ).first()
        
        assert retrieved is not None
        assert retrieved.metric == "Amount"
        assert retrieved.confidence == 0.95
    
    def test_summary_creation(self, db_session: Session, test_user: User, test_data_table: DataTable):
        """Test creating summaries"""
        summary = Summary(
            data_table_id=test_data_table.id,
            user_id=test_user.id,
            summary_type="executive",
            content="This dataset contains sales information...",
            key_points=["Widget is most common product", "Average sale: $150"],
            metadata={"method": "rule-based", "version": "1.0"}
        )
        db_session.add(summary)
        db_session.commit()
        
        retrieved = db_session.query(Summary).filter(
            Summary.id == summary.id
        ).first()
        
        assert retrieved is not None
        assert retrieved.summary_type == "executive"
        assert len(retrieved.key_points) == 2
    
    def test_embedding_creation(self, db_session: Session, test_user: User, test_data_table: DataTable):
        """Test creating embeddings"""
        # Create insight first
        insight = Insight(
            data_table_id=test_data_table.id,
            user_id=test_user.id,
            insight_type="statistic",
            metric="Amount",
            value="150.5",
            confidence=0.95
        )
        db_session.add(insight)
        db_session.flush()
        
        # Create embedding
        embedding = InsightEmbedding(
            insight_id=insight.id,
            embedding=[0.1, 0.2, 0.3],
            embedding_model="tfidf"
        )
        db_session.add(embedding)
        db_session.commit()
        
        retrieved = db_session.query(InsightEmbedding).filter(
            InsightEmbedding.id == embedding.id
        ).first()
        
        assert retrieved is not None
        assert retrieved.embedding_model == "tfidf"
        assert len(retrieved.embedding) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
