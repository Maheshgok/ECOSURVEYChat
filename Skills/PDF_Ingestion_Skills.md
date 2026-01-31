# PDF Ingestion Skills (Phase 5)

**Goal:** Extract structured nodes with references and cross-link to XLSX tables

---

## 📋 Prerequisites

- Phase 1 (Database) completed
- Phase 3 (XLSX ingestion) completed
- Economic Survey PDF files available
- PyMuPDF (fitz) library installed
- Understanding of document structure detection

---

## 🎯 Critical Requirements

**Must handle:**
1. Multi-chapter PDF ingestion
2. Hierarchical structure (Chapter → Section → Paragraph)
3. Object detection (Tables, Boxes, Charts by caption pattern)
4. Reference registry (Table I.2a, Box I.2, Chart I.21)
5. Cross-linking PDF ↔ XLSX
6. Edge creation with ONLY {contains, refers_to, supports}
7. Offline embedding generation
8. Document classification (primary vs supplement)

**STOP CONDITIONS:**
- "Chart I.x" or "Table I.x" must link PDF ↔ XLSX
- Edge types must be ONLY {contains, refers_to, supports}
- Embeddings generated at runtime (not offline)

---

## 🎯 Tasks Breakdown

### **Task 5.1: Node Types & Labels**

**Node types in spec:**
- `chapter` - Top-level chapter
- `section` - Section within chapter
- `paragraph` - Text paragraph
- `table` - Table object (caption + reference)
- `box` - Box/callout object
- `chart` - Chart/figure object

**Label format:**
```
Chapter I: Economic Review
Section I.1: Introduction
Box I.2: Policy Framework
Table I.1: GDP Growth
Chart I.21: Inflation Trends
```

**File: `app/models/node.py`**

Verify model includes:
```python
class Node(Base):
    __tablename__ = 'nodes'
    
    id = Column(Integer, primary_key=True)
    corpus_id = Column(Integer, ForeignKey('corpora.id'))
    document_id = Column(Integer, ForeignKey('documents.id'))
    node_type = Column(String)  # chapter, section, paragraph, table, box, chart
    node_label = Column(String)  # e.g., "Section I.1"
    title = Column(Text)
    snippet = Column(Text)  # First 300 chars
    full_text = Column(Text)
    position = Column(Integer)  # Sequential within document
    page_num = Column(Integer, nullable=True)
    metadata = Column(JSONB)
```

---

### **Task 5.2: Caption Pattern Detection**

**Patterns to detect:**

| Object Type | Patterns | Examples |
|-------------|----------|----------|
| Table | `Table <chapter>.<number><suffix>` | Table I.1, Table I.2a, Table II.3 |
| Box | `Box <chapter>.<number>` | Box I.2, Box III.1 |
| Chart | `Chart <chapter>.<number>` | Chart I.21, Chart II.5a |

**File: `ingestion/pdf_ingest.py`**

```python
import re
from typing import Optional, Tuple

def detect_object_caption(text: str) -> Optional[Tuple[str, str]]:
    """
    Detect if line is a caption for Table/Box/Chart.
    
    Returns: (object_type, reference_label) or None
    Examples:
    - "Table I.1: GDP Growth" → ("table", "Table I.1")
    - "Box I.2 Policy Framework" → ("box", "Box I.2")
    - "Chart I.21 - Inflation" → ("chart", "Chart I.21")
    """
    patterns = [
        (r'^Table\s+([IVX]+\.\d+[a-z]?)', 'table'),
        (r'^Box\s+([IVX]+\.\d+)', 'box'),
        (r'^Chart\s+([IVX]+\.\d+[a-z]?)', 'chart'),
        (r'^Figure\s+([IVX]+\.\d+[a-z]?)', 'chart'),  # Treat Figure as chart
    ]
    
    for pattern, obj_type in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            reference_label = f"{obj_type.capitalize()} {match.group(1)}"
            return (obj_type, reference_label)
    
    return None

def extract_object_title(text: str, reference_label: str) -> str:
    """
    Extract title after reference label.
    
    Input: "Table I.1: GDP Growth Rates"
    Output: "GDP Growth Rates"
    """
    # Remove reference label prefix
    text = re.sub(r'^(Table|Box|Chart|Figure)\s+[IVX]+\.\d+[a-z]?\s*[:–-]?\s*', '', text, flags=re.IGNORECASE)
    return text.strip()
```

---

### **Task 5.3: Document Structure Detection**

**File: `ingestion/pdf_ingest.py`**

```python
import fitz  # PyMuPDF

def extract_pdf_structure(pdf_path: str) -> List[dict]:
    """
    Extract hierarchical structure from PDF.
    
    Returns list of nodes with:
    - node_type
    - node_label
    - title
    - full_text
    - page_num
    - position (sequential)
    """
    doc = fitz.open(pdf_path)
    nodes = []
    position = 0
    current_chapter = None
    current_section = None
    
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect chapter headings (heuristic: all caps, short, starts with "CHAPTER")
            if detect_chapter_heading(line):
                current_chapter = line
                current_section = None
                
                nodes.append({
                    "node_type": "chapter",
                    "node_label": extract_chapter_number(line),
                    "title": line,
                    "full_text": "",  # Accumulated later
                    "page_num": page_num,
                    "position": position
                })
                position += 1
            
            # Detect section headings (heuristic: numbered like "1.1", "I.2")
            elif detect_section_heading(line):
                current_section = line
                
                nodes.append({
                    "node_type": "section",
                    "node_label": extract_section_number(line),
                    "title": line,
                    "full_text": "",
                    "page_num": page_num,
                    "position": position
                })
                position += 1
            
            # Detect object captions
            elif (caption_info := detect_object_caption(line)):
                obj_type, reference_label = caption_info
                title = extract_object_title(line, reference_label)
                
                nodes.append({
                    "node_type": obj_type,
                    "node_label": reference_label,
                    "title": title,
                    "full_text": "",  # Extract surrounding text
                    "page_num": page_num,
                    "position": position,
                    "metadata": {"reference": reference_label}
                })
                position += 1
            
            # Regular paragraph text
            else:
                if current_section:
                    # Append to current section's full_text
                    if nodes and nodes[-1]["node_type"] == "section":
                        nodes[-1]["full_text"] += line + " "
    
    doc.close()
    return nodes

def detect_chapter_heading(line: str) -> bool:
    """Heuristic: all caps, contains CHAPTER, < 100 chars"""
    return (
        line.isupper() and
        'CHAPTER' in line and
        len(line) < 100
    )

def extract_chapter_number(line: str) -> str:
    """Extract 'Chapter I' from 'CHAPTER I: ECONOMIC REVIEW'"""
    match = re.search(r'CHAPTER\s+([IVX]+)', line, re.IGNORECASE)
    return f"Chapter {match.group(1)}" if match else "Chapter"

def detect_section_heading(line: str) -> bool:
    """Heuristic: starts with number like '1.1' or 'I.2'"""
    return bool(re.match(r'^[IVX0-9]+\.\d+', line))

def extract_section_number(line: str) -> str:
    """Extract 'Section I.1' from 'I.1 Introduction'"""
    match = re.match(r'^([IVX0-9]+\.\d+)', line)
    return f"Section {match.group(1)}" if match else "Section"
```

---

### **Task 5.4: Reference Registry**

**File: `ingestion/pdf_ingest.py`**

Build a registry of all detected references for cross-linking:

```python
def build_reference_registry(nodes: List[dict]) -> dict:
    """
    Build registry of reference_label → node_id for cross-linking.
    
    Returns: {"Table I.1": node_id, "Box I.2": node_id, ...}
    """
    registry = {}
    
    for node in nodes:
        if node["node_type"] in ["table", "box", "chart"]:
            reference_label = node.get("metadata", {}).get("reference")
            if reference_label:
                registry[reference_label] = node.get("id")  # Set after DB insert
    
    return registry
```

---

### **Task 5.5: Cross-Linking PDF ↔ XLSX**

**Critical: Ensure PDF table references link to XLSX tables**

**File: `ingestion/pdf_ingest.py`**

```python
def link_pdf_to_xlsx(db: Session, corpus_id: int, reference_registry: dict):
    """
    Create edges linking PDF table nodes to XLSX data_tables.
    
    STOP CONDITION: If "Table I.x" exists in PDF but not in XLSX → STOP
    """
    from app.models.data import DataTable
    from app.models.edge import Edge
    
    # Get all XLSX tables in corpus
    xlsx_tables = db.query(DataTable).filter(
        DataTable.file_id.in_(
            db.query(DataFile.id).filter(DataFile.corpus_id == corpus_id)
        )
    ).all()
    
    # Build mapping: table_name → data_table_id
    xlsx_table_map = {}
    for table in xlsx_tables:
        # Normalize table names (e.g., "Table I.1" from title)
        normalized = normalize_table_reference(table.title)
        if normalized:
            xlsx_table_map[normalized] = table.id
    
    # Create edges for matching references
    for pdf_ref, pdf_node_id in reference_registry.items():
        if pdf_ref.startswith("Table") or pdf_ref.startswith("Chart"):
            xlsx_table_id = xlsx_table_map.get(pdf_ref)
            
            if not xlsx_table_id:
                print(f"⚠️  WARNING: {pdf_ref} in PDF but not found in XLSX tables")
                # STOP CONDITION: Critical reference missing
                continue
            
            # Create "refers_to" edge
            edge = Edge(
                corpus_id=corpus_id,
                source_node_id=pdf_node_id,
                target_node_id=None,  # XLSX tables don't have node_id (they're in data_tables)
                target_table_id=xlsx_table_id,
                rel_type="refers_to",
                metadata={"link_type": "pdf_to_xlsx"}
            )
            db.add(edge)
    
    db.commit()

def normalize_table_reference(title: str) -> Optional[str]:
    """
    Extract normalized reference from table title.
    
    Input: "Table I.1 - GDP Growth"
    Output: "Table I.1"
    """
    match = re.match(r'^(Table|Chart|Box)\s+([IVX]+\.\d+[a-z]?)', title, re.IGNORECASE)
    if match:
        return f"{match.group(1).capitalize()} {match.group(2)}"
    return None
```

---

### **Task 5.6: Edge Creation (ONLY {contains, refers_to, supports})**

**CRITICAL: Use ONLY these three edge types**

**File: `ingestion/pdf_ingest.py`**

```python
def create_hierarchy_edges(db: Session, corpus_id: int, nodes: List[dict]):
    """
    Create edges for document hierarchy.
    
    Edge types:
    - contains: parent contains child (Chapter contains Section)
    - refers_to: node references another node/object
    - supports: evidence supports claim
    """
    from app.models.edge import Edge
    
    for i, node in enumerate(nodes):
        # Find parent node
        parent_node = find_parent_node(nodes, i)
        
        if parent_node:
            edge = Edge(
                corpus_id=corpus_id,
                source_node_id=parent_node["id"],
                target_node_id=node["id"],
                rel_type="contains",  # Parent CONTAINS child
                metadata={"hierarchy": True}
            )
            db.add(edge)
    
    db.commit()

def find_parent_node(nodes: List[dict], current_index: int) -> Optional[dict]:
    """
    Find parent node for hierarchy.
    
    Rules:
    - Section parent is Chapter
    - Paragraph/object parent is Section (or Chapter if no section)
    """
    current = nodes[current_index]
    
    # Look backwards for parent
    for i in range(current_index - 1, -1, -1):
        node = nodes[i]
        
        if current["node_type"] == "section" and node["node_type"] == "chapter":
            return node
        
        if current["node_type"] in ["paragraph", "table", "box", "chart"]:
            if node["node_type"] == "section":
                return node
            elif node["node_type"] == "chapter":
                return node
    
    return None
```

---

### **Task 5.7: Offline Embeddings Generation**

**CRITICAL: Embeddings must be generated offline, NEVER at runtime**

**File: `ingestion/pdf_ingest.py`**

```python
import hashlib
from openai import OpenAI

def generate_embeddings_offline(db: Session, corpus_id: int, embedding_model: str = "text-embedding-3-large"):
    """
    Generate embeddings for all nodes in corpus.
    
    MUST:
    - Use consistent embedding_model_id
    - Store source_hash for reproducibility
    - Run OFFLINE only (never at runtime)
    """
    from app.models.node import Node
    from app.models.search import Embedding
    
    client = OpenAI()
    
    nodes = db.query(Node).filter(Node.corpus_id == corpus_id).all()
    
    for node in nodes:
        # Construct embedded text
        embedded_text = construct_embedded_text(node)
        
        # Compute source hash
        source_hash = hashlib.sha256(embedded_text.encode()).hexdigest()
        
        # Check if embedding already exists
        existing = db.query(Embedding).filter(
            Embedding.node_id == node.id,
            Embedding.embedding_model_id == embedding_model,
            Embedding.source_hash == source_hash
        ).first()
        
        if existing:
            print(f"✓ Embedding exists for node {node.id}")
            continue
        
        # Generate embedding
        response = client.embeddings.create(
            input=embedded_text,
            model=embedding_model
        )
        
        embedding_vector = response.data[0].embedding
        
        # Store in database
        embedding = Embedding(
            corpus_id=corpus_id,
            node_id=node.id,
            embedding_model_id=embedding_model,
            dimensionality=len(embedding_vector),
            embedding_vector=embedding_vector,
            source_hash=source_hash,
            metadata={"generated_at": "ingestion"}
        )
        db.add(embedding)
    
    db.commit()
    print(f"✓ Generated embeddings for {len(nodes)} nodes")

def construct_embedded_text(node) -> str:
    """
    Construct text to embed.
    
    Format: title + " - " + node_label + " - " + snippet
    """
    parts = []
    
    if node.title:
        parts.append(node.title)
    
    if node.node_label:
        parts.append(node.node_label)
    
    if node.snippet:
        parts.append(node.snippet)
    elif node.full_text:
        # Use first 300 chars as snippet
        parts.append(node.full_text[:300])
    
    return " - ".join(parts)
```

**STOP CONDITION:** If embeddings are generated at runtime (Phase 7), STOP immediately.

---

### **Task 5.8: Document Classification (Primary vs Supplement)**

**File: `ingestion/pdf_ingest.py`**

```python
def classify_document_role(filename: str, corpus_id: int) -> str:
    """
    Classify document as 'primary' or 'supplement'.
    
    Rules:
    - Primary: Main Economic Survey volume
    - Supplement: Annexures, Statistical Appendix, Technical Notes
    """
    filename_lower = filename.lower()
    
    supplement_keywords = [
        'annex', 'annexure', 'appendix', 'statistical',
        'technical note', 'supplement', 'addendum'
    ]
    
    if any(kw in filename_lower for kw in supplement_keywords):
        return 'supplement'
    
    return 'primary'
```

**Usage in main ingestion:**

```python
def ingest_pdf_file(pdf_path: str, corpus_id: int):
    """Main PDF ingestion entry point"""
    db = SessionLocal()
    
    try:
        # Create document record
        doc_record = Document(
            corpus_id=corpus_id,
            filename=Path(pdf_path).name,
            path=pdf_path,
            role=classify_document_role(Path(pdf_path).name, corpus_id)  # PRIMARY or SUPPLEMENT
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)
        
        # Extract structure
        nodes = extract_pdf_structure(pdf_path)
        
        # Create node records
        node_records = []
        for node_data in nodes:
            node = Node(
                corpus_id=corpus_id,
                document_id=doc_record.id,
                **node_data
            )
            db.add(node)
            node_records.append(node)
        
        db.commit()
        
        # Refresh to get IDs
        for node in node_records:
            db.refresh(node)
        
        # Build reference registry
        reference_registry = build_reference_registry(node_records)
        
        # Create hierarchy edges
        create_hierarchy_edges(db, corpus_id, node_records)
        
        # Cross-link to XLSX
        link_pdf_to_xlsx(db, corpus_id, reference_registry)
        
        # Generate embeddings (OFFLINE)
        generate_embeddings_offline(db, corpus_id)
        
        print(f"✓ Ingested {len(node_records)} nodes from {pdf_path}")
        
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python -m ingestion.pdf_ingest <pdf_path> <corpus_id>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    corpus_id = int(sys.argv[2])
    
    ingest_pdf_file(pdf_path, corpus_id)
```

---

## ✅ Acceptance Criteria

### **Test 1: Structure Extraction**
```bash
python -m ingestion.pdf_ingest survey.pdf 1
```

**Verify:**
```sql
SELECT node_type, COUNT(*) FROM nodes WHERE corpus_id = 1 GROUP BY node_type;
```

**Expected:**
- chapter: 5-10
- section: 20-50
- paragraph: 100+
- table/box/chart: 50-200

---

### **Test 2: Cross-Linking (CRITICAL)**
```bash
python -m ingestion.pdf_ingest survey.pdf 1
```

**Verify:**
```sql
SELECT e.rel_type, COUNT(*) 
FROM edges e
WHERE e.corpus_id = 1 AND e.rel_type = 'refers_to'
GROUP BY e.rel_type;
```

**Expected:** refers_to edges > 0

**STOP CONDITION:** If "Table I.2" exists in PDF but no edge links to XLSX → STOP

---

### **Test 3: Edge Type Validation**
```sql
SELECT DISTINCT rel_type FROM edges WHERE corpus_id = 1;
```

**Expected:** ONLY {contains, refers_to, supports}

**STOP CONDITION:** If any other rel_type exists → STOP and fix immediately

---

### **Test 4: Embeddings Offline Verification**
```sql
SELECT COUNT(*), embedding_model_id 
FROM embeddings 
WHERE corpus_id = 1 
GROUP BY embedding_model_id;
```

**Expected:**
- Count matches number of nodes
- embedding_model_id is consistent (e.g., "text-embedding-3-large")
- All source_hash values are non-null

**STOP CONDITION:** If embeddings generated at runtime in Phase 7 → STOP

---

### **Test 5: Document Role Classification**
```sql
SELECT role, COUNT(*) FROM documents WHERE corpus_id = 1 GROUP BY role;
```

**Expected:**
- primary: 1-3 (main survey volumes)
- supplement: 0-5 (annexures, statistical appendix)

---

## 📝 Deliverables Checklist

- [ ] PDF structure extractor working
- [ ] Reference registry built
- [ ] Cross-linking PDF ↔ XLSX working
- [ ] Edges use ONLY {contains, refers_to, supports}
- [ ] Embeddings generated offline with model_id + source_hash
- [ ] Document role classification implemented
- [ ] All acceptance tests passing

---

## 🔗 Next Phase

Once all deliverables complete and stop conditions verified:
- **Phase 6: Summaries & Claim Cards** (LLM-generated briefings)
