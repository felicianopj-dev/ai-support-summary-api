import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app


async def get(path: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_health_check() -> None:
    response = asyncio.run(get("/health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_page() -> None:
    response = asyncio.run(get("/"))

    assert response.status_code == 200
    assert "AI Support Summary API" in response.text
