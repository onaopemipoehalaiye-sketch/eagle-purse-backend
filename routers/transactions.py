from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import Transaction, User

router = APIRouter()


class AddTransactionRequest(BaseModel):
    category: str
    vendor: str
    item: str
    amount: float
    date: str  # ISO format, e.g. "2026-05-19"


@router.post("/transactions/add")
async def add_transaction(
    body: AddTransactionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    transaction = Transaction(
        user_email=current_user.email,
        date=body.date,
        category=body.category,
        vendor=body.vendor,
        item=body.item,
        amount=body.amount,
    )
    db.add(transaction)
    await db.flush()

    return {
        "success": True,
        "transaction": {
            "date": body.date,
            "category": body.category,
            "vendor": body.vendor,
            "item": body.item,
            "amount": body.amount,
        },
        "message": f"Expense of ₦{body.amount} at {body.vendor} logged successfully.",
    }
