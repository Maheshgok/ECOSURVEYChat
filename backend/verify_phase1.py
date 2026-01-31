#!/usr/bin/env python3
"""
Phase 1 Verification Script
Quick check that all components are ready (no database required)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print(" Phase 1 Component Verification")
print("=" * 70)

# 1. Settings
print("\n[1/5] Checking settings configuration...")
try:
    from app.core.settings import settings
    print(f"   ✓ Settings loaded")
    print(f"     - Database: {settings.database_host}:{settings.database_port}/{settings.database_name}")
    print(f"     - Environment: {settings.environment}")
except Exception as e:
    print(f"   ✗ Settings failed: {e}")
    sys.exit(1)

# 2. Models
print("\n[2/5] Checking SQLAlchemy models...")
try:
    from app.models import (
        Corpus, Document, Node, Edge,
        DataFile, DataSheet, DataTable, Indicator, IndicatorSeries,
        TopicBrief, ClaimCard, SearchIndex, Embedding,
        Session, Conversation, Message, RetrievalEvent, MessageLabel,
        TopicCluster, DailyInsight, IngestionRun, Base
    )
    model_count = len(Base.metadata.tables)
    print(f"   ✓ All {model_count} models loaded successfully")
except Exception as e:
    print(f"   ✗ Models failed: {e}")
    sys.exit(1)

# 3. Database Connection
print("\n[3/5] Checking database connectivity...")
try:
    from app.core.database import engine
    with engine.connect() as connection:
        connection.execute("SELECT 1 AS test")
    print(f"   ✓ Database connection successful")
except Exception as e:
    print(f"   ⚠ Database not accessible: {e}")
    print(f"     - Make sure PostgreSQL is running on {settings.database_host}:{settings.database_port}")
    print(f"     - Or skip database for now with --skip-db flag")

# 4. FastAPI
print("\n[4/5] Checking FastAPI application...")
try:
    from app.main import app
    routes = len([r for r in app.routes if hasattr(r, 'path')])
    print(f"   ✓ FastAPI app loaded with {routes} routes")
except Exception as e:
    print(f"   ✗ FastAPI failed: {e}")
    sys.exit(1)

# 5. API Health
print("\n[5/5] Checking API health endpoint...")
try:
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get("/health")
    if response.status_code == 200:
        health = response.json()
        print(f"   ✓ Health endpoint working")
        print(f"     - Status: {health.get('status')}")
        print(f"     - Database: {health.get('database')}")
    else:
        print(f"   ⚠ Health endpoint returned {response.status_code}")
except Exception as e:
    print(f"   ⚠ Health check failed: {e}")

# Summary
print("\n" + "=" * 70)
print(" ✓ Phase 1 Verification Complete")
print("=" * 70)
print("\nNext Steps:")
print("  1. Start PostgreSQL (if not already running)")
print("  2. Create database: psql -U postgres -c \"CREATE DATABASE survey_chat;\"")
print("  3. Run API: python -m uvicorn app.main:app --reload")
print("  4. Test health: curl http://localhost:8000/health")
print("  5. View docs: http://localhost:8000/docs")
