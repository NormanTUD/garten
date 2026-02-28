from datetime import datetime, date

from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.shopping.models import ShoppingItem
from app.shopping.schemas import ShoppingItemCreate, ShoppingItemUpdate, ShoppingItemPurchase
from app.finance.models import GardenExpense, MemberPayment


async def get_items(db: AsyncSession, include_purchased: bool = False):
    q = select(ShoppingItem).options(
        joinedload(ShoppingItem.added_by),
        joinedload(ShoppingItem.purchased_by),
    )
    if not include_purchased:
        # Zeige: alle offenen + alle recurring (auch wenn gekauft)
        q = q.where(
            (ShoppingItem.purchased == False) | (ShoppingItem.is_recurring == True)
        )
    q = q.order_by(ShoppingItem.is_recurring.desc(), desc(ShoppingItem.created_at))
    result = await db.execute(q)
    return result.scalars().unique().all()


async def get_item(db: AsyncSession, item_id: int):
    q = select(ShoppingItem).options(
        joinedload(ShoppingItem.added_by),
        joinedload(ShoppingItem.purchased_by),
    ).where(ShoppingItem.id == item_id)
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def create_item(db: AsyncSession, user_id: int, data: ShoppingItemCreate):
    item = ShoppingItem(
        title=data.title,
        notes=data.notes,
        quantity=data.quantity,
        category=data.category,
        is_recurring=data.is_recurring,
        added_by_id=user_id,
    )
    db.add(item)
    await db.flush()
    return item


async def update_item(db: AsyncSession, item_id: int, data: ShoppingItemUpdate):
    item = await get_item(db, item_id)
    if not item:
        return None
    if data.title is not None:
        item.title = data.title
    if data.notes is not None:
        item.notes = data.notes
    if data.quantity is not None:
        item.quantity = data.quantity
    if data.category is not None:
        item.category = data.category
    if data.is_recurring is not None:
        item.is_recurring = data.is_recurring
    await db.flush()
    return item


async def purchase_item(
    db: AsyncSession, item_id: int, user_id: int, data: ShoppingItemPurchase
):
    item = await get_item(db, item_id)
    if not item or item.purchased:
        return None

    # 1. Ausgabe erstellen (wird auf alle umgelegt)
    expense = GardenExpense(
        user_id=user_id,
        description=f"Einkauf: {item.title}" + (f" ({item.quantity})" if item.quantity else ""),
        amount_cents=data.cost_cents,
        category_id=None,
        expense_date=date.today(),
        is_shared=True,
        confirmed_by_admin=False,
        notes=data.notes or f"Aus Einkaufsliste von {item.added_by.display_name}",
    )
    db.add(expense)
    await db.flush()

    # 2. Gutschrift für den Käufer
    payment = MemberPayment(
        user_id=user_id,
        for_user_id=user_id,
        amount_cents=data.cost_cents,
        payment_type="expense_refund",
        description=f"Einkauf: {item.title}" + (f" ({item.quantity})" if item.quantity else ""),
        payment_date=date.today(),
        confirmed_by_admin=False,
        notes="Automatisch aus Einkaufsliste",
    )
    db.add(payment)
    await db.flush()

    # 3. Item als gekauft markieren
    item.purchased = True
    item.purchased_by_id = user_id
    item.purchased_at = datetime.utcnow()
    item.cost_cents = data.cost_cents
    item.expense_id = expense.id

    await db.flush()
    return item


async def reset_recurring_item(db: AsyncSession, item_id: int):
    """Reset a recurring item so it can be purchased again."""
    item = await get_item(db, item_id)
    if not item or not item.is_recurring or not item.purchased:
        return None

    item.purchased = False
    item.purchased_by_id = None
    item.purchased_at = None
    item.cost_cents = None
    item.expense_id = None

    await db.flush()
    return item


async def unpurchase_item(db: AsyncSession, item_id: int):
    item = await get_item(db, item_id)
    if not item or not item.purchased:
        return None

    # Finanzbuchung (Ausgabe) löschen
    if item.expense_id:
        expense = await db.get(GardenExpense, item.expense_id)
        if expense:
            await db.delete(expense)

    # Gutschrift (MemberPayment) löschen
    q = select(MemberPayment).where(
        and_(
            MemberPayment.user_id == item.purchased_by_id,
            MemberPayment.amount_cents == item.cost_cents,
            MemberPayment.payment_type == "expense_refund",
            MemberPayment.description.contains(item.title),
        )
    )
    result = await db.execute(q)
    payment = result.scalar_one_or_none()
    if payment:
        await db.delete(payment)

    item.purchased = False
    item.purchased_by_id = None
    item.purchased_at = None
    item.cost_cents = None
    item.expense_id = None

    await db.flush()
    return item


async def delete_item(db: AsyncSession, item_id: int):
    item = await get_item(db, item_id)
    if not item:
        return False

    if item.purchased:
        if item.expense_id:
            expense = await db.get(GardenExpense, item.expense_id)
            if expense:
                await db.delete(expense)

        q = select(MemberPayment).where(
            and_(
                MemberPayment.user_id == item.purchased_by_id,
                MemberPayment.amount_cents == item.cost_cents,
                MemberPayment.payment_type == "expense_refund",
                MemberPayment.description.contains(item.title),
            )
        )
        result = await db.execute(q)
        payment = result.scalar_one_or_none()
        if payment:
            await db.delete(payment)

    await db.delete(item)
    await db.flush()
    return True

