from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant"]


class Message(BaseModel):
    role: Role
    content: str


class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1, description="对话历史，按时间顺序")
    temperature: float = Field(0.3, ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    reply: str
    model: str
    cards: list[dict[str, Any]] = Field(default_factory=list)
    trip_id: str = ""


class HealthResponse(BaseModel):
    status: str
    model: str
    api_key_configured: bool
    assistant: str
    tool_mode: str
