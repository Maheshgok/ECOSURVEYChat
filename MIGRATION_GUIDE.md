# Migration Complete: Supabase → Firestore + Pinecone

## ✅ What's Been Updated

### 1. New Database Modules
- **`backend/app/core/firestore.py`** - Firestore client for metadata storage
- **`backend/app/core/pinecone_db.py`** - Pinecone client for vector storage

### 2. Updated Ingestion Scripts
- **`backend/scripts/ingest_pdf.py`** - Now uses Firestore + Pinecone
- **`backend/scripts/ingest_xlsx.py`** - Now uses Firestore + Pinecone  
- **`backend/scripts/batch_ingest.py`** - Updated for new architecture

### 3. Updated Dependencies
- **`backend/requirements.txt`** - Added:
  - `pinecone-client==3.0.0`
  - `firebase-admin==6.4.0`
  - `openai==1.12.0`
  - Removed: SQLAlchemy, psycopg2, pgvector

## 🔧 Environment Variables Needed

Add these to your `backend/.env` file:

```env
# OpenAI (already set)
OPENAI_API_KEY=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

# Firebase (already set)
FIREBASE_PROJECT_ID=watch-mail-trial

# Pinecone (NEW - get these after creating index)
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_INDEX_NAME=economic-survey-2026

# Optional: Service account for Firestore
# FIREBASE_SERVICE_ACCOUNT_PATH=/path/to/service-account.json
```

## 📋 Next Steps

### 1. Install New Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Get Pinecone Credentials
After creating your Pinecone index:
1. Go to **API Keys** in Pinecone dashboard
2. Copy your API key
3. Add to `.env` file

### 3. Firebase Service Account (Optional but Recommended)
For production, download service account JSON:
1. Go to Firebase Console → Project Settings → Service Accounts
2. Click "Generate New Private Key"
3. Download JSON file
4. Set path in `.env`: `FIREBASE_SERVICE_ACCOUNT_PATH=/path/to/file.json`

### 4. Test Single File Ingestion
```bash
cd backend
python scripts/ingest_pdf.py "../Content/Report/echapter.pdf" --title "Economic Survey 2025-26"
```

### 5. Run Full Ingestion
```bash
cd backend
python scripts/ingest_all.py
```

## 🏗️ Architecture

**Before (Supabase):**
```
Supabase PostgreSQL
├── Tables (users, corpuses, documents, chunks, messages)
└── pgvector extension (embeddings)
```

**After (Firestore + Pinecone):**
```
Firestore                          Pinecone
├── users                          └── Vectors (embeddings only)
├── corpuses                           └── metadata (corpus_id, document_id, pages)
├── documents
├── chunks (text + pinecone_id)
└── messages
```

## 🔄 Data Flow

### Ingestion:
1. Extract text from PDF/XLSX
2. Chunk text (800 words, 100 overlap for PDFs)
3. Generate OpenAI embeddings (3072 dims)
4. **Upsert vectors to Pinecone** (id, embedding, metadata)
5. **Store chunk metadata in Firestore** (text, pinecone_id, pages)

### Chat Query:
1. User asks question
2. Generate query embedding
3. **Search Pinecone** for similar vectors → get pinecone_ids
4. **Fetch chunks from Firestore** using pinecone_ids → get text
5. Build context with chunk texts
6. Generate answer with OpenAI
7. Return answer + citations

## ✨ Benefits

1. **No Network Issues** - Both services are cloud-native
2. **Simpler Setup** - Firestore uses same Firebase project  
3. **Better Performance** - Pinecone is optimized for vector search
4. **Free Tier** - 100K vectors in Pinecone, 50K reads/day in Firestore
5. **Scalable** - Both auto-scale for production

## 🚨 Important Notes

- **Pinecone Free Tier**: Only 1 index allowed
- **Dimensions**: Cannot change 3072 after index creation
- **Firestore Batching**: Queries limited to 10 IDs per batch (handled in code)
- **No Migration Tool**: Old Supabase data is abandoned (no data was ingested anyway)
