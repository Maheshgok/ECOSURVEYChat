"""
Deterministic retrieval and context pack construction for Phase 7.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import re
import time
import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, Text

from app.core.settings import settings
from app.models import (
    ClaimCard,
    TopicBrief,
    Indicator,
    IndicatorSeries,
    Node,
    Document,
    DataTable,
    DataSheet,
    DataFile,
    Edge,
)


DATA_KEYWORDS = {
    "trend", "series", "years", "cagr", "yoy", "compare", "vs", "rank",
    "top", "bottom", "growth", "inflation", "rate", "percent", "%",
    "increase", "decrease", "change",
}

EXPLICIT_PATTERNS = [
    r"\bTable\s+[A-Z]?[IVXLC]+\.?\d+[A-Za-z]*\b",
    r"\bBox\s+[A-Z]?[IVXLC]+\.?\d+[A-Za-z]*\b",
    r"\bChart\s+[A-Z]?[IVXLC]+\.?\d+[A-Za-z]*\b",
    r"\bChapter\s+\d+\b",
]


@dataclass
class RetrievalItem:
    id: str
    category: str
    score: float
    token_cost: int
    data: Dict
    is_supplement: bool = False
    explicit: bool = False
    sticky: bool = False


@dataclass
class RetrievalResult:
    context_pack: Dict
    retrieved_node_ids: List[str]
    retrieved_series_ids: List[str]
    used_evidence: List[Dict]


def classify_query(query: str) -> str:
    lowered = query.lower()
    if any(keyword in lowered for keyword in DATA_KEYWORDS):
        return "data"
    return "narrative"


def extract_explicit_refs(query: str) -> List[str]:
    refs: List[str] = []
    for pattern in EXPLICIT_PATTERNS:
        for match in re.findall(pattern, query, flags=re.IGNORECASE):
            refs.append(match)
    return list(dict.fromkeys(refs))


def tokenize(query: str) -> List[str]:
    return [token for token in re.split(r"\W+", query.lower()) if token]


def score_text(text: Optional[str], terms: List[str]) -> int:
    if not text:
        return 0
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered)


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate_text(text: Optional[str], max_chars: int) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def retrieve_claim_cards(db: Session, corpus_id: str, terms: List[str], limit: int = 10) -> List[ClaimCard]:
    query = db.query(ClaimCard).filter(ClaimCard.corpus_id == corpus_id)
    if terms:
        filters = [
            ClaimCard.claim_text.ilike(f"%{term}%") |
            ClaimCard.explanation.ilike(f"%{term}%") |
            ClaimCard.topic.ilike(f"%{term}%")
            for term in terms
        ]
        query = query.filter(or_(*filters))
    return query.order_by(ClaimCard.confidence.desc()).limit(limit).all()


def retrieve_topic_briefs(db: Session, corpus_id: str, terms: List[str], limit: int = 5) -> List[TopicBrief]:
    query = db.query(TopicBrief).filter(TopicBrief.corpus_id == corpus_id)
    if terms:
        filters = [
            TopicBrief.topic.ilike(f"%{term}%") |
            cast(TopicBrief.bullets, Text).ilike(f"%{term}%")
            for term in terms
        ]
        query = query.filter(or_(*filters))
    return query.limit(limit).all()


def retrieve_indicator_series(db: Session, corpus_id: str, terms: List[str], limit: int = 10) -> List[Tuple[IndicatorSeries, Indicator]]:
    query = (
        db.query(IndicatorSeries, Indicator)
        .join(Indicator, Indicator.id == IndicatorSeries.indicator_id)
        .filter(Indicator.corpus_id == corpus_id)
    )
    if terms:
        filters = [
            Indicator.name.ilike(f"%{term}%") |
            cast(Indicator.aliases, Text).ilike(f"%{term}%") |
            Indicator.topic.ilike(f"%{term}%")
            for term in terms
        ]
        query = query.filter(or_(*filters))
    return query.limit(limit).all()


def retrieve_nodes(db: Session, corpus_id: str, terms: List[str], limit: int = 20) -> List[Tuple[Node, Document]]:
    query = (
        db.query(Node, Document)
        .join(Document, Document.id == Node.document_id)
        .filter(Document.corpus_id == corpus_id)
    )
    if terms:
        filters = [
            Node.text.ilike(f"%{term}%") |
            Node.label.ilike(f"%{term}%") |
            Node.title.ilike(f"%{term}%")
            for term in terms
        ]
        query = query.filter(or_(*filters))
    return query.limit(limit).all()


def retrieve_tables(db: Session, corpus_id: str, terms: List[str], limit: int = 10) -> List[Tuple[DataTable, DataFile, DataSheet]]:
    query = (
        db.query(DataTable, DataFile, DataSheet)
        .join(DataFile, DataFile.id == DataTable.file_id)
        .join(DataSheet, DataSheet.id == DataTable.sheet_id)
        .filter(DataFile.corpus_id == corpus_id)
    )
    if terms:
        filters = [
            DataTable.title.ilike(f"%{term}%") |
            DataTable.table_name.ilike(f"%{term}%") |
            DataTable.notes.ilike(f"%{term}%")
            for term in terms
        ]
        query = query.filter(or_(*filters))
    return query.limit(limit).all()


def retrieve_explicit_nodes(db: Session, corpus_id: str, refs: List[str]) -> List[Tuple[Node, Document]]:
    if not refs:
        return []
    query = (
        db.query(Node, Document)
        .join(Document, Document.id == Node.document_id)
        .filter(Document.corpus_id == corpus_id)
    )
    filters = [Node.label.ilike(f"%{ref}%") for ref in refs]
    return query.filter(or_(*filters)).all()


def expand_graph(db: Session, node_ids: List[str]) -> List[str]:
    if not node_ids:
        return []
    edges = (
        db.query(Edge)
        .filter(Edge.src_node_id.in_(node_ids))
        .filter(Edge.rel_type.in_(["refers_to", "supports"]))
        .all()
    )
    return [str(edge.dst_node_id) for edge in edges]


def build_context_pack(
    db: Session,
    corpus_id: str,
    question: str,
    conversation_memory: List[Dict],
) -> RetrievalResult:
    terms = tokenize(question)
    query_type = classify_query(question)
    explicit_refs = extract_explicit_refs(question)

    explicit_nodes = retrieve_explicit_nodes(db, corpus_id, explicit_refs)
    claim_cards = retrieve_claim_cards(db, corpus_id, terms)
    topic_briefs = retrieve_topic_briefs(db, corpus_id, terms)
    indicator_series = retrieve_indicator_series(db, corpus_id, terms)
    nodes = retrieve_nodes(db, corpus_id, terms)
    tables = retrieve_tables(db, corpus_id, terms)

    explicit_node_ids = {str(node.id) for node, _doc in explicit_nodes}

    items: List[RetrievalItem] = []

    for card in claim_cards:
        score = score_text(card.claim_text, terms) + score_text(card.explanation, terms)
        token_cost = estimate_tokens(card.claim_text or "") + estimate_tokens(card.explanation or "")
        data = {
            "id": str(card.id),
            "topic": card.topic,
            "claim_text": card.claim_text,
            "explanation": card.explanation,
            "evidence_node_ids": card.evidence_node_ids or [],
            "evidence_series_ids": card.evidence_series_ids or [],
        }
        items.append(RetrievalItem(id=str(card.id), category="claims", score=score, token_cost=token_cost, data=data))

    for brief in topic_briefs:
        score = score_text(brief.topic, terms) + score_text(json.dumps(brief.bullets or []), terms)
        token_cost = estimate_tokens(json.dumps(brief.bullets or []))
        data = {
            "id": str(brief.id),
            "topic": brief.topic,
            "bullets": brief.bullets,
            "key_numbers": brief.key_numbers,
            "linked_node_ids": brief.linked_node_ids or [],
            "linked_series_ids": brief.linked_series_ids or [],
        }
        items.append(RetrievalItem(id=str(brief.id), category="claims", score=score, token_cost=token_cost, data=data))

    for series, indicator in indicator_series:
        score = score_text(indicator.name, terms) + score_text(indicator.topic, terms)
        points = series.points or []
        last_point = points[-1] if points else None
        token_cost = estimate_tokens(json.dumps(last_point or {})) + 120
        data = {
            "id": str(series.id),
            "indicator_name": indicator.name,
            "indicator_topic": indicator.topic,
            "unit": indicator.unit,
            "freq": indicator.freq,
            "geo_key": series.geo_key,
            "last_point": last_point,
            "derived_views": series.derived_views or {},
        }
        items.append(RetrievalItem(id=str(series.id), category="data", score=score, token_cost=token_cost, data=data))

    for node, doc in nodes:
        score = score_text(node.text, terms) + score_text(node.label, terms)
        token_cost = estimate_tokens(node.text or "")
        is_supplement = (doc.role == "supplement")
        data = {
            "id": str(node.id),
            "label": node.label,
            "title": node.title,
            "node_type": node.node_type,
            "page_start": node.page_start,
            "page_end": node.page_end,
            "document_title": doc.title,
            "document_role": doc.role,
            "snippet": truncate_text(node.text, 1200),
        }
        explicit = str(node.id) in explicit_node_ids
        items.append(
            RetrievalItem(
                id=str(node.id),
                category="narrative",
                score=score,
                token_cost=token_cost,
                data=data,
                is_supplement=is_supplement,
                explicit=explicit,
                sticky=explicit,
            )
        )

    for table, data_file, sheet in tables:
        score = score_text(table.title, terms) + score_text(table.table_name, terms)
        token_cost = estimate_tokens(json.dumps(table.table_json or {}))
        data = {
            "id": str(table.id),
            "table_name": table.table_name,
            "title": table.title,
            "range_a1": table.range_a1,
            "units": table.units,
            "notes": table.notes,
            "file": data_file.filename,
            "sheet": sheet.sheet_name,
        }
        items.append(RetrievalItem(id=str(table.id), category="data", score=score, token_cost=token_cost, data=data))

    # Graph expansion for nodes
    primary_node_ids = [item.id for item in items if item.category == "narrative"]
    expanded_node_ids = expand_graph(db, primary_node_ids)
    expanded_nodes = (
        db.query(Node, Document)
        .join(Document, Document.id == Node.document_id)
        .filter(Node.id.in_(expanded_node_ids))
        .all()
    )
    for node, doc in expanded_nodes:
        if str(node.id) in primary_node_ids:
            continue
        data = {
            "id": str(node.id),
            "label": node.label,
            "title": node.title,
            "node_type": node.node_type,
            "page_start": node.page_start,
            "page_end": node.page_end,
            "document_title": doc.title,
            "document_role": doc.role,
            "snippet": truncate_text(node.text, 1200),
            "linked_from_graph": True,
        }
        items.append(
            RetrievalItem(
                id=str(node.id),
                category="narrative",
                score=1,
                token_cost=estimate_tokens(node.text or ""),
                data=data,
                is_supplement=(doc.role == "supplement"),
                explicit=False,
                sticky=True,
            )
        )

    # Apply boosts and selection
    for item in items:
        if item.explicit:
            item.score += 5
        if item.category == "narrative" and item.data.get("document_role") == "primary":
            item.score += 2
        if item.data.get("linked_from_graph"):
            item.score += 1
        if item.is_supplement and not item.explicit:
            item.score -= 2

    def select_category(category: str, quota: int, supplement_limit: Optional[int] = None) -> List[RetrievalItem]:
        subset = [item for item in items if item.category == category]
        subset.sort(key=lambda x: (x.score / max(1, x.token_cost)), reverse=True)
        selected: List[RetrievalItem] = []
        used_tokens = 0
        supplement_tokens = 0
        for item in subset:
            if item.sticky and item not in selected:
                selected.append(item)
                used_tokens += item.token_cost
                if item.is_supplement:
                    supplement_tokens += item.token_cost
        for item in subset:
            if item in selected:
                continue
            if used_tokens + item.token_cost > quota:
                continue
            if supplement_limit is not None and item.is_supplement and not item.explicit:
                if supplement_tokens + item.token_cost > supplement_limit:
                    continue
            selected.append(item)
            used_tokens += item.token_cost
            if item.is_supplement:
                supplement_tokens += item.token_cost
        return selected

    claims_selected = select_category("claims", settings.CONTEXT_QUOTA_CLAIMS)
    narrative_selected = select_category(
        "narrative",
        settings.CONTEXT_QUOTA_NARRATIVE,
        supplement_limit=int(settings.CONTEXT_QUOTA_NARRATIVE * settings.SUPPLEMENT_QUOTA_PERCENT / 100),
    )
    data_selected = select_category("data", settings.CONTEXT_QUOTA_DATA)

    # Must-include rule: top claim card and top indicator series for data queries
    if claims_selected == [] and claim_cards:
        card = claim_cards[0]
        claims_selected.append(
            RetrievalItem(
                id=str(card.id),
                category="claims",
                score=1,
                token_cost=estimate_tokens(card.claim_text or ""),
                data={
                    "id": str(card.id),
                    "topic": card.topic,
                    "claim_text": card.claim_text,
                    "explanation": card.explanation,
                    "evidence_node_ids": card.evidence_node_ids or [],
                    "evidence_series_ids": card.evidence_series_ids or [],
                },
                sticky=True,
            )
        )

    if query_type in {"data", "mixed"} and not data_selected and indicator_series:
        series, indicator = indicator_series[0]
        data_selected.append(
            RetrievalItem(
                id=str(series.id),
                category="data",
                score=1,
                token_cost=estimate_tokens(json.dumps(series.points or [])),
                data={
                    "id": str(series.id),
                    "indicator_name": indicator.name,
                    "indicator_topic": indicator.topic,
                    "unit": indicator.unit,
                    "freq": indicator.freq,
                    "geo_key": series.geo_key,
                    "last_point": (series.points or [])[-1] if series.points else None,
                    "derived_views": series.derived_views or {},
                },
                sticky=True,
            )
        )

    # Assemble context pack
    context_pack = {
        "question": question,
        "query_type": query_type,
        "explicit_refs": explicit_refs,
        "conversation_memory": conversation_memory,
        "claim_cards": [item.data for item in claims_selected],
        "narrative_nodes": [item.data for item in narrative_selected],
        "data_items": [item.data for item in data_selected],
        "generated_at": datetime.utcnow().isoformat(),
    }

    retrieved_node_ids = [item.id for item in narrative_selected]
    retrieved_series_ids = [item.id for item in data_selected]

    used_evidence: List[Dict] = []
    for item in claims_selected:
        used_evidence.append({"type": "claim_card", "id": item.id, "topic": item.data.get("topic")})
    for item in narrative_selected:
        used_evidence.append({"type": "node", "id": item.id, "label": item.data.get("label")})
    for item in data_selected:
        used_evidence.append({"type": "series", "id": item.id, "name": item.data.get("indicator_name")})

    return RetrievalResult(
        context_pack=context_pack,
        retrieved_node_ids=retrieved_node_ids,
        retrieved_series_ids=retrieved_series_ids,
        used_evidence=used_evidence,
    )
