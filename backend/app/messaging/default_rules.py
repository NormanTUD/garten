from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.models import AutoMessageRule

DEFAULT_RULES = [
    {
        "event_type": "payment_received",
        "subject_template": "Einzahlung erhalten: {amount}",
        "body_template": "{user_name} hat {amount} in die Gartenkasse eingezahlt ({payment_type}). Dein neuer Stand: {remaining}.",
        "send_to": "affected_user",
    },
    {
        "event_type": "expense_added",
        "subject_template": "Neue Ausgabe: {description}",
        "body_template": "{user_name} hat eine Ausgabe von {amount} eingetragen: {description}.",
        "send_to": "all_users",
    },
    {
        "event_type": "payment_confirmed",
        "subject_template": "Einzahlung bestätigt ✓",
        "body_template": "Deine Einzahlung von {amount} wurde vom Admin bestätigt.",
        "send_to": "affected_user",
    },
    {
        "event_type": "standing_order_skipped",
        "subject_template": "Dauerauftrag nicht gezahlt: {month}/{year}",
        "body_template": "Dein Dauerauftrag ({amount}/Monat) wurde für {month}/{year} als nicht gezahlt markiert. Grund: {reason}",
        "send_to": "affected_user",
    },
    {
        "event_type": "balance_reminder",
        "subject_template": "Erinnerung: Offener Betrag {remaining}",
        "body_template": "Du schuldest noch {remaining} für {year}. Bitte zahle zeitnah in die Gartenkasse ein.",
        "send_to": "affected_user",
    },
]


async def seed_default_rules(db: AsyncSession) -> None:
    """Insert default auto-message rules if they don't exist."""
    for rule_data in DEFAULT_RULES:
        existing = await db.execute(
            select(AutoMessageRule).where(
                AutoMessageRule.event_type == rule_data["event_type"]
            )
        )
        if existing.scalar_one_or_none() is None:
            rule = AutoMessageRule(**rule_data)
            db.add(rule)
    await db.flush()

