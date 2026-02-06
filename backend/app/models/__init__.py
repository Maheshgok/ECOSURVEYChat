"""
Simplified SQLAlchemy models for Economic Survey RAG Chat
5 core tables: users, corpuses, documents, chunks, messages
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid

from app.core.database import Base


class User(Base):
    """User account created via OAuth (Firebase, Azure AD, etc.)"""
    __tablename__ = "users"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    picture = Column(String(500))
    email_verified = Column(Integer, default=0)  # SQLite compat: 0=False, 1=True
    first_login = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")


class Corpus(Base):
    """A collection of documents (Economic Survey + supplements)"""
    __tablename__ = "corpuses"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    documents = relationship("Document", back_populates="corpus", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="corpus", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="corpus", cascade="all, delete-orphan")


class Document(Base):
    """A PDF or XLSX file"""
    __tablename__ = "documents"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corpus_id = Column(PG_UUID(as_uuid=True), ForeignKey("corpuses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    filename = Column(String(255))
    year = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    corpus = relationship("Corpus", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    """Text chunk with embedding for RAG retrieval"""
    __tablename__ = "chunks"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    corpus_id = Column(PG_UUID(as_uuid=True), ForeignKey("corpuses.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    page_start = Column(Integer)
    page_end = Column(Integer)
    chunk_index = Column(Integer)
    embedding = Column(Vector(3072))  # OpenAI text-embedding-3-large
    meta = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    corpus = relationship("Corpus", back_populates="chunks")


class Message(Base):
    """Chat message (user query or assistant response)"""
    __tablename__ = "messages"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    corpus_id = Column(PG_UUID(as_uuid=True), ForeignKey("corpuses.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    meta = Column(JSONB, default={})  # Store citations, conversation_id, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')"),
    )
    
    # Relationships
    user = relationship("User", back_populates="messages")
    corpus = relationship("Corpus", back_populates="messages")


# Backwards compatibility alias (for existing code that references Node)
Node = Chunk
