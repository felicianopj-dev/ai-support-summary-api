from app.config import settings
from app.routers import register_insights_routes, register_page_routes, register_ticket_routes
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    register_ticket_routes(app)
    register_insights_routes(app)
    register_page_routes(app)

    @app.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
