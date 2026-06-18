from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ticket, TicketAnalysis
from app.schemas import TicketAnalysisRead, TicketCreate, TicketRead, TicketStatusUpdate
from app.services import analyze_ticket

DbSession = Annotated[Session, Depends(get_db)]


def register_ticket_routes(app: FastAPI) -> None:
    @app.post(
        "/api/tickets",
        response_model=TicketRead,
        status_code=status.HTTP_201_CREATED,
        tags=["tickets"],
    )
    async def create_ticket(ticket_in: TicketCreate, db: DbSession) -> Ticket:
        ticket = Ticket(**ticket_in.model_dump())
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket

    @app.get("/api/tickets", response_model=list[TicketRead], tags=["tickets"])
    async def list_tickets(db: DbSession) -> list[Ticket]:
        return list(db.scalars(select(Ticket).order_by(Ticket.id)).all())

    @app.get("/api/tickets/{ticket_id}", response_model=TicketRead, tags=["tickets"])
    async def get_ticket(ticket_id: int, db: DbSession) -> Ticket:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        return ticket

    @app.patch("/api/tickets/{ticket_id}/status", response_model=TicketRead, tags=["tickets"])
    async def update_ticket_status(
        ticket_id: int,
        ticket_in: TicketStatusUpdate,
        db: DbSession,
    ) -> Ticket:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

        ticket.status = ticket_in.status
        db.commit()
        db.refresh(ticket)
        return ticket

    @app.post(
        "/api/tickets/{ticket_id}/analyze",
        response_model=TicketAnalysisRead,
        tags=["tickets"],
    )
    async def analyze_ticket_endpoint(ticket_id: int, db: DbSession) -> TicketAnalysis:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

        result = analyze_ticket(ticket.title, ticket.description)
        values = {
            "summary": result.summary,
            "category": result.category,
            "priority": result.priority,
            "sentiment": result.sentiment,
            "recommended_action": result.recommended_action,
        }

        analysis = db.scalar(
            select(TicketAnalysis).where(TicketAnalysis.ticket_id == ticket.id)
        )
        if analysis is None:
            analysis = TicketAnalysis(ticket_id=ticket.id, **values)
            db.add(analysis)
        else:
            for field, value in values.items():
                setattr(analysis, field, value)

        db.commit()
        db.refresh(analysis)
        return analysis
