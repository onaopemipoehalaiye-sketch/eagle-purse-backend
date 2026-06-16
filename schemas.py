from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class FoodItem(BaseModel):
    vendor: str
    item: str
    price: float
    meal_type: str
    protein: int
    carbs: int
    veg: int
    location: str


class Transaction(BaseModel):
    date: date
    category: str
    vendor: str
    item: str
    amount: float


class ProfileUpdateRequest(BaseModel):
    allowance: float = Field(..., alias="monthly_allowance")
    feeding_budget: float
    dietary_pref: str | None = None


class BudgetSummaryResponse(BaseModel):
    total_spent: float
    feeding_spent: float
    days_elapsed: int
    days_remaining: int
    daily_burn_rate: float
    projected_broke_day: float
    survival_threshold: float
    survival_mode: bool
    recommendation_summary: str


class AutoAdjustResponse(BaseModel):
    new_daily_limit: float
    survival_mode: bool
    suggested_meals: list[FoodItem]
    sacrifices: list[str]
    message: str


class MealPlanResponse(BaseModel):
    best_meal: FoodItem
    alternatives: list[FoodItem]
    survival_mode: bool
    message: str


class CoachAdviceRequest(BaseModel):
    user_id: str
    recent_transactions: list[dict[str, Any]]
    chat_history: list[dict[str, Any]]


class CoachAdviceResponse(BaseModel):
    message: str
    auto_adjust: dict | None = None
