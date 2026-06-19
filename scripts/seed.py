"""Seed the database with realistic demo support tickets."""

import argparse
import sys
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Ticket, TicketAnalysis
from app.services.mock_ai import analyze_ticket

SEED_TICKETS = [
    {
        "customer_name": "Alice Mendes",
        "customer_email": "alice@acme.io",
        "title": "Payment failed after 3D Secure",
        "description": (
            "My payment was declined right after completing the 3DS verification step. "
            "The bank confirmed the charge never went through. Order #8821 is still pending."
        ),
        "status": "open",
    },
    {
        "customer_name": "Bruno Carvalho",
        "customer_email": "bruno@startup.dev",
        "title": "Webhook not received after order placement",
        "description": (
            "We set up the order.created webhook endpoint but it never fires. "
            "Checked our server logs — no incoming requests. Delivery logs show failed attempts."
        ),
        "status": "open",
    },
    {
        "customer_name": "Clara Souza",
        "customer_email": "clara@shop.com",
        "title": "Duplicate charge on Stripe subscription",
        "description": (
            "Our customer was billed twice this month for the same subscription plan. "
            "The payment history shows two identical charges on the same date."
        ),
        "status": "open",
    },
    {
        "customer_name": "Daniel Ferreira",
        "customer_email": "daniel@corp.net",
        "title": "Cannot login after password reset",
        "description": (
            "I reset my password using the email link but I still cannot login. "
            "The error says my credentials are invalid even with the new password."
        ),
        "status": "open",
    },
    {
        "customer_name": "Elena Ribeiro",
        "customer_email": "elena@client.org",
        "title": "Refund not processed after 7 days",
        "description": (
            "I requested a refund for my last order over a week ago and it never arrived. "
            "The support ticket said it was approved but the refund is missing from my account."
        ),
        "status": "open",
    },
    {
        "customer_name": "Felipe Nunes",
        "customer_email": "felipe@enterprise.co",
        "title": "Integration timeout on checkout",
        "description": (
            "Our checkout integration times out after ~30 seconds when processing large carts. "
            "Smaller orders go through fine. Started happening after last Friday's deployment."
        ),
        "status": "open",
    },
]


def seed(force: bool) -> None:
    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(Ticket)) or 0

        if count > 0 and not force:
            print(f"DB already has {count} ticket(s). Run with --force to reseed.")
            sys.exit(0)

        if force and count > 0:
            db.query(Ticket).delete()
            db.commit()
            print(f"Cleared {count} existing ticket(s).")

        for data in SEED_TICKETS:
            ticket = Ticket(**data)
            db.add(ticket)
            db.flush()

            result = analyze_ticket(ticket.title, ticket.description)
            db.add(
                TicketAnalysis(
                    ticket_id=ticket.id,
                    summary=result.summary,
                    category=result.category,
                    priority=result.priority,
                    sentiment=result.sentiment,
                    recommended_action=result.recommended_action,
                )
            )

        db.commit()
        print(f"Seeded {len(SEED_TICKETS)} tickets with AI analysis.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the database with demo support tickets.")
    parser.add_argument("--force", action="store_true", help="Clear existing tickets before seeding.")
    seed(parser.parse_args().force)
