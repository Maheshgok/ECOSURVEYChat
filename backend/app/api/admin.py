"""Admin analytics endpoints"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/insights")
async def get_insights(start: str, end: str):
    """Placeholder: Get analytics insights - Phase 8 implementation"""
    return {"start": start, "end": end, "message": "Insights - Phase 8 implementation"}


@router.get("/top_questions")
async def get_top_questions(start: str, end: str):
    """Placeholder: Get top questions - Phase 8 implementation"""
    return {"start": start, "end": end, "message": "Top questions - Phase 8 implementation"}
