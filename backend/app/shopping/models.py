from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship
from app.database import Base


class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    notes = Column(Text, nullable=True)
    quantity = Column(String(50), nullable=True)  # z.B. "3 Säcke", "10kg"
    category = Column(String(50), nullable=True)  # z.B. "Erde", "Samen", "Werkzeug"
    added_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Kauf-Felder
    purchased = Column(Boolean, default=False, nullable=False)
    purchased_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    purchased_at = Column(DateTime(timezone=True), nullable=True)
    cost_cents = Column(Integer, nullable=True)  # Preis in Cent
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=True)  # Link zur Finanz-Buchung

    added_by = relationship("User", foreign_keys=[added_by_id], lazy="joined")
    purchased_by = relationship("User", foreign_keys=[purchased_by_id], lazy="joined")
    expense = relationship("Expense", lazy="joined")

