from fastapi import APIRouter, HTTPException, status

from app.dependencies import DBSession, CurrentUser, AdminUser
from app.shopping import service
from app.shopping.schemas import (
    ShoppingItemCreate,
    ShoppingItemRead,
    ShoppingItemUpdate,
    ShoppingItemPurchase,
)

router = APIRouter(prefix="/api/shopping", tags=["shopping"])


@router.get("/", response_model=list[ShoppingItemRead])
async def list_items(
    user: CurrentUser,
    db: DBSession,
    include_purchased: bool = False,
):
    items = await service.get_items(db, include_purchased=include_purchased)
    return [ShoppingItemRead.from_model(i) for i in items]


@router.post("/", response_model=ShoppingItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(data: ShoppingItemCreate, user: CurrentUser, db: DBSession):
    item = await service.create_item(db, user.id, data)
    await db.refresh(item)
    await db.commit()
    return ShoppingItemRead.from_model(item)


@router.put("/{item_id}", response_model=ShoppingItemRead)
async def update_item(item_id: int, data: ShoppingItemUpdate, user: CurrentUser, db: DBSession):
    item = await service.update_item(db, item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Item nicht gefunden")
    await db.commit()
    return ShoppingItemRead.from_model(item)


@router.post("/{item_id}/purchase", response_model=ShoppingItemRead)
async def purchase_item(
    item_id: int, data: ShoppingItemPurchase, user: CurrentUser, db: DBSession
):
    item = await service.purchase_item(db, item_id, user.id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Item nicht gefunden oder bereits gekauft")
    await db.commit()
    return ShoppingItemRead.from_model(item)


@router.post("/{item_id}/reset", response_model=ShoppingItemRead)
async def reset_recurring_item(item_id: int, user: CurrentUser, db: DBSession):
    """Reset a recurring item so it appears as 'to buy' again."""
    item = await service.reset_recurring_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item nicht gefunden, nicht recurring, oder nicht gekauft")
    await db.commit()
    return ShoppingItemRead.from_model(item)


@router.post("/{item_id}/unpurchase", response_model=ShoppingItemRead)
async def unpurchase_item(item_id: int, user: AdminUser, db: DBSession):
    item = await service.unpurchase_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item nicht gefunden oder nicht gekauft")
    await db.commit()
    return ShoppingItemRead.from_model(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: int, user: CurrentUser, db: DBSession):
    deleted = await service.delete_item(db, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item nicht gefunden")
    await db.commit()

