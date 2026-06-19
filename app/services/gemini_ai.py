import json

import google.generativeai as genai

from app.config import settings
from app.services.base import AnalysisResult

_PROMPT_TEMPLATE = """\
You are a support ticket analyst. Given a ticket title and description, return a JSON object with exactly these fields:
- summary: one sentence summarising the customer's issue
- category: one of "billing", "authentication", "integration", "general"
- priority: one of "high", "medium", "low"
- sentiment: one of "positive", "negative", "neutral"
- recommended_action: one sentence describing the next step for the support agent

Title: {title}

Description: {description}"""


def analyze_ticket(title: str, description: str) -> AnalysisResult:
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(
        _PROMPT_TEMPLATE.format(title=title, description=description),
        generation_config=genai.types.GenerationConfig(response_mime_type="application/json"),
    )
    data = json.loads(response.text)
    return AnalysisResult(
        summary=data["summary"],
        category=data["category"],
        priority=data["priority"],
        sentiment=data["sentiment"],
        recommended_action=data["recommended_action"],
    )
