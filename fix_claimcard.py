#!/usr/bin/env python3
"""Fix remaining indentation errors in models/__init__.py"""

filepath = r'c:\Users\Dell 5330\OneDrive\Documents\ECOSURVEYCHat\backend\app\models\__init__.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the entire ClaimCard class definition to fix all issues at once
old_claim_card = '''class ClaimCard(Base):
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
        updated_at = Column(DateTime(timezone=True), server_default=func.now())
    
        __table_args__ = (
            CheckConstraint("confidence >= 0 AND confidence <= 1"),
        )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    corpus = relationship("Corpus", back_populates="claim_cards")'''

new_claim_card = '''class ClaimCard(Base):
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
    corpus = relationship("Corpus", back_populates="claim_cards")'''

content = content.replace(old_claim_card, new_claim_card)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed ClaimCard class indentation")
