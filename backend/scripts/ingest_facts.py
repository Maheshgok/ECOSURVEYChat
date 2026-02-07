"""
Fact-based ingestion pipeline
Extracts structured facts from documents and stores in Pinecone
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict
import fitz  # PyMuPDF
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.fact_extractor import FactExtractor
from app.models.fact import RAGIngressFact

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FactIngestionPipeline:
    """Pipeline for extracting facts from documents and storing in Pinecone"""
    
    def __init__(
        self,
        pinecone_api_key: str,
        openai_api_key: str,
        index_name: str = "ecosurvey-facts",
        create_index: bool = False
    ):
        self.extractor = FactExtractor(api_key=openai_api_key)
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index_name = index_name
        
        # Create index if needed
        if create_index:
            self._create_index()
        
        # Connect to index
        self.index = self.pc.Index(index_name)
        logger.info(f"Connected to Pinecone index: {index_name}")
    
    def _create_index(self):
        """Create Pinecone index for facts if it doesn't exist"""
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]
        
        if self.index_name in existing_indexes:
            logger.info(f"Index {self.index_name} already exists")
            return
        
        logger.info(f"Creating new Pinecone index: {self.index_name}")
        self.pc.create_index(
            name=self.index_name,
            dimension=3072,  # text-embedding-3-large
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
        
        # Wait for index to be ready
        while not self.pc.describe_index(self.index_name).status['ready']:
            logger.info("Waiting for index to be ready...")
            time.sleep(5)
        
        logger.info(f"Index {self.index_name} created successfully")
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Extract text chunks from PDF with page numbers"""
        logger.info(f"Extracting text from: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        chunks = []
        
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            
            # Skip empty pages
            if not text.strip():
                continue
            
            # Split long pages into chunks (max 2000 chars per chunk)
            page_chunks = self._split_text(text, max_length=2000)
            
            for idx, chunk_text in enumerate(page_chunks):
                chunks.append({
                    'text': chunk_text,
                    'page': page_num,
                    'chunk_index': idx,
                    'document_id': os.path.basename(pdf_path)
                })
        
        doc.close()
        logger.info(f"Extracted {len(chunks)} chunks from {len(doc)} pages")
        return chunks
    
    def _split_text(self, text: str, max_length: int = 2000) -> List[str]:
        """Split text into chunks preserving sentence boundaries"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by sentences (approximate)
        sentences = text.replace('\n', ' ').split('. ')
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= max_length:
                current_chunk += sentence + '. '
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + '. '
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def ingest_document(
        self,
        pdf_path: str,
        source_origin: str,
        batch_size: int = 10
    ) -> Dict:
        """
        Ingest a PDF document as structured facts
        
        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Starting fact ingestion for: {pdf_path}")
        start_time = time.time()
        
        # Extract chunks
        chunks = self.extract_text_from_pdf(pdf_path)
        
        # Extract facts from chunks
        logger.info(f"Extracting facts from {len(chunks)} chunks...")
        all_facts = self.extractor.batch_extract(
            chunks=chunks,
            source_origin=source_origin
        )
        
        logger.info(f"Extracted {len(all_facts)} facts")
        
        # Generate embeddings and prepare for upsert
        vectors = []
        for fact in all_facts:
            # Create fact text for embedding
            fact_text = self._fact_to_text(fact)
            
            # Generate embedding
            embedding = self.extractor.client.embeddings.create(
                input=fact_text,
                model="text-embedding-3-large"
            ).data[0].embedding
            
            # Prepare metadata (Pinecone has size limits)
            metadata = {
                'subject': fact.subject,
                'predicate': fact.predicate,
                'value_quantity': fact.value_quantity,
                'value_unit': fact.value_unit or '',
                'temporal_context': fact.temporal_context or '',
                'certainty_score': fact.certainty_score,
                'sentiment_magnitude': fact.sentiment_magnitude,
                'source_origin': fact.source_origin,
                'page_reference': fact.page_reference,
                'entities': fact.related_entities[:10],  # Limit to 10
                'verbatim': fact.verbatim_extraction[:500],  # Truncate
                'parent_context_id': fact.parent_context_id or ''
            }
            
            vectors.append({
                'id': fact.fact_id,
                'values': embedding,
                'metadata': metadata
            })
        
        # Batch upsert to Pinecone
        logger.info(f"Upserting {len(vectors)} vectors to Pinecone...")
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch)
            logger.info(f"Upserted batch {i // batch_size + 1}/{(len(vectors) + batch_size - 1) // batch_size}")
        
        elapsed_time = time.time() - start_time
        
        stats = {
            'document': pdf_path,
            'chunks_processed': len(chunks),
            'facts_extracted': len(all_facts),
            'facts_per_chunk': len(all_facts) / len(chunks) if chunks else 0,
            'elapsed_time': elapsed_time,
            'facts_per_second': len(all_facts) / elapsed_time if elapsed_time > 0 else 0
        }
        
        logger.info(f"Ingestion complete: {stats}")
        return stats
    
    def _fact_to_text(self, fact: RAGIngressFact) -> str:
        """Convert fact to text for embedding"""
        parts = [
            f"Subject: {fact.subject}",
            f"Relation: {fact.predicate}"
        ]
        
        if fact.value_quantity is not None:
            parts.append(f"Value: {fact.value_quantity}")
        
        if fact.value_unit:
            parts.append(f"Unit: {fact.value_unit}")
        
        if fact.temporal_context:
            parts.append(f"Time: {fact.temporal_context}")
        
        if fact.related_entities:
            parts.append(f"Entities: {', '.join(fact.related_entities[:3])}")
        
        return " | ".join(parts)
    
    def get_index_stats(self) -> Dict:
        """Get statistics about the fact index"""
        stats = self.index.describe_index_stats()
        return {
            'total_facts': stats.get('total_vector_count', 0),
            'index_fullness': stats.get('index_fullness', 0.0),
            'dimensions': stats.get('dimension', 0),
            'namespaces': stats.get('namespaces', {})
        }


def main():
    """CLI for fact ingestion"""
    parser = argparse.ArgumentParser(description='Ingest documents as structured facts')
    parser.add_argument('pdf_path', help='Path to PDF document')
    parser.add_argument('--source', default='Economic_Survey', help='Source origin identifier')
    parser.add_argument('--index-name', default='ecosurvey-facts', help='Pinecone index name')
    parser.add_argument('--create-index', action='store_true', help='Create index if not exists')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for upserts')
    
    args = parser.parse_args()
    
    # Get API keys from environment
    pinecone_api_key = os.getenv('PINECONE_API_KEY')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not pinecone_api_key:
        logger.error("PINECONE_API_KEY not found in environment")
        sys.exit(1)
    
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found in environment")
        sys.exit(1)
    
    # Verify PDF exists
    if not os.path.exists(args.pdf_path):
        logger.error(f"PDF not found: {args.pdf_path}")
        sys.exit(1)
    
    # Run ingestion
    pipeline = FactIngestionPipeline(
        pinecone_api_key=pinecone_api_key,
        openai_api_key=openai_api_key,
        index_name=args.index_name,
        create_index=args.create_index
    )
    
    stats = pipeline.ingest_document(
        pdf_path=args.pdf_path,
        source_origin=args.source,
        batch_size=args.batch_size
    )
    
    logger.info("=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info(f"Document: {stats['document']}")
    logger.info(f"Chunks processed: {stats['chunks_processed']}")
    logger.info(f"Facts extracted: {stats['facts_extracted']}")
    logger.info(f"Facts per chunk: {stats['facts_per_chunk']:.2f}")
    logger.info(f"Elapsed time: {stats['elapsed_time']:.1f}s")
    logger.info(f"Throughput: {stats['facts_per_second']:.2f} facts/s")
    logger.info("=" * 60)
    
    # Show index stats
    index_stats = pipeline.get_index_stats()
    logger.info(f"Total facts in index: {index_stats['total_facts']}")
    logger.info(f"Index fullness: {index_stats['index_fullness']:.2%}")


if __name__ == "__main__":
    main()
