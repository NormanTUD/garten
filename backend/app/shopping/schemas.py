from datetime import datetime
from pydantic import BaseModel, Field


class ShoppingItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    notes: str | None = None
    quantity: str | None = None
    category: str | None = None


class ShoppingItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = None
    quantity: str | None = None
    category: str | None = None


class ShoppingItemPurchase(BaseModel):
    cost_cents: int = Field(gt=0)
    notes: str | None = None  # Optionale Notiz für die Finanzbuchung


class ShoppingItemRead(BaseModel):
    id: int
    title: str
    notes: str | None
    quantity: str | None
    category: str | None
    added_by_name: str
    added_by_id: int
    created_at: datetime
    purchased: bool
    purchased_by_name: str | None
    purchased_at: datetime | None
    cost_cents: int | None
    expense_id: int | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, obj):
        return cls(
            id=obj.id,
            title=obj.title,
            notes=obj.notes,
            quantity=obj.quantity,
            category=obj.category,
            added_by_name=obj.added_by.display_name,
            added_by_id=obj.added_by_id,
            created_at=obj.created_at,
            purchased=obj.purchased,
            purchased_by_name=obj.purchased_by.display_name if obj.purchased_by else None,
            purchased_at=obj.purchased_at,
            cost_cents=obj.cost_cents,
            expense_id=obj.expense_id,
        )

