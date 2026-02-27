from datetime import datetime

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.messaging.models import AutoMessageRule, Message
from app.messaging.schemas import AutoMessageRuleCreate, AutoMessageRuleUpdate, MessageCreate


# ─── Messages ─────────────────────────────────────────────────────

async def get_messages_for_user(
    db: AsyncSession,
    user_id: int,
    include_archived: bool = False,
    unread_only: bool = False,
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.recipient_id == user_id)
        .order_by(Message.created_at.desc())
    )
    if not include_archived:
        stmt = stmt.where(Message.is_archived.is_(False))
    if unread_only:
        stmt = stmt.where(Message.is_read.is_(False))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_sent_messages(db: AsyncSession, user_id: int) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.sender_id == user_id)
        .order_by(Message.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_message_by_id(db: AsyncSession, message_id: int) -> Message | None:
    result = await db.execute(select(Message).where(Message.id == message_id))
    return result.scalar_one_or_none()


async def get_unread_count(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count(Message.id))
        .where(Message.recipient_id == user_id)
        .where(Message.is_read.is_(False))
        .where(Message.is_archived.is_(False))
    )
    return result.scalar() or 0


async def create_message(
    db: AsyncSession,
    sender_id: int | None,
    data: MessageCreate,
    message_type: str = "manual",
    related_entity: str | None = None,
    related_entity_id: int | None = None,
) -> Message:
    msg = Message(
        sender_id=sender_id,
        recipient_id=data.recipient_id,
        subject=data.subject,
        body=data.body,
        message_type=message_type,
        related_entity=related_entity,
        related_entity_id=related_entity_id,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


async def send_system_message(
    db: AsyncSession,
    recipient_id: int,
    subject: str,
    body: str,
    message_type: str = "system",
    related_entity: str | None = None,
    related_entity_id: int | None = None,
) -> Message:
    msg = Message(
        sender_id=None,
        recipient_id=recipient_id,
        subject=subject,
        body=body,
        message_type=message_type,
        related_entity=related_entity,
        related_entity_id=related_entity_id,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


async def broadcast_system_message(
    db: AsyncSession,
    subject: str,
    body: str,
    message_type: str = "system",
    to_admins_only: bool = False,
) -> list[Message]:
    """Send a system message to all active users (or admins only)."""
    stmt = select(User).where(User.is_active.is_(True))
    if to_admins_only:
        stmt = stmt.where(User.role == "admin")
    result = await db.execute(stmt)
    users = list(result.scalars().all())

    messages = []
    for user in users:
        msg = await send_system_message(db, user.id, subject, body, message_type)
        messages.append(msg)
    return messages


async def mark_as_read(db: AsyncSession, message_id: int) -> None:
    await db.execute(
        update(Message).where(Message.id == message_id).values(is_read=True)
    )
    await db.flush()


async def mark_all_as_read(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        update(Message)
        .where(Message.recipient_id == user_id)
        .where(Message.is_read.is_(False))
        .values(is_read=True)
    )
    await db.flush()
    return result.rowcount


async def archive_message(db: AsyncSession, message_id: int) -> None:
    await db.execute(
        update(Message).where(Message.id == message_id).values(is_archived=True)
    )
    await db.flush()


async def delete_message(db: AsyncSession, message: Message) -> None:
    await db.delete(message)
    await db.flush()


# ─── Auto Message Rules ──────────────────────────────────────────

async def get_all_rules(db: AsyncSession) -> list[AutoMessageRule]:
    result = await db.execute(select(AutoMessageRule).order_by(AutoMessageRule.event_type))
    return list(result.scalars().all())


async def get_rule_by_event(db: AsyncSession, event_type: str) -> AutoMessageRule | None:
    result = await db.execute(
        select(AutoMessageRule).where(AutoMessageRule.event_type == event_type)
    )
    return result.scalar_one_or_none()


async def create_rule(db: AsyncSession, data: AutoMessageRuleCreate) -> AutoMessageRule:
    rule = AutoMessageRule(**data.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


async def update_rule(db: AsyncSession, rule: AutoMessageRule, data: AutoMessageRuleUpdate) -> AutoMessageRule:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.flush()
    await db.refresh(rule)
    return rule


async def delete_rule(db: AsyncSession, rule: AutoMessageRule) -> None:
    await db.delete(rule)
    await db.flush()


# ─── Auto Message Trigger ─────────────────────────────────────────

async def trigger_auto_message(
    db: AsyncSession,
    event_type: str,
    context: dict,
    affected_user_id: int | None = None,
) -> list[Message]:
    """Trigger an auto-message based on event type.

    Context dict is used for template substitution:
      {user_name}, {amount}, {description}, etc.
    """
    rule = await get_rule_by_event(db, event_type)
    if rule is None or not rule.is_active:
        return []

    # Template substitution
    subject = rule.subject_template
    body = rule.body_template
    for key, value in context.items():
        subject = subject.replace(f"{{{key}}}", str(value))
        body = body.replace(f"{{{key}}}", str(value))

    messages = []

    if rule.send_to == "affected_user" and affected_user_id:
        msg = await send_system_message(
            db, affected_user_id, subject, body,
            message_type=f"auto:{event_type}",
        )
        messages.append(msg)

    elif rule.send_to == "all_users":
        msgs = await broadcast_system_message(db, subject, body, message_type=f"auto:{event_type}")
        messages.extend(msgs)

    elif rule.send_to == "all_admins":
        msgs = await broadcast_system_message(
            db, subject, body, message_type=f"auto:{event_type}", to_admins_only=True
        )
        messages.extend(msgs)

    return messages

