from typing import Annotated, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant"]


class Message(BaseModel):
    role: Role
    content: str


class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1, description="对话历史，按时间顺序")
    temperature: float = Field(0.3, ge=0.0, le=1.0)


class CardBase(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    trip_id: str | None
    title: str
    data_mode: str | None
    realtime: bool
    bookable: bool
    booking_url: str
    cta_label: str
    notice: str | None


class TransportCard(CardBase):
    type: Literal["transport_offer"]
    transport_type: Literal["train", "flight"]
    service_label: str
    origin: str
    destination: str
    departure_date: str
    return_date: str
    departure_time: str
    arrival_time: str
    seat_class: str
    remaining_inventory: int
    inventory_status: str
    travelers: int
    unit_price_yuan: float
    total_price_yuan: float
    original_price_yuan: float | None
    duration_minutes: int
    recommended: bool
    flight_type: str


class HotelCard(CardBase):
    type: Literal["hotel_offer"]
    location: str
    tier: str
    checkin_date: str
    checkout_date: str
    rooms: int
    nights: int
    rating: float
    remaining_inventory: int
    inventory_status: str
    unit_price_yuan: float
    total_price_yuan: float
    original_price_yuan: float | None
    room_type: str
    room_size: str
    bed_type: str
    capacity: int
    distance_km: float | None
    cancel_policy: str
    services: list[str]
    image_count: int
    image_url: str
    is_recommended: bool
    recommended_reason: str


class TicketCard(CardBase):
    type: Literal["ticket_offer"]
    attraction_name: str
    category: str
    destination: str
    travelers: int
    unit_price_yuan: float
    total_price_yuan: float
    remaining_inventory: int
    inventory_status: str
    duration_hours: float
    opening_hours: str
    image_url: str
    is_recommended: bool
    recommended_reason: str


Card = Annotated[TransportCard | HotelCard | TicketCard, Field(discriminator="type")]


class ChatResponse(BaseModel):
    reply: str
    model: str
    cards: list[Card] = Field(default_factory=list)
    trip_id: str = ""


class HealthResponse(BaseModel):
    status: str
    model: str
    api_key_configured: bool
    assistant: str
    tool_mode: str
