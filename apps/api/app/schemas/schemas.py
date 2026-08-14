from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    organization_id: UUID
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ConnectionResponse(BaseModel):
    id: UUID
    integration_type: str
    status: str
    metadata_json: Optional[dict] = None
    last_synced_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    title: Optional[str] = None


class ChatSessionUpdate(BaseModel):
    title: str


class ChatSessionResponse(BaseModel):
    id: UUID
    title: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SessionSummaryResponse(ChatSessionResponse):
    """A session with enough context to render an investigation card:
    the question asked, the tools that executed, and a result preview."""

    message_count: int = 0
    question: Optional[str] = None
    tools: List[dict] = []
    result: Optional[str] = None


class MessageCreate(BaseModel):
    content: str

    def __init__(self, **data):
        super().__init__(**data)
        if len(self.content) > 10000:
            raise ValueError("Message content must be 10,000 characters or fewer")
        if not self.content.strip():
            raise ValueError("Message content cannot be empty")


class SourceRef(BaseModel):
    type: str
    url: str
    title: str
    detail: Optional[str] = None


class ToolActivity(BaseModel):
    tool: str
    status: str
    description: str
    duration_ms: Optional[float] = None


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    sources: Optional[List[SourceRef]] = None
    tool_calls: Optional[List[ToolActivity]] = Field(
        default=None, validation_alias="tool_activities"
    )
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionWithMessages(ChatSessionResponse):
    messages: List[MessageResponse] = []


class ToolCallResponse(BaseModel):
    id: UUID
    tool_name: str
    arguments_json: dict
    status: str
    result_json: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ToolExecutionResponse(BaseModel):
    tool: str
    status: str
    duration_ms: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnalyticsResponse(BaseModel):
    total_queries: int
    successful_queries: int
    failed_queries: int
    avg_latency_ms: float
    avg_tool_calls_per_query: float
    total_tokens: int
    estimated_cost: float
    most_used_tools: List[dict]
    investigations: int
    tool_calls: int
    tool_success_rate: Optional[float] = None
    median_tool_latency_ms: Optional[float] = None
    recent_tool_executions: List[ToolExecutionResponse] = []


class GitHubConnectRequest(BaseModel):
    token: Optional[str] = None


class SlackConnectRequest(BaseModel):
    code: Optional[str] = None


class HubSpotConnectRequest(BaseModel):
    code: Optional[str] = None


class PostgresConnectRequest(BaseModel):
    host: str
    port: int = 5432
    database: str
    username: str
    password: str


class WriteConfirmationRequest(BaseModel):
    tool_name: str
    arguments: dict
    confirmed: bool
