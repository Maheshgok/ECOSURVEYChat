# PDF Ingestion Common Errors (Phase 5)

**Reference:** Skills/PDF_Ingestion_Skills.md

---

## Error 1: Cross-Link Missing (STOP CONDITION)

**Symptom:** "Table I.2" in PDF but no edge links to XLSX

**Cause:** Reference normalization mismatch

**Fix:**
```python
# Normalize both sides identically
def normalize_ref(text):
    # Extract "Table I.2" from "Table I.2: GDP Growth"
    match = re.match(r'^(Table|Box|Chart)\s+([IVX]+\.\d+[a-z]?)', text, re.IGNORECASE)
    if match:
        return f"{match.group(1).capitalize()} {match.group(2)}"
    return None

# In link_pdf_to_xlsx():
pdf_ref_normalized = normalize_ref(pdf_ref)
xlsx_ref_normalized = normalize_ref(xlsx_table.title)

if pdf_ref_normalized == xlsx_ref_normalized:
    # Create edge
```

**Verification:**
```sql
SELECT COUNT(*) FROM edges WHERE rel_type = 'refers_to' AND corpus_id = 1;
```
Must be > 0.

---

## Error 2: Invalid Edge Types (STOP CONDITION)

**Symptom:** Edge with `rel_type` value other than `contains`, `refers_to`, or `supports`

**Cause:** Code using non-standard edge types (e.g., `parent_of`, `child_of`, `depends_on`). Spec strictly limits to 3 types only.

**Fix:**
```python
# ONLY allow these 3:
VALID_REL_TYPES = {'contains', 'refers_to', 'supports'}

def create_edge(source_id, target_id, rel_type):
    if rel_type not in VALID_REL_TYPES:
        raise ValueError(f"Invalid rel_type: {rel_type}. Must be in {VALID_REL_TYPES}")
    
    edge = Edge(source_node_id=source_id, target_node_id=target_id, rel_type=rel_type)
    return edge
```

**Verification:**
```sql
SELECT DISTINCT rel_type FROM edges WHERE corpus_id = 1;
```
Must return ONLY: contains, refers_to, supports

---

## Error 3: Chapter Detection Fails

**Symptom:** No chapter nodes created

**Cause:** `detect_chapter_heading()` too strict

**Fix:**
```python
def detect_chapter_heading(line: str) -> bool:
    # Relax constraints
    line_upper = line.upper()
    
    # Must contain CHAPTER
    if 'CHAPTER' not in line_upper:
        return False
    
    # Must be < 150 chars (not 100)
    if len(line) > 150:
        return False
    
    # Allow mixed case if mostly uppercase
    uppercase_ratio = sum(1 for c in line if c.isupper()) / len(line)
    return uppercase_ratio > 0.6
```

---

## Error 4: Caption Not Detected

**Symptom:** "Table I.2: GDP Growth" creates paragraph node, not table node

**Cause:** Caption pattern not matching

**Fix:**
```python
# Make pattern case-insensitive and flexible
patterns = [
    (r'Table\s+([IVX]+\.\d+[a-z]?)', 'table'),
    (r'Box\s+([IVX]+\.\d+[a-z]?)', 'box'),
    (r'Chart\s+([IVX]+\.\d+[a-z]?)', 'chart'),
]

match = re.search(pattern, text, re.IGNORECASE)  # Add re.IGNORECASE
```

---

## Error 5: Embeddings at Runtime (STOP CONDITION)

**Symptom:** API response time > 5 seconds due to embedding generation

**Cause:** `generate_embeddings_offline()` called in API route

**Fix:**
- Embeddings MUST be generated in ingestion phase only
- Add CI check to prevent importing `generate_embeddings_offline` in `app/api/` or `app/services/`

**CI Check:**
```bash
# In .github/workflows/ci.yml
grep -r "generate_embeddings" app/api/ app/services/ && exit 1 || exit 0
```

---

## Error 6: Document Role Not Set

**Symptom:** All documents have `role = NULL`

**Cause:** `classify_document_role()` not called

**Fix:**
```python
# In ingest_pdf_file():
doc_record = Document(
    corpus_id=corpus_id,
    filename=Path(pdf_path).name,
    role=classify_document_role(Path(pdf_path).name, corpus_id)  # ADD THIS
)
```

---

## Error 7: Node Position Not Sequential

**Symptom:** Nodes have position = 0 or duplicates

**Cause:** Position counter not incremented

**Fix:**
```python
position = 0
for page in doc:
    for line in lines:
        # ... create node ...
        node_data["position"] = position
        position += 1  # INCREMENT
```

---

## Error 8: Snippet Missing

**Symptom:** Nodes have `snippet = NULL`

**Cause:** `snippet` not extracted from `full_text`

**Fix:**
```python
# After extracting full_text:
if node.full_text:
    node.snippet = node.full_text[:300]  # First 300 chars
```

---

## Error 9: Hierarchy Edges Missing

**Symptom:** No "contains" edges

**Cause:** `create_hierarchy_edges()` not called

**Fix:**
```python
# In ingest_pdf_file(), after creating nodes:
create_hierarchy_edges(db, corpus_id, node_records)  # ADD THIS
```

---

## Error 10: Reference Registry Empty

**Symptom:** `build_reference_registry()` returns empty dict

**Cause:** Nodes don't have `metadata` field with "reference"

**Fix:**
```python
# In extract_pdf_structure(), when creating object nodes:
nodes.append({
    "node_type": obj_type,
    "node_label": reference_label,
    "metadata": {"reference": reference_label}  # ADD THIS
})
```

---

## Error 11: Multi-Chapter Ingestion Conflicts

**Symptom:** Chapter I in document 2 overwrites Chapter I from document 1

**Cause:** No document-level isolation

**Fix:**
```python
# Use document_id in node_label
node_label = f"Chapter {roman} (Doc {doc_record.id})"
```

---

## Error 12: PDF Text Extraction Garbled

**Symptom:** Extracted text has encoding issues or line breaks missing

**Cause:** PyMuPDF default extraction

**Fix:**
```python
# Use better extraction
text = page.get_text("text", sort=True)  # Add sort=True

# OR use layout-aware extraction
text = page.get_text("blocks")
```

---

## Error 13: Embedding Source Hash Not Stored

**Symptom:** Embeddings table has `source_hash = NULL`

**Cause:** `source_hash` not computed

**Fix:**
```python
import hashlib

embedded_text = construct_embedded_text(node)
source_hash = hashlib.sha256(embedded_text.encode()).hexdigest()

embedding = Embedding(
    ...,
    source_hash=source_hash  # ADD THIS
)
```

---

## Debugging Checklist

- [ ] Chapter nodes created
- [ ] Section nodes created
- [ ] Object nodes (table/box/chart) created
- [ ] All nodes have sequential position
- [ ] All nodes have snippet
- [ ] Hierarchy edges (contains) exist
- [ ] Reference registry populated
- [ ] Cross-link edges (refers_to) exist
- [ ] Edge types are ONLY {contains, refers_to, supports}
- [ ] Document role set (primary/supplement)
- [ ] Embeddings have source_hash
- [ ] No embeddings generated at runtime

---

## Escalation

If cross-linking still fails:
1. Print `reference_registry` to verify contents
2. Print `xlsx_table_map` to verify XLSX table names
3. Check if normalization logic matches on both sides
4. Manually verify "Table I.2" appears in both PDF and XLSX
