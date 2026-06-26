import json
import logging

import google.generativeai as genai
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.schemas import AnalysisCategory, AnalysisPriority, AnalysisSentiment
from app.services.base import AnalysisResult
from app.services.mock_ai import analyze_ticket as _mock_analyze

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_SECONDS = 15

_PROMPT_TEMPLATE = """\
You are a support ticket analyst. Given a ticket title and description, return a JSON \
object with exactly these fields:
- summary: one sentence summarising the customer's issue
- category: one of "billing", "authentication", "integration", "general"
- priority: one of "high", "medium", "low"
- sentiment: one of "positive", "negative", "neutral"
- recommended_action: one sentence describing the next step for the support agent

Title: {title}

Description: {description}"""


class _GeminiAnalysis(BaseModel):
    """Validates the model's JSON output, rejecting values outside the allowed enums."""

    summary: str
    category: AnalysisCategory
    priority: AnalysisPriority
    sentiment: AnalysisSentiment
    recommended_action: str


def analyze_ticket(title: str, description: str) -> AnalysisResult:
    try:
        return _call_gemini(title, description)
    except Exception:
        # Any failure (network, timeout, malformed JSON, out-of-enum value) must not take
        # the endpoint down — degrade gracefully to the deterministic mock analyser.
        logger.warning("Gemini analysis failed; falling back to mock analyser.", exc_info=True)
        return _mock_analyze(title, description)


def _call_gemini(title: str, description: str) -> AnalysisResult:
    genai.configure(api_key=settings.gemini_api_key)  # type: ignore[attr-defined]
    model = genai.GenerativeModel("gemini-1.5-flash")  # type: ignore[attr-defined]
    response = model.generate_content(
        _PROMPT_TEMPLATE.format(title=title, description=description),
        generation_config=genai.types.GenerationConfig(response_mime_type="application/json"),
        request_options={"timeout": _REQUEST_TIMEOUT_SECONDS},
    )

    try:
        data = json.loads(response.text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("Gemini returned a non-JSON response.") from exc

    try:
        analysis = _GeminiAnalysis.model_validate(data)
    except ValidationError as exc:
        raise ValueError("Gemini response did not match the expected schema.") from exc

    return AnalysisResult(
        summary=analysis.summary,
        category=analysis.category,
        priority=analysis.priority,
        sentiment=analysis.sentiment,
        recommended_action=analysis.recommended_action,
    )
