from typing import List, Optional

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    monthly_allowance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    feeding_budget: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dietary_pref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    allowance_period: Mapped[str] = mapped_column(String, nullable=False, default="monthly")
    meals_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    meal_times: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)

    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User email={self.email}>"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(
        String, ForeignKey("users.email", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    vendor: Mapped[str] = mapped_column(String, nullable=False)
    item: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} user={self.user_email} amount={self.amount}>"
