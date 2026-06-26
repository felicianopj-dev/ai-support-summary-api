import json
import logging

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.schemas import AnalysisCategory, AnalysisPriority, AnalysisSentiment
from app.services.base import AnalysisResult
from app.services.mock_ai import analyze_ticket as _mock_analyze

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.0-flash"
_REQUEST_TIMEOUT_MS = 15_000

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


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def analyze_ticket(title: str, description: str) -> AnalysisResult:
    try:
        return _call_gemini(title, description)
    except Exception:
        # Any failure (network, timeout, malformed JSON, out-of-enum value) must not take
        # the endpoint down — degrade gracefully to the deterministic mock analyser.
        logger.warning("Gemini analysis failed; falling back to mock analyser.", exc_info=True)
        return _mock_analyze(title, description)


def _call_gemini(title: str, description: str) -> AnalysisResult:
    response = _get_client().models.generate_content(
        model=_MODEL,
        contents=_PROMPT_TEMPLATE.format(title=title, description=description),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            http_options=types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS),
        ),
    )

    if response.text is None:
        raise ValueError("Gemini returned an empty response.")

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
