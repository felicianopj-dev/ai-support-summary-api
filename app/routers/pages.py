from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ticket, TicketAnalysis
from app.schemas import CategoryCount, InsightsRead, TicketRead

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: DbSession) -> HTMLResponse:
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
    insights = InsightsRead(
        total_tickets=total,
        open_tickets=open_count,
        analyzed_tickets=analyzed,
        high_priority_tickets=high_priority,
        top_categories=[CategoryCount(category=r.category, count=r.n) for r in top_cats],
        recent_high_priority_tickets=[TicketRead.model_validate(t) for t in recent_high],
    )
    return templates.TemplateResponse(
        request=request, name="index.html", context={"insights": insights}
    )


@router.get("/tickets", response_class=HTMLResponse)
def ticket_list(request: Request, db: DbSession) -> HTMLResponse:
    tickets = list(db.scalars(select(Ticket).order_by(Ticket.id)))
    return templates.TemplateResponse(
        request=request, name="tickets.html", context={"tickets": tickets}
    )


@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_detail(request: Request, ticket_id: int, db: DbSession) -> HTMLResponse:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return templates.TemplateResponse(
        request=request, name="ticket_detail.html", context={"ticket": ticket}
    )
