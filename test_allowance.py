import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))

from auth import create_user, users
from utils.budget_calc import get_budget_summary_data
import pandas as pd

def test_allowance():
    # Make a dummy food_df
    food_df = pd.DataFrame([
        {"item": "Test", "price": 100, "protein": 1, "carbs": 1, "meal_type": "lunch"}
    ])
    
    test_email = "test_allowance@test.com"
    if test_email in users:
        del users[test_email]
        
    user = create_user(
        email=test_email,
        password="pwd",
        monthly_allowance=10000,
        feeding_budget=5000,
        allowance_period="weekly",
        transactions=[
            {"amount": 1000, "category": "feeding", "date": "2026-05-15"},
            {"amount": 500, "category": "snack", "date": "2026-05-16"}
        ]
    )
    
    print(f"Created user with allowance_period: {user['allowance_period']}")
    
    from auth import get_user_transactions
    transactions = get_user_transactions(test_email)
    summary = get_budget_summary_data(user, transactions, food_df)
    print(f"Period days: {summary['period_days']}")
    print(f"Days elapsed: {summary['days_elapsed']}")
    print(f"Days remaining: {summary['days_remaining']}")

if __name__ == "__main__":
    test_allowance()
