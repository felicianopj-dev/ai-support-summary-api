from app.config import settings
from app.routers import insights_router, pages_router, tickets_router
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(tickets_router)
    app.include_router(insights_router)
    app.include_router(pages_router)

    @app.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
