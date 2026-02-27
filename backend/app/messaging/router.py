from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import AdminUser, CurrentUser, DBSession
from app.messaging import service
from app.messaging.schemas import (
    AutoMessageRuleCreate,
    AutoMessageRuleRead,
    AutoMessageRuleUpdate,
    MessageCreate,
    MessageRead,
    MessageUpdate,
    UnreadCount,
)

message_router = APIRouter(prefix="/api/messages", tags=["messaging"])
rule_router = APIRouter(prefix="/api/messages/rules", tags=["messaging"])


# ─── Messages ─────────────────────────────────────────────────────

@message_router.get("/", response_model=list[MessageRead])
async def list_messages(
    user: CurrentUser,
    db: DBSession,
    include_archived: bool = Query(default=False),
    unread_only: bool = Query(default=False),
):
    """Get all messages for the current user."""
    return await service.get_messages_for_user(
        db, user.id, include_archived=include_archived, unread_only=unread_only
    )


@message_router.get("/sent", response_model=list[MessageRead])
async def list_sent_messages(user: CurrentUser, db: DBSession):
    """Get all messages sent by the current user."""
    return await service.get_sent_messages(db, user.id)


@message_router.get("/unread-count", response_model=UnreadCount)
async def get_unread_count(user: CurrentUser, db: DBSession):
    """Get count of unread messages."""
    count = await service.get_unread_count(db, user.id)
    return UnreadCount(count=count)


@message_router.get("/{message_id}", response_model=MessageRead)
async def get_message(message_id: int, user: CurrentUser, db: DBSession):
    """Get a specific message. Auto-marks as read."""
    msg = await service.get_message_by_id(db, message_id)
    if msg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if msg.recipient_id != user.id and msg.sender_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your message")
    # Auto-mark as read when recipient opens it
    if msg.recipient_id == user.id and not msg.is_read:
        await service.mark_as_read(db, msg.id)
        msg.is_read = True
    return msg


@message_router.post("/", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def send_message(data: MessageCreate, user: CurrentUser, db: DBSession):
    """Send a message to another user."""
    if data.recipient_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send a message to yourself",
        )
    msg = await service.create_message(db, user.id, data)
    return msg


@message_router.post("/broadcast", response_model=list[MessageRead], status_code=status.HTTP_201_CREATED)
async def broadcast_message(data: MessageCreate, admin: AdminUser, db: DBSession):
    """Admin sends a message to all active users."""
    messages = await service.broadcast_system_message(
        db, data.subject, data.body, message_type="broadcast"
    )
    return messages


@message_router.patch("/{message_id}", response_model=MessageRead)
async def update_message(message_id: int, data: MessageUpdate, user: CurrentUser, db: DBSession):
    """Mark message as read/archived."""
    msg = await service.get_message_by_id(db, message_id)
    if msg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if msg.recipient_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your message")
    if data.is_read is not None:
        if data.is_read:
            await service.mark_as_read(db, msg.id)
        msg.is_read = data.is_read if data.is_read is not None else msg.is_read
    if data.is_archived is not None:
        if data.is_archived:
            await service.archive_message(db, msg.id)
        msg.is_archived = data.is_archived
    await db.refresh(msg)
    return msg


@message_router.post("/mark-all-read", response_model=UnreadCount)
async def mark_all_read(user: CurrentUser, db: DBSession):
    """Mark all messages as read."""
    await service.mark_all_as_read(db, user.id)
    count = await service.get_unread_count(db, user.id)
    return UnreadCount(count=count)


@message_router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(message_id: int, user: CurrentUser, db: DBSession):
    """Delete a message (only recipient or admin)."""
    msg = await service.get_message_by_id(db, message_id)
    if msg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if msg.recipient_id != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your message")
    await service.delete_message(db, msg)


# ─── Auto Message Rules (Admin) ───────────────────────────────────

@rule_router.get("/", response_model=list[AutoMessageRuleRead])
async def list_rules(admin: AdminUser, db: DBSession):
    return await service.get_all_rules(db)


@rule_router.post("/", response_model=AutoMessageRuleRead, status_code=status.HTTP_201_CREATED)
async def create_rule(data: AutoMessageRuleCreate, admin: AdminUser, db: DBSession):
    return await service.create_rule(db, data)


@rule_router.patch("/{rule_id}", response_model=AutoMessageRuleRead)
async def update_rule(rule_id: int, data: AutoMessageRuleUpdate, admin: AdminUser, db: DBSession):
    rules = await service.get_all_rules(db)
    rule = next((r for r in rules if r.id == rule_id), None)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return await service.update_rule(db, rule, data)


@rule_router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: int, admin: AdminUser, db: DBSession):
    rules = await service.get_all_rules(db)
    rule = next((r for r in rules if r.id == rule_id), None)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    await service.delete_rule(db, rule)

