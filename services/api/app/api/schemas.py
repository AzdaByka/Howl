"""Pydantic request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    display_name: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    user: UserResponse


class CommunityCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CommunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime
    updated_at: datetime


class CommunitySummary(CommunityResponse):
    member_count: int


class ChannelCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    community_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class InviteResponse(BaseModel):
    id: UUID
    community_id: UUID
    token: str
    expires_at: datetime


class InvitePreviewResponse(BaseModel):
    community_id: UUID
    community_name: str
    expires_at: datetime
    is_expired: bool


class MediaParticipant(BaseModel):
    user_id: UUID
    display_name: str
    is_muted: bool = False


class VoiceSessionResponse(BaseModel):
    session_id: str
    signaling_url: str
    media_token: str
    expires_at: datetime
    participants: list[MediaParticipant] = Field(default_factory=list)


class RealtimeEvent(BaseModel):
    type: str
    version: int = 1
    event_id: str
    occurred_at: datetime
    community_id: UUID | None = None
    channel_id: UUID | None = None
    payload: dict = Field(default_factory=dict)


class RealtimeSubscribe(BaseModel):
    type: str = "subscribe"
    community_id: UUID
    channel_id: UUID | None = None


class MediaEventRequest(BaseModel):
    event_id: str
    type: str
    occurred_at: datetime
    community_id: UUID
    channel_id: UUID
    session_id: str | None = None
    user_id: UUID | None = None
    payload: dict = Field(default_factory=dict)


class MediaSessionRequest(BaseModel):
    user_id: UUID
    community_id: UUID
    channel_id: UUID
    display_name: str
    max_participants: int
    idempotency_key: str


class MediaSessionResponse(BaseModel):
    session_id: str
    signaling_url: str
    media_token: str
    expires_at: datetime
    participants: list[MediaParticipant] = Field(default_factory=list)
