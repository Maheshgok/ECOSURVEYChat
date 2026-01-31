"""Evidence endpoints"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional

from app.core.database import get_db
from app.api.auth import get_current_user_dependency, UserResponse
from app.models import Node, Document, DataTable, DataFile, DataSheet, IndicatorSeries, Indicator

router = APIRouter()


class EvidenceNodeResponse(BaseModel):
    id: str
    label: Optional[str]
    title: Optional[str]
    node_type: str
    page_start: Optional[int]
    page_end: Optional[int]
    document_title: str
    document_role: str
    snippet: str


class EvidenceTableResponse(BaseModel):
    id: str
    table_name: str
    title: Optional[str]
    range_a1: Optional[str]
    units: Optional[str]
    notes: Optional[str]
    file: str
    sheet: str
    preview: List[Any]


class EvidenceSeriesResponse(BaseModel):
    id: str
    indicator_name: str
    indicator_topic: Optional[str]
    unit: Optional[str]
    freq: Optional[str]
    geo_key: Optional[str]
    last_time: Optional[str]
    last_value: Optional[float]
    derived_views: Dict[str, Any]


def _table_preview(table_json: Any) -> List[Any]:
    if table_json is None:
        return []
    if isinstance(table_json, list):
        rows = table_json
    elif isinstance(table_json, dict):
        rows = table_json.get("rows") or table_json.get("data") or []
    else:
        return []
    preview = []
    for row in rows[:10]:
        if isinstance(row, list):
            preview.append(row[:10])
        else:
            preview.append(row)
    return preview


@router.get("/evidence/node/{node_id}", response_model=EvidenceNodeResponse)
async def get_evidence_node(
    node_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_dependency),
):
    """Get evidence node (PDF paragraph/box/table/chart snippet)"""
    node = (
        db.query(Node, Document)
        .join(Document, Document.id == Node.document_id)
        .filter(Node.id == node_id)
        .first()
    )
    if not node:
        raise HTTPException(status_code=404, detail="Evidence node not found")
    record, doc = node

    return EvidenceNodeResponse(
        id=str(record.id),
        label=record.label,
        title=record.title,
        node_type=record.node_type,
        page_start=record.page_start,
        page_end=record.page_end,
        document_title=doc.title,
        document_role=doc.role,
        snippet=(record.text or "")[:1200],
    )


@router.get("/evidence/table/{table_id}", response_model=EvidenceTableResponse)
async def get_evidence_table(
    table_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_dependency),
):
    """Get dataset table preview and metadata"""
    result = (
        db.query(DataTable, DataFile, DataSheet)
        .join(DataFile, DataFile.id == DataTable.file_id)
        .join(DataSheet, DataSheet.id == DataTable.sheet_id)
        .filter(DataTable.id == table_id)
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Data table not found")
    table, data_file, sheet = result

    return EvidenceTableResponse(
        id=str(table.id),
        table_name=table.table_name,
        title=table.title,
        range_a1=table.range_a1,
        units=table.units,
        notes=table.notes,
        file=data_file.filename,
        sheet=sheet.sheet_name,
        preview=_table_preview(table.table_json),
    )


@router.get("/evidence/series/{series_id}", response_model=EvidenceSeriesResponse)
async def get_evidence_series(
    series_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_dependency),
):
    """Get indicator series summary"""
    result = (
        db.query(IndicatorSeries, Indicator)
        .join(Indicator, Indicator.id == IndicatorSeries.indicator_id)
        .filter(IndicatorSeries.id == series_id)
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Series not found")
    series, indicator = result

    points = series.points or []
    last_point = points[-1] if points else {}
    last_time = last_point.get("time") if isinstance(last_point, dict) else None
    last_value = last_point.get("value") if isinstance(last_point, dict) else None

    return EvidenceSeriesResponse(
        id=str(series.id),
        indicator_name=indicator.name,
        indicator_topic=indicator.topic,
        unit=indicator.unit,
        freq=indicator.freq,
        geo_key=series.geo_key,
        last_time=last_time,
        last_value=last_value,
        derived_views=series.derived_views or {},
    )
