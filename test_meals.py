import os
import sys
import pandas as pd
from pathlib import Path

# Add backend dir to sys.path
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))

from utils.loader import load_food_catalog
from utils.meals_logic import generate_meal_combos

def test_meals():
    food_df = load_food_catalog()
    
    budgets = [600.0, 200.0, 1500.0]
    
    for b in budgets:
        print(f"--- Budget: ₦{b} ---")
        res = generate_meal_combos(b, food_df, "lunch")
        print(f"Survival mode: {res['survival_mode']}")
        if res['survival_mode']:
            print(f"Message: {res['message']}")
        else:
            for c in res['combos']:
                print(f"Combo: {c['name']} (₦{c['total_price']}, Score: {c['filling_score']})")
                for item in c['items']:
                    print(f"  - {item['item']} (₦{item['price']})")
        print()

if __name__ == "__main__":
    test_meals()
