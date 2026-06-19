from app.config import settings
from app.services.mock_ai import MockAnalysis, analyze_ticket as _mock_analyze


def analyze_ticket(title: str, description: str) -> MockAnalysis:
    if settings.openai_api_key:
        from app.services.openai_ai import analyze_ticket as _openai_analyze
        return _openai_analyze(title, description)
    return _mock_analyze(title, description)


__all__ = ["analyze_ticket"]
