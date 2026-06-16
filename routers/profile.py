from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from auth import get_current_user, get_user_transactions, _save_users

router = APIRouter()


class ProfileUpdateRequest(BaseModel):
    monthly_allowance: float
    feeding_budget: float
    dietary_pref: str | None = None
    allowance_period: str | None = None
    meals_per_day: int | None = None
    meal_times: list[str] | None = None


def load_user_transactions(user: dict) -> list[dict]:
    return get_user_transactions(user["email"])


@router.get("/profile")
def get_profile(
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
        "email": current_user["email"],
        "monthly_allowance": current_user["monthly_allowance"],
        "feeding_budget": current_user["feeding_budget"],
        "dietary_pref": current_user.get("dietary_pref"),
        "allowance_period": current_user.get("allowance_period", "monthly"),
        "meals_per_day": len(actual_meal_times),
        "meal_times": actual_meal_times,
    }
    return {
        "user_id": current_user["email"],
        "profile": profile,
        "transactions": transactions,
        "total_spent": sum(tx["amount"] for tx in transactions),
        "feeding_spent": float(sum(tx["amount"] for tx in transactions if tx.get("category") in {"lunch", "breakfast", "snack", "drink", "feeding", "Feeding"})),
    }


@router.post("/profile/update")
def update_profile(
    update: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    current_user["monthly_allowance"] = update.monthly_allowance
    current_user["feeding_budget"] = update.feeding_budget
    current_user["dietary_pref"] = update.dietary_pref
    if update.allowance_period:
        current_user["allowance_period"] = update.allowance_period
    
    if update.meal_times is not None:
        current_user["meal_times"] = update.meal_times
        current_user["meals_per_day"] = len(update.meal_times)
    elif update.meals_per_day is not None:
        current_user["meals_per_day"] = update.meals_per_day
        # update meal_times accordingly
        fallback = []
        if update.meals_per_day >= 1: fallback.append("breakfast")
        if update.meals_per_day >= 2: fallback.append("lunch")
        if update.meals_per_day >= 3: fallback.append("dinner")
        if update.meals_per_day >= 4: fallback.append("snack")
        if not fallback: fallback = ["breakfast", "lunch", "dinner"]
        current_user["meal_times"] = fallback

    _save_users()
    
    actual_meal_times = current_user.get("meal_times", ["breakfast", "lunch", "dinner"])
    return {
        "message": "Profile updated",
        "profile": {
            "email": current_user["email"],
            "monthly_allowance": current_user["monthly_allowance"],
            "feeding_budget": current_user["feeding_budget"],
            "dietary_pref": current_user.get("dietary_pref"),
            "allowance_period": current_user.get("allowance_period", "monthly"),
            "meals_per_day": len(actual_meal_times),
            "meal_times": actual_meal_times,
        },
    }
