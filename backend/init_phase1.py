#!/usr/bin/env python3
"""
Phase 1 Database Initialization Script
Tests database connectivity and creates tables
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("=" * 60)
    print("Phase 1 Database Initialization")
    print("=" * 60)
    
    # Step 1: Test imports
    print("\n[1/4] Testing imports...")
    try:
        from app.core.database import engine, SessionLocal, Base
        from app.models import (
            Corpus, Document, Node, Edge,
            DataFile, DataSheet, DataTable, Indicator, IndicatorSeries,
            TopicBrief, ClaimCard, SearchIndex, Embedding,
            Session, Conversation, Message, RetrievalEvent, MessageLabel,
            TopicCluster, DailyInsight, IngestionRun
        )
        print("   ✓ All imports successful")
    except Exception as e:
        print(f"   ✗ Import failed: {e}")
        return False
    
    # Step 2: Test database connection
    print("\n[2/4] Testing database connection...")
    try:
        with engine.connect() as connection:
            result = connection.execute("SELECT 1 AS test")
            result.fetchone()
        print("   ✓ Database connection successful")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        print("   ! Make sure PostgreSQL is running and DATABASE_URL is correct")
        return False
    
    # Step 3: Create tables
    print("\n[3/4] Creating tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("   ✓ All tables created")
    except Exception as e:
        print(f"   ✗ Table creation failed: {e}")
        return False
    
    # Step 4: Verify tables
    print("\n[4/4] Verifying tables...")
    try:
        session = SessionLocal()
        models = [
            Corpus, Document, Node, Edge,
            DataFile, DataSheet, DataTable, Indicator, IndicatorSeries,
            TopicBrief, ClaimCard, SearchIndex, Embedding,
            Session, Conversation, Message, RetrievalEvent, MessageLabel,
            TopicCluster, DailyInsight, IngestionRun
        ]
        
        model_count = len(models)
        print(f"   ✓ {model_count} models available")
        
        # Try a simple query
        corpus_count = session.query(Corpus).count()
        print(f"   ✓ Database query works: {corpus_count} corpora exist")
        
        session.close()
    except Exception as e:
        print(f"   ✗ Verification failed: {e}")
        return False
    
    # Success
    print("\n" + "=" * 60)
    print("✓ Phase 1 Initialization Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Start FastAPI: python -m uvicorn app.main:app --reload")
    print("  2. Test health: curl http://localhost:8000/health")
    print("  3. View API docs: http://localhost:8000/docs")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
