from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisResult:
    summary: str
    category: str
    priority: str
    sentiment: str
    recommended_action: str
