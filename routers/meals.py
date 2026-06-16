from fastapi import APIRouter, Depends, Query, Request

from auth import get_current_user, get_user_transactions
from schemas import FoodItem
from utils.loader import get_feeding_spent, get_days_elapsed
from utils.budget_calc import get_period_days
from utils.meals_logic import generate_meal_combos

router = APIRouter()


def calculate_daily_budget(profile: dict, transactions: list[dict]) -> float:
    feeding_spent = get_feeding_spent(transactions)
    days_elapsed = get_days_elapsed(transactions)
    period_days = get_period_days(profile.get("allowance_period", "monthly"))
    days_remaining = max(0, period_days - days_elapsed)
    remaining_feeding = profile["feeding_budget"] - feeding_spent
    return round(remaining_feeding / days_remaining, 2) if days_remaining > 0 else 0.0


def load_user_transactions(user: dict) -> list[dict]:
    return get_user_transactions(user["email"])


@router.get("/coach/meal-plan")
def meal_plan(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    transactions = load_user_transactions(current_user)
    actual_meal_times = current_user.get("meal_times")
    if actual_meal_times is None:
        old_meals = current_user.get("meals_per_day", 3)
        actual_meal_times = []
        if old_meals >= 1:
            actual_meal_times.append("breakfast")
        if old_meals >= 2:
            actual_meal_times.append("lunch")
        if old_meals >= 3:
            actual_meal_times.append("dinner")
        if old_meals >= 4:
            actual_meal_times.append("snack")
        if not actual_meal_times:
            actual_meal_times = ["breakfast", "lunch", "dinner"]

    profile = {
        "monthly_allowance": current_user["monthly_allowance"],
        "feeding_budget": current_user["feeding_budget"],
        "allowance_period": current_user.get("allowance_period", "monthly"),
        "dietary_pref": current_user.get("dietary_pref"),
    }
    food_df = request.app.state.food_df
    daily_budget = calculate_daily_budget(profile, transactions)
    
    return generate_meal_combos(
        daily_budget=daily_budget, 
        food_df=food_df, 
        meal_times=actual_meal_times, 
        dietary_pref=profile["dietary_pref"]
    )
