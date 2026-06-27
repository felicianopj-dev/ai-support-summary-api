from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import InsightsRead
from app.services.insights import compute_insights

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/api", tags=["insights"])


@router.get("/insights", response_model=InsightsRead)
def get_insights(db: DbSession) -> InsightsRead:
    return compute_insights(db)
