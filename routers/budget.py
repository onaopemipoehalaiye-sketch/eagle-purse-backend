from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user, get_user_transactions
from database import get_db
from models import User
from utils.budget_calc import get_auto_adjust_data, get_budget_summary_data

router = APIRouter()


class ApplyPlanRequest(BaseModel):
    new_daily_limit: float


def _user_profile(user: User) -> dict:
    return {
        "monthly_allowance": user.monthly_allowance,
        "feeding_budget": user.feeding_budget,
        "allowance_period": user.allowance_period or "monthly",
    }


@router.get("/budget/summary")
async def budget_summary(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    transactions = await get_user_transactions(current_user.email, db)
    return get_budget_summary_data(_user_profile(current_user), transactions, request.app.state.food_df)


@router.post("/budget/auto-adjust")
async def auto_adjust(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    transactions = await get_user_transactions(current_user.email, db)
    return get_auto_adjust_data(_user_profile(current_user), transactions, request.app.state.food_df)


@router.post("/budget/apply-plan")
async def apply_plan(
    body: ApplyPlanRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    transactions = await get_user_transactions(current_user.email, db)
    summary = get_budget_summary_data(_user_profile(current_user), transactions, request.app.state.food_df)
    days_remaining = summary["days_remaining"]
    if days_remaining == 0:
        raise HTTPException(status_code=400, detail="Cannot apply plan because there are no days remaining.")

    new_feeding_budget = round(body.new_daily_limit * days_remaining, 2)
    current_user.feeding_budget = new_feeding_budget
    db.add(current_user)

    return {
        "success": True,
        "new_feeding_budget": new_feeding_budget,
        "message": f"Plan applied. Your new feeding budget is ₦{new_feeding_budget}.",
    }


@router.post("/budget/reset-cycle")
async def reset_cycle(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import delete
    from models import Transaction
    await db.execute(delete(Transaction).where(Transaction.user_email == current_user.email))
    return {
        "success": True,
        "message": "New allowance cycle started. Your spent has been reset.",
    }


@router.post("/budget/reset-transactions")
async def reset_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import delete
    from models import Transaction
    await db.execute(delete(Transaction).where(Transaction.user_email == current_user.email))
    return {
        "success": True,
        "message": "All expenses cleared.",
    }
