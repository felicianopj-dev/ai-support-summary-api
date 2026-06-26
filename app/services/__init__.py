from app.config import settings
from app.services.base import AnalysisResult
from app.services.mock_ai import analyze_ticket as _mock_analyze


def analyze_ticket(title: str, description: str) -> AnalysisResult:
    if settings.gemini_api_key:
        from app.services.gemini_ai import analyze_ticket as _gemini_analyze

        return _gemini_analyze(title, description)
    return _mock_analyze(title, description)


__all__ = ["analyze_ticket"]
