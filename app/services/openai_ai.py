import json

import openai

from app.config import settings
from app.services.mock_ai import MockAnalysis

_SYSTEM_PROMPT = """\
You are a support ticket analyst. Given a ticket title and description, return a JSON object with exactly these fields:
- summary: one sentence summarising the customer's issue
- category: one of "billing", "authentication", "integration", "general"
- priority: one of "high", "medium", "low"
- sentiment: one of "positive", "negative", "neutral"
- recommended_action: one sentence describing the next step for the support agent
"""


def analyze_ticket(title: str, description: str) -> MockAnalysis:
    client = openai.OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Title: {title}\n\nDescription: {description}"},
        ],
    )
    data = json.loads(response.choices[0].message.content)
    return MockAnalysis(
        summary=data["summary"],
        category=data["category"],
        priority=data["priority"],
        sentiment=data["sentiment"],
        recommended_action=data["recommended_action"],
    )
