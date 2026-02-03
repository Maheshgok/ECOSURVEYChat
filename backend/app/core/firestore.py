"""
Firestore configuration for metadata storage
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional
from datetime import datetime

# Global Firestore client
_db: Optional[firestore.Client] = None


def init_firestore():
    """Initialize Firestore with Firebase Admin SDK"""
    global _db
    
    if _db is not None:
        return _db
    
    # Check if already initialized
    if not firebase_admin._apps:
        # Use service account JSON file if available
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        
        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        else:
            # Use project ID from environment (works with default credentials)
            project_id = os.getenv("FIREBASE_PROJECT_ID")
            if not project_id:
                raise ValueError("FIREBASE_PROJECT_ID not set in environment. Please download service account JSON from Firebase Console.")
            
            # Try to initialize without credentials (will use GOOGLE_APPLICATION_CREDENTIALS env var if set)
            try:
                firebase_admin.initialize_app(options={
                    'projectId': project_id,
                })
            except Exception as e:
                raise ValueError(
                    f"Failed to initialize Firebase. Please either:\n"
                    f"1. Download service account JSON from Firebase Console and set FIREBASE_SERVICE_ACCOUNT_PATH\n"
                    f"2. Or set GOOGLE_APPLICATION_CREDENTIALS to point to your service account JSON\n"
                    f"Error: {e}"
                )
    
    _db = firestore.client()
    return _db


def get_firestore() -> firestore.Client:
    """Get Firestore client (dependency for FastAPI routes)"""
    if _db is None:
        return init_firestore()
    return _db


class FirestoreCollections:
    """Collection names"""
    USERS = "users"
    CORPUSES = "corpuses"
    DOCUMENTS = "documents"
    CHUNKS = "chunks"
    MESSAGES = "messages"


def create_user(google_id: str, email: str, name: str = None, picture: str = None) -> dict:
    """Create or update user in Firestore"""
    db = get_firestore()
    user_ref = db.collection(FirestoreCollections.USERS).document(google_id)
    
    user_data = {
        "googleId": google_id,
        "email": email,
        "name": name,
        "picture": picture,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "lastLogin": firestore.SERVER_TIMESTAMP,
    }
    
    user_ref.set(user_data, merge=True)
    return {"id": google_id, **user_data}


def get_user_by_google_id(google_id: str) -> Optional[dict]:
    """Get user by Google ID"""
    db = get_firestore()
    user_ref = db.collection(FirestoreCollections.USERS).document(google_id)
    user = user_ref.get()
    
    if user.exists:
        return {"id": user.id, **user.to_dict()}
    return None


def create_corpus(name: str, description: str = None, year: int = None) -> dict:
    """Create a corpus in Firestore"""
    db = get_firestore()
    corpus_ref = db.collection(FirestoreCollections.CORPUSES).document()
    
    corpus_data = {
        "name": name,
        "description": description,
        "year": year,
        "createdAt": firestore.SERVER_TIMESTAMP,
    }
    
    corpus_ref.set(corpus_data)
    return {"id": corpus_ref.id, **corpus_data}


def get_corpus_by_name(name: str) -> Optional[dict]:
    """Get corpus by name"""
    db = get_firestore()
    corpuses = db.collection(FirestoreCollections.CORPUSES).where("name", "==", name).limit(1).stream()
    
    for corpus in corpuses:
        return {"id": corpus.id, **corpus.to_dict()}
    return None


def get_all_corpuses() -> list[dict]:
    """Get all corpuses"""
    db = get_firestore()
    corpuses = db.collection(FirestoreCollections.CORPUSES).stream()
    return [{"id": c.id, **c.to_dict()} for c in corpuses]


def create_document(corpus_id: str, title: str, filename: str = None, year: int = None, page_count: int = None) -> dict:
    """Create a document in Firestore"""
    db = get_firestore()
    doc_ref = db.collection(FirestoreCollections.DOCUMENTS).document()
    
    doc_data = {
        "corpusId": corpus_id,
        "title": title,
        "filename": filename,
        "year": year,
        "pageCount": page_count,
        "createdAt": firestore.SERVER_TIMESTAMP,
    }
    
    doc_ref.set(doc_data)
    return {"id": doc_ref.id, **doc_data}


def create_chunk(
    document_id: str,
    corpus_id: str,
    text: str,
    pinecone_id: str,
    page_start: int = None,
    page_end: int = None,
    chunk_index: int = None,
    meta: dict = None
) -> dict:
    """Create a chunk in Firestore"""
    db = get_firestore()
    chunk_ref = db.collection(FirestoreCollections.CHUNKS).document()
    
    chunk_data = {
        "documentId": document_id,
        "corpusId": corpus_id,
        "text": text,
        "pineconeId": pinecone_id,
        "pageStart": page_start,
        "pageEnd": page_end,
        "chunkIndex": chunk_index,
        "meta": meta or {},
        "createdAt": firestore.SERVER_TIMESTAMP,
    }
    
    chunk_ref.set(chunk_data)
    return {"id": chunk_ref.id, **chunk_data}


def get_chunks_by_pinecone_ids(pinecone_ids: list[str]) -> dict[str, dict]:
    """Get chunks by their Pinecone IDs"""
    db = get_firestore()
    
    # Firestore 'in' operator supports max 10 items at a time
    chunks = {}
    for i in range(0, len(pinecone_ids), 10):
        batch = pinecone_ids[i:i+10]
        results = db.collection(FirestoreCollections.CHUNKS).where("pineconeId", "in", batch).stream()
        
        for chunk in results:
            chunk_data = chunk.to_dict()
            chunks[chunk_data["pineconeId"]] = {"id": chunk.id, **chunk_data}
    
    return chunks


def create_message(user_id: str, corpus_id: str, role: str, content: str, meta: dict = None) -> dict:
    """Create a message in Firestore"""
    db = get_firestore()
    msg_ref = db.collection(FirestoreCollections.MESSAGES).document()
    
    msg_data = {
        "userId": user_id,
        "corpusId": corpus_id,
        "role": role,
        "content": content,
        "meta": meta or {},
        "createdAt": firestore.SERVER_TIMESTAMP,
    }
    
    msg_ref.set(msg_data)
    return {"id": msg_ref.id, **msg_data}


def get_user_messages(user_id: str, limit: int = 50) -> list[dict]:
    """Get recent messages for a user"""
    db = get_firestore()
    messages = (
        db.collection(FirestoreCollections.MESSAGES)
        .where("userId", "==", user_id)
        .order_by("createdAt", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    
    return [{"id": m.id, **m.to_dict()} for m in messages]
