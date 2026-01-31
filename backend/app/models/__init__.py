"""
SQLAlchemy models for Economic Survey Practitioner Chat v1.2
Maps to PostgreSQL schema from migrations/001_init.sql
"""

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ARRAY, UUID, CheckConstraint, ForeignKey, Boolean, Date
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, TSVECTOR, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid

from app.core.database import Base


# ============================================================================
# PHASE 2: Authentication Models (User & Session)
# ============================================================================

class User(Base):
    """User account created via Google OAuth"""
    __tablename__ = "users"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    picture = Column(String(500))
    email_verified = Column(Boolean, default=False)
    
    # Login tracking
    first_login = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user")
    retrieval_events = relationship("RetrievalEvent", back_populates="user")


class Session(Base):
    """Session token created at login"""
    __tablename__ = "sessions"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), unique=True, nullable=False, index=True)
    
    # Session metadata
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(String(500))
    
    # Session tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    is_active = Column(Boolean, default=True, index=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")


# ============================================================================
# PHASE 1: Core Data Models (existing)
# ============================================================================

class Corpus(Base):
    """A collection of documents (Survey + supplements + datasets)"""
    __tablename__ = "corpora"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    documents = relationship("Document", back_populates="corpus", cascade="all, delete-orphan")
    topic_briefs = relationship("TopicBrief", back_populates="corpus", cascade="all, delete-orphan")
    claim_cards = relationship("ClaimCard", back_populates="corpus", cascade="all, delete-orphan")


class Document(Base):
    """A PDF, XLSX, HTML, or supplement"""
    __tablename__ = "documents"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corpus_id = Column(PG_UUID(as_uuid=True), ForeignKey("corpora.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    year = Column(Integer)
    volume = Column(Integer)
    role = Column(String(20), nullable=False, default="primary")  # 'primary' or 'supplement'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("role IN ('primary', 'supplement')"),
    )
    
    # Relationships
    corpus = relationship("Corpus", back_populates="documents")
    nodes = relationship("Node", back_populates="document", cascade="all, delete-orphan")
    edges = relationship("Edge", back_populates="document", cascade="all, delete-orphan")


class Node(Base):
    """An evidence unit: section, paragraph, box, table, chart, image"""
    __tablename__ = "nodes"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    node_type = Column(String(50), nullable=False)  # 'section', 'paragraph', 'box', 'table', 'chart', 'image'
    label = Column(String(255))  # e.g., "Box I.2", "Table I.2a", "Chart I.21"
    title = Column(String(255))
    text = Column(Text)
    page_start = Column(Integer)
    page_end = Column(Integer)
    node_metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="nodes")
    edges_src = relationship("Edge", foreign_keys="Edge.src_node_id", back_populates="src_node")
    edges_dst = relationship("Edge", foreign_keys="Edge.dst_node_id", back_populates="dst_node")


class Edge(Base):
    """Relationship between nodes: contains, refers_to, supports"""
    __tablename__ = "edges"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    src_node_id = Column(PG_UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    rel_type = Column(String(20), nullable=False)  # ONLY: 'contains', 'refers_to', 'supports'
    dst_node_id = Column(PG_UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    confidence = Column(Float, default=1.0)
    evidence = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("rel_type IN ('contains', 'refers_to', 'supports')"),
    )
    
    # Relationships
    document = relationship("Document", back_populates="edges")
    src_node = relationship("Node", foreign_keys=[src_node_id], back_populates="edges_src")
    dst_node = relationship("Node", foreign_keys=[dst_node_id], back_populates="edges_dst")


class DataFile(Base):
    """An XLSX workbook"""
    __tablename__ = "data_files"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corpus_id = Column(PG_UUID(as_uuid=True), ForeignKey("corpora.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sheets = relationship("DataSheet", back_populates="file", cascade="all, delete-orphan")
    tables = relationship("DataTable", back_populates="file", cascade="all, delete-orphan")


class DataSheet(Base):
    """A sheet within an XLSX workbook"""
    __tablename__ = "data_sheets"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(PG_UUID(as_uuid=True), ForeignKey("data_files.id", ondelete="CASCADE"), nullable=False)
    sheet_name = Column(String(255), nullable=False)
    sheet_index = Column(Integer, nullable=False)
    sheet_metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    file = relationship("DataFile", back_populates="sheets")
    tables = relationship("DataTable", back_populates="sheet", cascade="all, delete-orphan")


class DataTable(Base):
    """An extracted table from a sheet (with panel splitting)"""
    __tablename__ = "data_tables"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(PG_UUID(as_uuid=True), ForeignKey("data_files.id", ondelete="CASCADE"), nullable=False)
    sheet_id = Column(PG_UUID(as_uuid=True), ForeignKey("data_sheets.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255))
    table_name = Column(String(255), nullable=False)
    range_a1 = Column(String(50))  # e.g., "A1:F100"
    header_rows = Column(Integer, default=1)
    index_cols = Column(Integer, default=1)
    units = Column(String(255))
    notes = Column(Text)
    table_json = Column(JSONB)  # Full table structure
    table_long = Column(JSONB)  # Long-format: [{time, geo, indicator, measure, value, unit, provenance}, ...]
    tags = Column(ARRAY(String))
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    file = relationship("DataFile", back_populates="tables")
    sheet = relationship("DataSheet", back_populates="tables")


class Indicator(Base):
    """A named metric (e.g., "GDP Growth", "Inflation Rate")"""
    __tablename__ = "indicators"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corpus_id = Column(PG_UUID(as_uuid=True), ForeignKey("corpora.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    aliases = Column(ARRAY(String))
    topic = Column(String(100))  # e.g., "Growth & Demand"
    unit = Column(String(50))  # e.g., "%", "Crores INR"
    freq = Column(String(20))  # e.g., "annual", "quarterly"
    geo_level = Column(String(50))  # e.g., "national", "state"
    definition = Column(Text)
    provenance = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    series = relationship("IndicatorSeries", back_populates="indicator", cascade="all, delete-orphan")


class IndicatorSeries(Base):
    """Time series for an indicator with derived metrics"""
    __tablename__ = "indicator_series"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    indicator_id = Column(PG_UUID(as_uuid=True), ForeignKey("indicators.id", ondelete="CASCADE"), nullable=False)
    geo_key = Column(String(100))  # e.g., "IND", "MH"
    time_start = Column(String(20))
    time_end = Column(String(20))
    points = Column(JSONB)  # [{time, value}, ...]
    derived_views = Column(JSONB)  # {yoy: [...], cagr_3y: [...], cagr_5y: [...], ranks: [...]}
    provenance = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    indicator = relationship("Indicator", back_populates="series")


class TopicBrief(Base):
    """3-5 minute summary per topic"""
    __tablename__ = "topic_briefs"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corpus_id = Column(PG_UUID(as_uuid=True), ForeignKey("corpora.id", ondelete="CASCADE"), nullable=False)
    topic = Column(String(255), nullable=False)  # e.g., "Growth & Demand"
    bullets = Column(JSONB, nullable=False, default=list)  # 5-8 bullet points as JSONB array
    key_numbers = Column(JSONB, nullable=False, default=list)  # [{value, unit, label, citation}, ...]
    linked_node_ids = Column(JSONB, default=list)  # Array of UUID strings as JSONB
    linked_series_ids = Column(JSONB, default=list)  # Array of UUID strings as JSONB
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    corpus = relationship("Corpus", back_populates="topic_briefs")


class ClaimCard(Base):
    """Practitioner-quality claim with evidence"""
    __tablename__ = "claim_cards"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corpus_id = Column(PG_UUID(as_uuid=True), ForeignKey("corpora.id", ondelete="CASCADE"), nullable=False)
    topic = Column(String(255), nullable=False)
    claim_text = Column(Text, nullable=False)  # One-sentence claim
    explanation = Column(Text)  # Practitioner tone
    evidence_node_ids = Column(JSONB, default=list)  # Array of UUID strings as JSONB
    evidence_series_ids = Column(JSONB, default=list)  # Array of UUID strings as JSONB
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1"),
    )
    
    # Relationships
    corpus = relationship("Corpus", back_populates="claim_cards")


class SearchIndex(Base):
    """Full-text search index"""
    __tablename__ = "search_index"
    
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    node_id = Column(PG_UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    raw_text = Column(Text, nullable=False)
    tsv = Column(TSVECTOR)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Embedding(Base):
    """Vector representation for semantic search"""
    __tablename__ = "embeddings"
    
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    node_id = Column(PG_UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    embedded_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # OpenAI text-embedding-3-large
    model_id = Column(String(50))  # e.g., "text-embedding-3-large"
    source_hash = Column(String(64))  # SHA256 of embedded_text
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatSession(Base):
    """Legacy Phase 1: Pseudonymous chat session tracking"""
    __tablename__ = "legacy_chat_sessions"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_pseudo_id = Column(String(64), nullable=False)  # SHA256(google_sub + SERVER_SALT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversations = relationship("Conversation", back_populates="chat_session", cascade="all, delete-orphan")


class Conversation(Base):
    """Chat session linked to authenticated user"""
    __tablename__ = "conversations"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corpus_id = Column(PG_UUID(as_uuid=True), ForeignKey("corpora.id", ondelete="CASCADE"), nullable=False)
    chat_session_id = Column(PG_UUID(as_uuid=True), ForeignKey("legacy_chat_sessions.id", ondelete="SET NULL"))
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # PHASE 2: Link to authenticated user
    user_pseudo_id = Column(String(64), nullable=False)
    session_metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chat_session = relationship("ChatSession", back_populates="conversations")
    user = relationship("User", back_populates="conversations")  # PHASE 2: User relationship
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    retrieval_events = relationship("RetrievalEvent", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Chat message"""
    __tablename__ = "messages"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    message_metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')"),
    )
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    labels = relationship("MessageLabel", back_populates="message", uselist=False, cascade="all, delete-orphan")


class RetrievalEvent(Base):
    """What evidence was retrieved for each message"""
    __tablename__ = "retrieval_events"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # PHASE 2: Link to user for analytics
    retrieved_node_ids = Column(ARRAY(PG_UUID(as_uuid=True)))
    retrieved_series_ids = Column(ARRAY(PG_UUID(as_uuid=True)))
    used_evidence = Column(JSONB)  # Final citations in response
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="retrieval_events")
    user = relationship("User", back_populates="retrieval_events")  # PHASE 2: User relationship


class MessageLabel(Base):
    """Offline classification of message"""
    __tablename__ = "message_labels"
    
    message_id = Column(PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True)
    topics = Column(ARRAY(String))
    entities = Column(ARRAY(String))
    intent = Column(String(50))  # 'question', 'clarification', 'challenge', 'request', 'feedback'
    sentiment = Column(String(20))  # 'optimistic', 'neutral', 'pessimistic', 'mixed'
    concerns = Column(ARRAY(String))
    confidence = Column(Float)
    label_version = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    message = relationship("Message", back_populates="labels")


class TopicCluster(Base):
    """Weekly clustering of user questions"""
    __tablename__ = "topic_clusters"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corpus_id = Column(PG_UUID(as_uuid=True), ForeignKey("corpora.id", ondelete="CASCADE"), nullable=False)
    cluster_id = Column(Integer)
    date_range = Column(String(50))  # e.g., "2026-01-27 to 2026-02-02"
    topic = Column(String(255))
    summary = Column(Text)
    example_message_ids = Column(ARRAY(PG_UUID(as_uuid=True)))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DailyInsight(Base):
    """Aggregated daily metrics"""
    __tablename__ = "daily_insights"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corpus_id = Column(PG_UUID(as_uuid=True), ForeignKey("corpora.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    total_questions = Column(Integer, default=0)
    top_topics = Column(ARRAY(String))
    top_concerns = Column(ARRAY(String))
    sentiment_mix = Column(JSONB)  # {optimistic: int, neutral: int, pessimistic: int, mixed: int}
    notable_questions = Column(ARRAY(Text))
    coverage_gaps = Column(ARRAY(String))  # Questions with low evidence
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IngestionRun(Base):
    """Track ingestion runs for idempotency"""
    __tablename__ = "ingestion_runs"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corpus_id = Column(PG_UUID(as_uuid=True), ForeignKey("corpora.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(50))  # 'pdf_ingest', 'xlsx_ingest', 'indicators', 'summaries'
    status = Column(String(20))  # 'started', 'completed', 'failed'
    error_message = Column(Text)
    items_processed = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================================
# PHASE 5: Insights & Summaries Models
# ============================================================================

class Insight(Base):
    """Extracted insights from data tables"""
    __tablename__ = "insights"
    
    id = Column(Integer, primary_key=True)
    data_table_id = Column(Integer, ForeignKey("data_tables.id", ondelete="CASCADE"), nullable=False, index=True)
    # user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # Not in DB schema
    
    insight_type = Column(String(50), nullable=False, index=True)  # 'statistic', 'pattern', 'anomaly', 'trend'
    metric = Column(String(255), nullable=False, index=True)  # Column name
    value = Column(Text)  # Insight value
    confidence = Column(Float)  # 0-1 confidence score
    description = Column(Text)  # Human-readable description
    supporting_data = Column(JSONB)  # Additional context
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    data_table = relationship("DataTable", backref="insights")
    # user = relationship("User", backref="insights")  # No FK in schema
    embeddings = relationship("InsightEmbedding", back_populates="insight", cascade="all, delete-orphan")


class Summary(Base):
    """Generated summaries from insights"""
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True)
    data_table_id = Column(Integer, ForeignKey("data_tables.id", ondelete="CASCADE"), nullable=False, index=True)
    # user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # Not in DB schema
    
    summary_type = Column(String(50), nullable=False, index=True)  # 'executive', 'detailed', 'statistical'
    content = Column(Text, nullable=False)  # Markdown-formatted summary
    key_points = Column(ARRAY(String))  # Array of bullet points
    summary_metadata = Column(JSONB)  # Generation metadata
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    data_table = relationship("DataTable", backref="summaries")
    # user = relationship("User", backref="summaries")  # No FK in schema


class InsightEmbedding(Base):
    """Vector embeddings for semantic search"""
    __tablename__ = "insight_embeddings"
    
    id = Column(Integer, primary_key=True)
    insight_id = Column(Integer, ForeignKey("insights.id", ondelete="CASCADE"), nullable=False, index=True)
    
    embedding = Column(ARRAY(Float))  # Array of float values (TF-IDF or other)
    embedding_model = Column(String(100))  # 'tfidf', 'sentence-transformers', etc
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    insight = relationship("Insight", back_populates="embeddings")
