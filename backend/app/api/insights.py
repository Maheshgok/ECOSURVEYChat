"""Phase 5 Insights and Summaries API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Optional
from datetime import datetime

from app.api.auth import get_current_user_dependency as get_current_user, UserResponse
from app.core.database import get_db
from app.models import User, Insight, Summary
from insights.extractors import InsightExtractor
from insights.generators import SummaryGenerator
from insights.embeddings import EmbeddingService


router = APIRouter(prefix="/api", tags=["insights"])


@router.post("/insights/extract/{table_id}")
async def extract_insights(
    table_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Extract insights from a data table
    
    Args:
        table_id: ID of data table to analyze
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Dict with extracted insights and storage IDs
    """
    try:
        # Verify user owns this table
        from app.models import DataTable
        table = db.query(DataTable).filter(
            DataTable.id == table_id,
            DataTable.user_id == current_user.id
        ).first()
        
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        
        # Extract insights
        extractor = InsightExtractor(table_id, db)
        insights_dict = extractor.get_all_insights()
        
        if not insights_dict:
            raise HTTPException(status_code=400, detail="No data to analyze")
        
        # Store insights in database
        stored_ids = _store_insights(
            table_id, current_user.id, insights_dict, db
        )
        
        return {
            "status": "success",
            "message": "Insights extracted successfully",
            "table_id": table_id,
            "table_name": table.name,
            "insights": insights_dict,
            "stored_insight_ids": stored_ids,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/summaries/generate/{table_id}")
async def generate_summary(
    table_id: int,
    summary_type: str = Query("detailed", regex="^(executive|detailed)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Generate summary from table insights
    
    Args:
        table_id: ID of data table
        summary_type: 'executive' or 'detailed'
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Dict with generated summary and metadata
    """
    try:
        # Verify user owns this table
        from app.models import DataTable
        table = db.query(DataTable).filter(
            DataTable.id == table_id,
            DataTable.user_id == current_user.id
        ).first()
        
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        
        # Extract insights
        extractor = InsightExtractor(table_id, db)
        insights_dict = extractor.get_all_insights()
        
        if not insights_dict:
            raise HTTPException(status_code=400, detail="No data to analyze")
        
        # Generate summary
        generator = SummaryGenerator(insights_dict, table.name)
        
        if summary_type == "executive":
            content = generator.generate_executive_summary()
        else:
            content = generator.generate_detailed_summary()
        
        key_points = generator.get_key_points()
        
        # Store summary
        summary = Summary(
            data_table_id=table_id,
            user_id=current_user.id,
            summary_type=summary_type,
            content=content,
            key_points=key_points,
            metadata={
                "generation_method": "rule-based",
                "version": "1.0",
                "generated_at": datetime.utcnow().isoformat()
            }
        )
        db.add(summary)
        db.commit()
        db.refresh(summary)
        
        return {
            "status": "success",
            "message": "Summary generated successfully",
            "table_id": table_id,
            "summary_id": summary.id,
            "summary_type": summary_type,
            "content": content,
            "key_points": key_points,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/summaries/{table_id}")
async def get_summaries(
    table_id: int,
    summary_type: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Retrieve summaries for a table
    
    Args:
        table_id: ID of data table
        summary_type: Optional filter by type
        limit: Number of results
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of summaries
    """
    try:
        # Verify user owns this table
        from app.models import DataTable
        table = db.query(DataTable).filter(
            DataTable.id == table_id,
            DataTable.user_id == current_user.id
        ).first()
        
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        
        # Query summaries
        query = db.query(Summary).filter(
            Summary.data_table_id == table_id,
            Summary.user_id == current_user.id
        )
        
        if summary_type:
            query = query.filter(Summary.summary_type == summary_type)
        
        summaries = query.order_by(Summary.created_at.desc()).limit(limit).all()
        
        return {
            "status": "success",
            "table_id": table_id,
            "count": len(summaries),
            "summaries": [
                {
                    "id": s.id,
                    "summary_type": s.summary_type,
                    "content": s.content,
                    "key_points": s.key_points,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat()
                }
                for s in summaries
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")


@router.get("/insights/{table_id}")
async def get_insights(
    table_id: int,
    insight_type: Optional[str] = None,
    metric: Optional[str] = None,
    min_confidence: float = Query(0.0, ge=0, le=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Retrieve insights for a table
    
    Args:
        table_id: ID of data table
        insight_type: Optional filter (statistic, pattern, anomaly, trend)
        metric: Optional filter by metric name
        min_confidence: Minimum confidence score
        limit: Number of results
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of insights
    """
    try:
        # Verify user owns this table
        from app.models import DataTable
        table = db.query(DataTable).filter(
            DataTable.id == table_id,
            DataTable.user_id == current_user.id
        ).first()
        
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        
        # Query insights
        query = db.query(Insight).filter(
            Insight.data_table_id == table_id,
            Insight.user_id == current_user.id,
            Insight.confidence >= min_confidence
        )
        
        if insight_type:
            query = query.filter(Insight.insight_type == insight_type)
        
        if metric:
            query = query.filter(Insight.metric.ilike(f"%{metric}%"))
        
        insights = query.order_by(
            Insight.confidence.desc(),
            Insight.created_at.desc()
        ).limit(limit).all()
        
        return {
            "status": "success",
            "table_id": table_id,
            "filters": {
                "insight_type": insight_type,
                "metric": metric,
                "min_confidence": min_confidence
            },
            "count": len(insights),
            "insights": [
                {
                    "id": i.id,
                    "insight_type": i.insight_type,
                    "metric": i.metric,
                    "value": i.value,
                    "confidence": float(i.confidence),
                    "description": i.description,
                    "supporting_data": i.supporting_data,
                    "created_at": i.created_at.isoformat()
                }
                for i in insights
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")


@router.delete("/insights/{insight_id}")
async def delete_insight(
    insight_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Delete an insight
    
    Args:
        insight_id: ID of insight to delete
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Confirmation message
    """
    try:
        # Find and verify ownership
        insight = db.query(Insight).filter(
            Insight.id == insight_id,
            Insight.user_id == current_user.id
        ).first()
        
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")
        
        # Delete
        db.delete(insight)
        db.commit()
        
        return {
            "status": "success",
            "message": "Insight deleted",
            "insight_id": insight_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


def _store_insights(
    table_id: int,
    user_id: int,
    insights_dict: Dict,
    db: Session
) -> Dict:
    """
    Store extracted insights in database
    
    Args:
        table_id: Data table ID
        user_id: User ID
        insights_dict: Dict with statistics, patterns, anomalies, trends
        db: Database session
        
    Returns:
        Dict with stored IDs
    """
    stored_ids = {
        "statistics": [],
        "patterns": [],
        "anomalies": [],
        "trends": []
    }
    
    # Store statistics
    for metric, stats in insights_dict.get("statistics", {}).items():
        insight = Insight(
            data_table_id=table_id,
            user_id=user_id,
            insight_type="statistic",
            metric=metric,
            value=str(stats.get("mean")),
            confidence=0.95,
            description=f"Mean: {stats.get('mean')}, Median: {stats.get('median')}",
            supporting_data=stats
        )
        db.add(insight)
        db.flush()
        stored_ids["statistics"].append(insight.id)
    
    # Store patterns
    for pattern in insights_dict.get("patterns", []):
        insight = Insight(
            data_table_id=table_id,
            user_id=user_id,
            insight_type="pattern",
            metric=pattern["metric"],
            value=pattern["value"],
            confidence=min(pattern.get("percentage", 0) / 100, 0.99),
            description=f"Value appears {pattern.get('percentage', 0):.0f}% of the time",
            supporting_data=pattern
        )
        db.add(insight)
        db.flush()
        stored_ids["patterns"].append(insight.id)
    
    # Store anomalies
    for anomaly in insights_dict.get("anomalies", []):
        insight = Insight(
            data_table_id=table_id,
            user_id=user_id,
            insight_type="anomaly",
            metric=anomaly["metric"],
            value=str(anomaly["value"]),
            confidence=0.85,
            description=anomaly.get("reason"),
            supporting_data=anomaly
        )
        db.add(insight)
        db.flush()
        stored_ids["anomalies"].append(insight.id)
    
    # Store trends
    for trend in insights_dict.get("trends", []):
        insight = Insight(
            data_table_id=table_id,
            user_id=user_id,
            insight_type="trend",
            metric=trend["metric"],
            value=trend.get("data_type"),
            confidence=0.90,
            description=f"Detected as {trend.get('data_type')} column",
            supporting_data=trend
        )
        db.add(insight)
        db.flush()
        stored_ids["trends"].append(insight.id)
    
    db.commit()
    
    return stored_ids
