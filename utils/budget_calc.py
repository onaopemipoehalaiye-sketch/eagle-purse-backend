from math import ceil
from typing import Dict, List

from schemas import FoodItem
from utils.loader import get_total_spent, get_feeding_spent, get_days_elapsed

def get_period_days(period: str) -> int:
    if period == "weekly":
        return 7
    if period == "bi-weekly":
        return 14
    return 30



def get_budget_summary_data(profile: dict, transactions: List[dict], food_df) -> Dict:
    total_spent = get_total_spent(transactions)
    feeding_spent = get_feeding_spent(transactions)
    days_elapsed = get_days_elapsed(transactions)
    period_days = get_period_days(profile.get("allowance_period", "monthly"))
    days_remaining = max(0, period_days - days_elapsed)
    daily_burn_rate = feeding_spent / days_elapsed if days_elapsed else 0.0
    remaining_feeding = profile["feeding_budget"] - feeding_spent
    if remaining_feeding < 0:
        projected_broke_day = 0.0
    else:
        projected_broke_day = round(remaining_feeding / daily_burn_rate, 2) if daily_burn_rate > 0 else None
    protein_carbs = food_df[(food_df["protein"] == 1) & (food_df["carbs"] == 1)]
    if not protein_carbs.empty:
        survival_threshold = float(protein_carbs["price"].min())
    else:
        survival_threshold = float(food_df["price"].min())
    survival_mode = False
    if days_remaining > 0:
        survival_mode = (remaining_feeding / days_remaining) < survival_threshold
    else:
        survival_mode = remaining_feeding <= 0
    if remaining_feeding < 0:
        recommendation_summary = "You have overspent. Reduce spending immediately."
    elif survival_mode:
        recommendation_summary = (
            "Feeding budget is tight; switch to the cheapest meals and cut snacks to survive the month."
        )
    else:
        recommendation_summary = (
            "Your budget is on track, but keep an eye on meal costs and avoid extra treats."
        )

    return {
        "total_spent": round(total_spent, 2),
        "feeding_spent": round(feeding_spent, 2),
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "period_days": period_days,
        "daily_burn_rate": round(daily_burn_rate, 2),
        "projected_broke_day": round(projected_broke_day, 2) if projected_broke_day is not None else None,
        "survival_threshold": round(survival_threshold, 2),
        "survival_mode": survival_mode,
        "recommendation_summary": recommendation_summary,
    }


def get_auto_adjust_data(profile: dict, transactions: List[dict], food_df) -> Dict:
    summary = get_budget_summary_data(profile, transactions, food_df)
    days_remaining = summary["days_remaining"]
    remaining_feeding = profile["feeding_budget"] - summary["feeding_spent"]
    new_daily_limit = max(0.0, round(remaining_feeding / days_remaining, 2)) if days_remaining > 0 else 0.0
    suggested_meals = []
    sacrifices = []
    try:
        if summary["survival_mode"]:
            sacrifices = [
                "Cut all snacks and suya",
                "Walk to class",
                "Use only Bingham Village spots",
            ]
            cheap_items = food_df[food_df["meal_type"] == "lunch"].sort_values("price").head(3)
            suggested_meals = [FoodItem(**item).model_dump() for _, item in cheap_items.iterrows()]
        else:
            if summary["feeding_spent"] > profile["feeding_budget"]:
                sacrifices = ["Avoid expensive campus meals", "Stick to cheapest lunch options"]
            cheap_lunch = food_df[
                (food_df["meal_type"] == "lunch") & (food_df["price"] <= new_daily_limit)
            ].sort_values(["price", "protein"], ascending=[True, False]).head(3)
            if cheap_lunch.empty:
                cheap_lunch = food_df[food_df["meal_type"] == "lunch"].sort_values("price").head(3)
            suggested_meals = [FoodItem(**item).model_dump() for _, item in cheap_lunch.iterrows()]

        return {
            "new_daily_limit": new_daily_limit,
            "survival_mode": summary["survival_mode"],
            "suggested_meals": suggested_meals,
            "sacrifices": sacrifices,
            "message": "Coach Ngozi has adjusted your plan. Accept?",
        }
    except Exception:
        return {
            "new_daily_limit": new_daily_limit,
            "survival_mode": summary["survival_mode"],
            "suggested_meals": [],
            "sacrifices": [],
            "message": "Unable to compute suggestions.",
        }
