from app.services.base import AnalysisResult

_RULES = (
    (
        "refund",
        "billing",
        "high",
        "Review the transaction and process or explain the refund.",
    ),
    (
        "payment",
        "billing",
        "high",
        "Check the payment status and gateway response, then update the customer.",
    ),
    (
        "webhook",
        "integration",
        "high",
        "Inspect webhook delivery logs and retry the failed event.",
    ),
    (
        "login",
        "authentication",
        "medium",
        "Verify the account and help the customer restore access.",
    ),
)

_NEGATIVE_WORDS = (
    "cannot",
    "can't",
    "failed",
    "failure",
    "error",
    "issue",
    "problem",
    "never",
    "missing",
    "declined",
    "broken",
    "stuck",
    "refund",
)
_POSITIVE_WORDS = ("thanks", "thank you", "great", "resolved", "working")


def analyze_ticket(title: str, description: str) -> AnalysisResult:
    text = f"{title} {description}".lower()

    matched_keyword = None
    category = "general"
    priority = "low"
    recommended_action = "Review the ticket and contact the customer for more details."

    for keyword, rule_category, rule_priority, action in _RULES:
        if keyword in text:
            matched_keyword = keyword
            category = rule_category
            priority = rule_priority
            recommended_action = action
            break

    if any(word in text for word in _NEGATIVE_WORDS):
        sentiment = "negative"
    elif any(word in text for word in _POSITIVE_WORDS):
        sentiment = "positive"
    else:
        sentiment = "neutral"

    subject = matched_keyword or "support"
    summary = f"Customer reports a {subject} issue: {title.strip()}."

    return AnalysisResult(
        summary=summary,
        category=category,
        priority=priority,
        sentiment=sentiment,
        recommended_action=recommended_action,
    )
