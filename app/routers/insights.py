from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ticket, TicketAnalysis
from app.schemas import CategoryCount, InsightsRead, TicketRead

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/api", tags=["insights"])


@router.get("/insights", response_model=InsightsRead)
async def get_insights(db: DbSession) -> InsightsRead:
    total = db.scalar(select(func.count()).select_from(Ticket)) or 0
    open_count = db.scalar(select(func.count()).where(Ticket.status == "open")) or 0
    analyzed = db.scalar(select(func.count()).select_from(TicketAnalysis)) or 0
    high_priority = (
        db.scalar(select(func.count()).where(TicketAnalysis.priority == "high")) or 0
    )

    top_cats = db.execute(
        select(TicketAnalysis.category, func.count().label("n"))
        .group_by(TicketAnalysis.category)
        .order_by(desc("n"))
        .limit(3)
    ).all()

    recent_high = list(
        db.scalars(
            select(Ticket)
            .join(TicketAnalysis)
            .where(TicketAnalysis.priority == "high")
            .order_by(desc(Ticket.created_at))
            .limit(5)
        )
    )

    return InsightsRead(
        total_tickets=total,
        open_tickets=open_count,
        analyzed_tickets=analyzed,
        high_priority_tickets=high_priority,
        top_categories=[CategoryCount(category=row.category, count=row.n) for row in top_cats],
        recent_high_priority_tickets=[TicketRead.model_validate(t) for t in recent_high],
    )
