from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import get_current_user, user_transactions, _save_transactions

router = APIRouter()


class AddTransactionRequest(BaseModel):
    category: str
    vendor: str
    item: str
    amount: float
    date: str  # ISO format, e.g. "2026-05-19"


@router.post("/transactions/add")
def add_transaction(
    body: AddTransactionRequest,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    transaction = {
        "date": body.date,
        "category": body.category,
        "vendor": body.vendor,
        "item": body.item,
        "amount": body.amount,
    }

    if email not in user_transactions:
        user_transactions[email] = []

    user_transactions[email].append(transaction)
    _save_transactions()

    return {
        "success": True,
        "transaction": transaction,
        "message": f"Expense of ₦{body.amount} at {body.vendor} logged successfully.",
    }
