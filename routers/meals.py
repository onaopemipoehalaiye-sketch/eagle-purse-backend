from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user, get_user_transactions
from database import get_db
from models import User
from utils.budget_calc import get_period_days
from utils.loader import get_days_elapsed, get_feeding_spent
from utils.meals_logic import generate_meal_combos

router = APIRouter()


def calculate_daily_budget(profile: dict, transactions: list[dict]) -> float:
    feeding_spent = get_feeding_spent(transactions)
    days_elapsed = get_days_elapsed(transactions)
    period_days = get_period_days(profile.get("allowance_period", "monthly"))
    days_remaining = max(0, period_days - days_elapsed)
    remaining_feeding = profile["feeding_budget"] - feeding_spent
    return round(remaining_feeding / days_remaining, 2) if days_remaining > 0 else 0.0


@router.get("/coach/meal-plan")
async def meal_plan(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    transactions = await get_user_transactions(current_user.email, db)
    meal_times = current_user.meal_times or ["breakfast", "lunch", "dinner"]

    profile = {
        "monthly_allowance": current_user.monthly_allowance,
        "feeding_budget": current_user.feeding_budget,
        "allowance_period": current_user.allowance_period or "monthly",
        "dietary_pref": current_user.dietary_pref,
    }
    food_df = request.app.state.food_df
    daily_budget = calculate_daily_budget(profile, transactions)

    return generate_meal_combos(
        daily_budget=daily_budget,
        food_df=food_df,
        meal_times=meal_times,
        dietary_pref=profile["dietary_pref"],
    )
