from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import TicketAnalysis
from app.services import analyze_ticket, gemini_ai
from app.services.base import AnalysisResult


@pytest.fixture()
def test_db() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
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


async def test_health_check(test_db: None) -> None:
    response = await request("GET", "/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_home_page(test_db: None) -> None:
    response = await request("GET", "/")

    assert response.status_code == 200
    assert "Dashboard" in response.text


async def test_create_ticket(test_db: None) -> None:
    response = await request(
        "POST",
        "/api/tickets",
        json={
            "customer_name": "Ada Lovelace",
            "customer_email": "ada@example.com",
            "title": "Cannot sign in",
            "description": "Password reset email never arrives.",
        },
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


async def test_list_tickets(test_db: None) -> None:
    await request(
        "POST",
        "/api/tickets",
        json={
            "customer_name": "Ada Lovelace",
            "customer_email": "ada@example.com",
            "title": "Cannot sign in",
            "description": "Password reset email never arrives.",
        },
    )
    await request(
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

    response = await request("GET", "/api/tickets")

    assert response.status_code == 200
    assert [ticket["title"] for ticket in response.json()] == ["Cannot sign in", "Export failed"]


async def test_get_ticket(test_db: None) -> None:
    create_response = await request(
        "POST",
        "/api/tickets",
        json={
            "customer_name": "Ada Lovelace",
            "customer_email": "ada@example.com",
            "title": "Cannot sign in",
            "description": "Password reset email never arrives.",
        },
    )

    response = await request("GET", f"/api/tickets/{create_response.json()['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Cannot sign in"


async def test_update_ticket_status(test_db: None) -> None:
    create_response = await request(
        "POST",
        "/api/tickets",
        json={
            "customer_name": "Ada Lovelace",
            "customer_email": "ada@example.com",
            "title": "Cannot sign in",
            "description": "Password reset email never arrives.",
        },
    )

    response = await request(
        "PATCH",
        f"/api/tickets/{create_response.json()['id']}/status",
        json={"status": "resolved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


async def test_get_ticket_returns_404(test_db: None) -> None:
    response = await request("GET", "/api/tickets/404")

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


# --- gemini hardening ---


def test_gemini_falls_back_to_mock_on_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(title: str, description: str) -> AnalysisResult:
        raise RuntimeError("network down")

    monkeypatch.setattr(gemini_ai, "_call_gemini", boom)

    result = gemini_ai.analyze_ticket("Login problem", "I cannot login.")

    assert result == gemini_ai._mock_analyze("Login problem", "I cannot login.")


def test_gemini_falls_back_when_response_is_out_of_enum(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeResponse:
        text = (
            '{"summary": "x", "category": "not-a-category", "priority": "high", '
            '"sentiment": "negative", "recommended_action": "y"}'
        )

    class _FakeModels:
        def generate_content(self, *args: object, **kwargs: object) -> _FakeResponse:
            return _FakeResponse()

    class _FakeClient:
        models = _FakeModels()

    monkeypatch.setattr(gemini_ai, "_get_client", lambda: _FakeClient())

    result = gemini_ai.analyze_ticket("Login problem", "I cannot login.")

    # Invalid enum value is rejected, so we degrade to the deterministic mock instead of 500ing.
    assert result == gemini_ai._mock_analyze("Login problem", "I cannot login.")


async def test_analyze_ticket_saves_analysis(
    test_db: sessionmaker[Session],
) -> None:
    create_response = await request(
        "POST",
        "/api/tickets",
        json={
            "customer_name": "Grace Hopper",
            "customer_email": "grace@example.com",
            "title": "Webhook delivery failed",
            "description": "Our webhook never arrives.",
        },
    )
    ticket_id = create_response.json()["id"]

    response = await request("POST", f"/api/tickets/{ticket_id}/analyze")

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


async def test_reanalyze_ticket_updates_single_saved_analysis(
    test_db: sessionmaker[Session],
) -> None:
    create_response = await request(
        "POST",
        "/api/tickets",
        json={
            "customer_name": "Ada Lovelace",
            "customer_email": "ada@example.com",
            "title": "Login problem",
            "description": "I cannot login.",
        },
    )
    ticket_id = create_response.json()["id"]

    first = await request("POST", f"/api/tickets/{ticket_id}/analyze")
    second = await request("POST", f"/api/tickets/{ticket_id}/analyze")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    with test_db() as db:
        assert db.query(TicketAnalysis).filter_by(ticket_id=ticket_id).count() == 1


async def test_analyze_ticket_returns_404(test_db: None) -> None:
    response = await request("POST", "/api/tickets/404/analyze")

    assert response.status_code == 404
    assert response.json() == {"detail": "Ticket not found"}


# --- insights ---

_TICKET_ADA = {
    "customer_name": "Ada Lovelace",
    "customer_email": "ada@example.com",
    "title": "Payment failed",
    "description": "My payment was declined.",
}

_TICKET_GRACE = {
    "customer_name": "Grace Hopper",
    "customer_email": "grace@example.com",
    "title": "Webhook not received",
    "description": "Our webhook never arrives.",
}

_TICKET_ALAN = {
    "customer_name": "Alan Turing",
    "customer_email": "alan@example.com",
    "title": "Login issue",
    "description": "Cannot login to my account.",
}


async def test_insights_empty(test_db: None) -> None:
    response = await request("GET", "/api/insights")

    assert response.status_code == 200
    body = response.json()
    assert body["total_tickets"] == 0
    assert body["open_tickets"] == 0
    assert body["analyzed_tickets"] == 0
    assert body["high_priority_tickets"] == 0
    assert body["top_categories"] == []
    assert body["recent_high_priority_tickets"] == []


async def test_insights_counts(test_db: None) -> None:
    for payload in (_TICKET_ADA, _TICKET_GRACE, _TICKET_ALAN):
        await request("POST", "/api/tickets", json=payload)

    tickets = (await request("GET", "/api/tickets")).json()
    await request("POST", f"/api/tickets/{tickets[0]['id']}/analyze")
    await request("POST", f"/api/tickets/{tickets[1]['id']}/analyze")
    await request("PATCH", f"/api/tickets/{tickets[2]['id']}/status", json={"status": "resolved"})

    body = (await request("GET", "/api/insights")).json()

    assert body["total_tickets"] == 3
    assert body["open_tickets"] == 2
    assert body["analyzed_tickets"] == 2
    assert body["high_priority_tickets"] == 2


async def test_insights_top_categories(test_db: None) -> None:
    for payload in (_TICKET_ADA, _TICKET_GRACE, _TICKET_ALAN):
        r = await request("POST", "/api/tickets", json=payload)
        await request("POST", f"/api/tickets/{r.json()['id']}/analyze")

    body = (await request("GET", "/api/insights")).json()

    categories = [c["category"] for c in body["top_categories"]]
    assert "billing" in categories
    assert "integration" in categories
    assert "authentication" in categories


async def test_insights_recent_high_priority(test_db: None) -> None:
    r = await request("POST", "/api/tickets", json=_TICKET_ADA)
    ticket_id = r.json()["id"]
    await request("POST", f"/api/tickets/{ticket_id}/analyze")

    body = (await request("GET", "/api/insights")).json()

    assert len(body["recent_high_priority_tickets"]) == 1
    assert body["recent_high_priority_tickets"][0]["id"] == ticket_id
