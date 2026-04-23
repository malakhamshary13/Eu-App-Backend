from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from modules.recommendations.service import RecommendationService
from modules.recommendations.schemas import RecommendationResponseSchema
from core.auth import get_current_user

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"]
)


@router.get("/today", response_model=RecommendationResponseSchema)
def get_today_recommendation(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    service = RecommendationService(db)
    return service.get_recommendation_for_user(current_user)