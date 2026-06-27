from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ticket
from app.services.insights import compute_insights

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: DbSession) -> HTMLResponse:
    insights = compute_insights(db)
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
