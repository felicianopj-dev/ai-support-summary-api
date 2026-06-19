from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TicketCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=255)
    customer_email: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    status: str = Field(default="open", min_length=1, max_length=50)


class TicketStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    customer_email: str
    title: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class TicketAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary: str
    category: str
    priority: str
    sentiment: str
    recommended_action: str


class CategoryCount(BaseModel):
    category: str
    count: int


class InsightsRead(BaseModel):
    total_tickets: int
    open_tickets: int
    analyzed_tickets: int
    high_priority_tickets: int
    top_categories: list[CategoryCount]
    recent_high_priority_tickets: list[TicketRead]
