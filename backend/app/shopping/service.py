from datetime import datetime, date

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.shopping.models import ShoppingItem
from app.shopping.schemas import ShoppingItemCreate, ShoppingItemUpdate, ShoppingItemPurchase
from app.finance.models import GardenExpense


async def get_items(db: AsyncSession, include_purchased: bool = False):
    q = select(ShoppingItem).options(
        joinedload(ShoppingItem.added_by),
        joinedload(ShoppingItem.purchased_by),
    )
    if not include_purchased:
        q = q.where(ShoppingItem.purchased == False)
    q = q.order_by(desc(ShoppingItem.created_at))
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
    await db.flush()
    return item


async def purchase_item(
    db: AsyncSession, item_id: int, user_id: int, data: ShoppingItemPurchase
):
    item = await get_item(db, item_id)
    if not item or item.purchased:
        return None

    # 1. Finanzbuchung erstellen (Einmal-Ausgabe)
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

    # 2. Item als gekauft markieren
    item.purchased = True
    item.purchased_by_id = user_id
    item.purchased_at = datetime.utcnow()
    item.cost_cents = data.cost_cents
    item.expense_id = expense.id

    await db.flush()
    return item


async def unpurchase_item(db: AsyncSession, item_id: int):
    item = await get_item(db, item_id)
    if not item or not item.purchased:
        return None

    # Finanzbuchung löschen
    if item.expense_id:
        expense = await db.get(Expense, item.expense_id)
        if expense:
            await db.delete(expense)

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

    # Falls gekauft, auch die Finanzbuchung löschen
    if item.expense_id:
        expense = await db.get(Expense, item.expense_id)
        if expense:
            await db.delete(expense)

    await db.delete(item)
    await db.flush()
    return True

