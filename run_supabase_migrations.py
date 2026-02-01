#!/usr/bin/env python3
"""
Supabase Migration Helper
Run all database migrations on Supabase
"""

import os
import sys
import subprocess
from pathlib import Path

# Supabase credentials (you'll be prompted or use env vars)
def get_supabase_connection_string():
    """Get Supabase connection string from user or environment"""
    # Check if passed as argument
    if len(sys.argv) > 1:
        return sys.argv[1]
    
    # Check environment variable
    db_url = os.environ.get('SUPABASE_DB_URL')
    if db_url:
        return db_url
    
    # Prompt user
    print("Enter your Supabase PostgreSQL connection string:")
    print("(From: Supabase Dashboard → Settings → Database → Connection string → URI)")
    print()
    return input("Connection string: ").strip()

def run_migrations(connection_string, migrations_dir="backend/migrations"):
    """Run all migration files in order"""
    
    # Migration files in order
    migration_files = [
        "001_init_phase1.sql",
        "002_add_auth_tables.sql",
        "003_add_ingestion_tables.sql",
        "004_add_data_storage.sql",
        "005_add_insights.sql",
        "006_add_summaries.sql",
        "007_fix_conversations_schema.sql",
    ]
    
    # Check if migrations directory exists
    if not os.path.isdir(migrations_dir):
        print(f"❌ Migrations directory not found: {migrations_dir}")
        return False
    
    print(f"📦 Running {len(migration_files)} migrations on Supabase...\n")
    
    for i, migration_file in enumerate(migration_files, 1):
        file_path = os.path.join(migrations_dir, migration_file)
        
        if not os.path.exists(file_path):
            print(f"⚠️  Migration {i}/{len(migration_files)}: {migration_file} - FILE NOT FOUND")
            continue
        
        print(f"📄 Migration {i}/{len(migration_files)}: {migration_file}")
        
        try:
            # Run psql command
            result = subprocess.run(
                ["psql", connection_string, "-f", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"   ✅ Success\n")
            else:
                print(f"   ⚠️  Warning/Info:\n   {result.stderr}\n")
        
        except FileNotFoundError:
            print(f"   ❌ ERROR: psql command not found")
            print(f"   Install PostgreSQL client tools to continue")
            return False
        except subprocess.TimeoutExpired:
            print(f"   ❌ ERROR: Migration timed out")
            return False
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            return False
    
    # Enable pgvector extension
    print("🔧 Enabling pgvector extension...")
    try:
        result = subprocess.run(
            ["psql", connection_string, "-c", "CREATE EXTENSION IF NOT EXISTS vector;"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("   ✅ pgvector enabled\n")
        else:
            print(f"   ⚠️  {result.stderr}\n")
    except Exception as e:
        print(f"   ⚠️  Could not enable pgvector: {e}\n")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("SUPABASE MIGRATION HELPER")
    print("=" * 60)
    print()
    
    # Get connection string
    conn_string = get_supabase_connection_string()
    
    if not conn_string:
        print("❌ No connection string provided")
        sys.exit(1)
    
    print()
    
    # Run migrations
    if run_migrations(conn_string):
        print("=" * 60)
        print("✅ ALL MIGRATIONS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Update backend/.env.prod with Supabase connection string")
        print("2. Build and deploy to Cloud Run")
        print("3. Update frontend API URL in React app")
        sys.exit(0)
    else:
        print("=" * 60)
        print("❌ MIGRATION FAILED")
        print("=" * 60)
        sys.exit(1)
