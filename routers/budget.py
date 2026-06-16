from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth import get_current_user, get_user_transactions, _save_users, user_transactions, _save_transactions
from utils.budget_calc import get_budget_summary_data, get_auto_adjust_data

router = APIRouter()


class ApplyPlanRequest(BaseModel):
    new_daily_limit: float


def load_user_transactions(user: dict) -> list[dict]:
    return get_user_transactions(user["email"])


@router.get("/budget/summary")
def budget_summary(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    transactions = load_user_transactions(current_user)
    profile = {
        "monthly_allowance": current_user["monthly_allowance"],
        "feeding_budget": current_user["feeding_budget"],
        "allowance_period": current_user.get("allowance_period", "monthly"),
    }
    return get_budget_summary_data(profile, transactions, request.app.state.food_df)


@router.post("/budget/auto-adjust")
def auto_adjust(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    transactions = load_user_transactions(current_user)
    profile = {
        "monthly_allowance": current_user["monthly_allowance"],
        "feeding_budget": current_user["feeding_budget"],
        "allowance_period": current_user.get("allowance_period", "monthly"),
    }
    return get_auto_adjust_data(profile, transactions, request.app.state.food_df)


@router.post("/budget/apply-plan")
def apply_plan(
    body: ApplyPlanRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    transactions = load_user_transactions(current_user)
    profile = {
        "monthly_allowance": current_user["monthly_allowance"],
        "feeding_budget": current_user["feeding_budget"],
        "allowance_period": current_user.get("allowance_period", "monthly"),
    }

    summary = get_budget_summary_data(profile, transactions, request.app.state.food_df)
    days_remaining = summary["days_remaining"]
    if days_remaining == 0:
        raise HTTPException(status_code=400, detail="Cannot apply plan because there are no days remaining.")

    new_feeding_budget = round(body.new_daily_limit * days_remaining, 2)
    current_user["feeding_budget"] = new_feeding_budget
    _save_users()

    return {
        "success": True,
        "new_feeding_budget": new_feeding_budget,
        "message": f"Plan applied. Your new feeding budget is ₦{new_feeding_budget}.",
    }


@router.post("/budget/reset-cycle")
def reset_cycle(
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    user_transactions[email] = []
    _save_transactions()
    return {
        "success": True,
        "message": "New allowance cycle started. Your spent has been reset.",
    }


@router.post("/budget/reset-transactions")
def reset_transactions(
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    user_transactions[email] = []
    _save_transactions()
    return {
        "success": True,
        "message": "All expenses cleared.",
    }
