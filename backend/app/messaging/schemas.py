from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    display_name: str


# ─── Message ──────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    recipient_id: int
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sender_id: int | None
    sender: UserSummary | None
    recipient_id: int
    recipient: UserSummary
    subject: str
    body: str
    message_type: str
    is_read: bool
    is_archived: bool
    related_entity: str | None
    related_entity_id: int | None
    created_at: datetime


class MessageUpdate(BaseModel):
    is_read: bool | None = None
    is_archived: bool | None = None


class UnreadCount(BaseModel):
    count: int


# ─── Auto Message Rules ──────────────────────────────────────────

class AutoMessageRuleCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    subject_template: str = Field(..., min_length=1, max_length=200)
    body_template: str = Field(..., min_length=1)
    is_active: bool = True
    send_to: str = Field(default="affected_user", pattern=r"^(affected_user|all_users|all_admins)$")


class AutoMessageRuleUpdate(BaseModel):
    subject_template: str | None = Field(default=None, min_length=1, max_length=200)
    body_template: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None
    send_to: str | None = Field(default=None, pattern=r"^(affected_user|all_users|all_admins)$")


class AutoMessageRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_type: str
    subject_template: str
    body_template: str
    is_active: bool
    send_to: str
    created_at: datetime

