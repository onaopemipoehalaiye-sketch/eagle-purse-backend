from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user, get_user_transactions, user_profile_payload
from database import get_db
from models import User

router = APIRouter()


class ProfileUpdateRequest(BaseModel):
    monthly_allowance: float
    feeding_budget: float
    dietary_pref: str | None = None
    allowance_period: str | None = None
    meals_per_day: int | None = None
    meal_times: list[str] | None = None


@router.get("/profile")
async def get_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    transactions = await get_user_transactions(current_user.email, db)
    meal_times = current_user.meal_times or ["breakfast", "lunch", "dinner"]
    feeding_categories = {"lunch", "breakfast", "snack", "drink", "feeding", "Feeding"}

    profile = {
        "email": current_user.email,
        "monthly_allowance": current_user.monthly_allowance,
        "feeding_budget": current_user.feeding_budget,
        "dietary_pref": current_user.dietary_pref,
        "allowance_period": current_user.allowance_period or "monthly",
        "meals_per_day": len(meal_times),
        "meal_times": meal_times,
    }
    return {
        "user_id": current_user.email,
        "profile": profile,
        "transactions": transactions,
        "total_spent": sum(tx["amount"] for tx in transactions),
        "feeding_spent": float(
            sum(tx["amount"] for tx in transactions if tx.get("category") in feeding_categories)
        ),
    }


@router.post("/profile/update")
async def update_profile(
    update: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.monthly_allowance = update.monthly_allowance
    current_user.feeding_budget = update.feeding_budget
    current_user.dietary_pref = update.dietary_pref

    if update.allowance_period:
        current_user.allowance_period = update.allowance_period

    if update.meal_times is not None:
        current_user.meal_times = update.meal_times
        current_user.meals_per_day = len(update.meal_times)
    elif update.meals_per_day is not None:
        current_user.meals_per_day = update.meals_per_day
        fallback = []
        if update.meals_per_day >= 1: fallback.append("breakfast")
        if update.meals_per_day >= 2: fallback.append("lunch")
        if update.meals_per_day >= 3: fallback.append("dinner")
        if update.meals_per_day >= 4: fallback.append("snack")
        if not fallback: fallback = ["breakfast", "lunch", "dinner"]
        current_user.meal_times = fallback

    db.add(current_user)
    actual_meal_times = current_user.meal_times or ["breakfast", "lunch", "dinner"]
    return {
        "message": "Profile updated",
        "profile": {
            "email": current_user.email,
            "monthly_allowance": current_user.monthly_allowance,
            "feeding_budget": current_user.feeding_budget,
            "dietary_pref": current_user.dietary_pref,
            "allowance_period": current_user.allowance_period or "monthly",
            "meals_per_day": len(actual_meal_times),
            "meal_times": actual_meal_times,
        },
    }
