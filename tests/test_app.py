import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import TicketAnalysis
from app.services import analyze_ticket


@pytest.fixture()
def test_db() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    async def override_get_db() -> AsyncGenerator[Session, None]:
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestingSessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


async def request(method: str, path: str, **kwargs) -> Response:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def test_health_check(test_db: None) -> None:
    response = asyncio.run(request("GET", "/health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_page(test_db: None) -> None:
    response = asyncio.run(request("GET", "/"))

    assert response.status_code == 200
    assert "AI Support Summary API" in response.text


def test_create_ticket(test_db: None) -> None:
    response = asyncio.run(
        request(
            "POST",
            "/api/tickets",
            json={
                "customer_name": "Ada Lovelace",
                "customer_email": "ada@example.com",
                "title": "Cannot sign in",
                "description": "Password reset email never arrives.",
            },
        )
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["customer_name"] == "Ada Lovelace"
    assert body["customer_email"] == "ada@example.com"
    assert body["title"] == "Cannot sign in"
    assert body["description"] == "Password reset email never arrives."
    assert body["status"] == "open"
    assert body["created_at"]
    assert body["updated_at"]


def test_list_tickets(test_db: None) -> None:
    asyncio.run(
        request(
            "POST",
            "/api/tickets",
            json={
                "customer_name": "Ada Lovelace",
                "customer_email": "ada@example.com",
                "title": "Cannot sign in",
                "description": "Password reset email never arrives.",
            },
        )
    )
    asyncio.run(
        request(
            "POST",
            "/api/tickets",
            json={
                "customer_name": "Grace Hopper",
                "customer_email": "grace@example.com",
                "title": "Export failed",
                "description": "CSV export returned a 500 response.",
                "status": "triaged",
            },
        )
    )

    response = asyncio.run(request("GET", "/api/tickets"))

    assert response.status_code == 200
    assert [ticket["title"] for ticket in response.json()] == ["Cannot sign in", "Export failed"]


def test_get_ticket(test_db: None) -> None:
    create_response = asyncio.run(
        request(
            "POST",
            "/api/tickets",
            json={
                "customer_name": "Ada Lovelace",
                "customer_email": "ada@example.com",
                "title": "Cannot sign in",
                "description": "Password reset email never arrives.",
            },
        )
    )

    response = asyncio.run(request("GET", f"/api/tickets/{create_response.json()['id']}"))

    assert response.status_code == 200
    assert response.json()["title"] == "Cannot sign in"


def test_update_ticket_status(test_db: None) -> None:
    create_response = asyncio.run(
        request(
            "POST",
            "/api/tickets",
            json={
                "customer_name": "Ada Lovelace",
                "customer_email": "ada@example.com",
                "title": "Cannot sign in",
                "description": "Password reset email never arrives.",
            },
        )
    )

    response = asyncio.run(
        request(
            "PATCH",
            f"/api/tickets/{create_response.json()['id']}/status",
            json={"status": "resolved"},
        )
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


def test_get_ticket_returns_404(test_db: None) -> None:
    response = asyncio.run(request("GET", "/api/tickets/404"))

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


@pytest.mark.parametrize(
    ("keyword", "category", "priority"),
    [
        ("payment", "billing", "high"),
        ("webhook", "integration", "high"),
        ("login", "authentication", "medium"),
        ("refund", "billing", "high"),
    ],
)
def test_mock_ai_uses_deterministic_keyword_rules(
    keyword: str,
    category: str,
    priority: str,
) -> None:
    first = analyze_ticket(f"{keyword.title()} problem", f"The {keyword} failed.")
    second = analyze_ticket(f"{keyword.title()} problem", f"The {keyword} failed.")

    assert first == second
    assert first.category == category
    assert first.priority == priority
    assert first.sentiment == "negative"


def test_analyze_ticket_saves_analysis(
    test_db: sessionmaker[Session],
) -> None:
    create_response = asyncio.run(
        request(
            "POST",
            "/api/tickets",
            json={
                "customer_name": "Grace Hopper",
                "customer_email": "grace@example.com",
                "title": "Webhook delivery failed",
                "description": "Our webhook never arrives.",
            },
        )
    )
    ticket_id = create_response.json()["id"]

    response = asyncio.run(request("POST", f"/api/tickets/{ticket_id}/analyze"))

    assert response.status_code == 200
    assert response.json() == {
        "summary": "Customer reports a webhook issue: Webhook delivery failed.",
        "category": "integration",
        "priority": "high",
        "sentiment": "negative",
        "recommended_action": "Inspect webhook delivery logs and retry the failed event.",
    }

    with test_db() as db:
        saved = db.query(TicketAnalysis).filter_by(ticket_id=ticket_id).one()
        assert saved.summary == response.json()["summary"]
        assert saved.category == "integration"


def test_reanalyze_ticket_updates_single_saved_analysis(
    test_db: sessionmaker[Session],
) -> None:
    create_response = asyncio.run(
        request(
            "POST",
            "/api/tickets",
            json={
                "customer_name": "Ada Lovelace",
                "customer_email": "ada@example.com",
                "title": "Login problem",
                "description": "I cannot login.",
            },
        )
    )
    ticket_id = create_response.json()["id"]

    first = asyncio.run(request("POST", f"/api/tickets/{ticket_id}/analyze"))
    second = asyncio.run(request("POST", f"/api/tickets/{ticket_id}/analyze"))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    with test_db() as db:
        assert db.query(TicketAnalysis).filter_by(ticket_id=ticket_id).count() == 1


def test_analyze_ticket_returns_404(test_db: None) -> None:
    response = asyncio.run(request("POST", "/api/tickets/404/analyze"))

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}
