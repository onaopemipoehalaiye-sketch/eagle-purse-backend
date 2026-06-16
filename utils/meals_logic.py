import pandas as pd

def _generate_combos_for_slot(budget: float, food_df: pd.DataFrame, slot_type: str) -> list[dict]:
    # Base candidates for the main meal
    if slot_type == "snack":
        # For snacks, we don't require full protein/carb complete meals, just anything affordable in snack/lifehack/drink
        main_candidates = food_df[(food_df["meal_type"] == "snack") | (food_df["category"] == "lifehack") | (food_df["category"] == "drink")]
        
        combos = []
        for _, row in main_candidates.iterrows():
            if row["price"] <= budget:
                combos.append({
                    "main_items": [row],
                    "protein": row["protein"],
                    "carbs": row["carbs"],
                    "base_price": row["price"],
                })
        
        # Combinations of 2 snacks
        for i, row1 in main_candidates.iterrows():
            for j, row2 in main_candidates.iterrows():
                if i >= j: continue
                if row1["item"] == row2["item"]: continue
                combined_price = row1["price"] + row2["price"]
                if combined_price <= budget:
                    combos.append({
                        "main_items": [row1, row2] if row1["price"] >= row2["price"] else [row2, row1],
                        "protein": row1["protein"] + row2["protein"],
                        "carbs": row1["carbs"] + row2["carbs"],
                        "base_price": combined_price,
                    })
        return combos
    
    main_candidates = food_df[(food_df["meal_type"] == slot_type) | (food_df["meal_type"] == "snack") | (food_df["category"] == "lifehack")]
    combos = []
    
    # 1. Complete meals
    complete_meals = food_df[(food_df["meal_type"] == slot_type) & (food_df["protein"] == 1) & (food_df["carbs"] == 1)]
    if not complete_meals.empty:
        for _, row in complete_meals.iterrows():
            if row["price"] <= budget:
                combos.append({
                    "main_items": [row],
                    "protein": row["protein"],
                    "carbs": row["carbs"],
                    "base_price": row["price"],
                })

    # 2. Pair a protein with a carb
    proteins = main_candidates[(main_candidates["protein"] == 1)]
    carbs = main_candidates[(main_candidates["carbs"] == 1)]
    
    for _, p_row in proteins.iterrows():
        for _, c_row in carbs.iterrows():
            if p_row["item"] == c_row["item"]:
                continue
            combined_price = p_row["price"] + c_row["price"]
            if combined_price <= budget:
                combos.append({
                    "main_items": [p_row, c_row] if p_row["price"] >= c_row["price"] else [c_row, p_row],
                    "protein": 1,
                    "carbs": 1,
                    "base_price": combined_price,
                })
    return combos

def generate_meal_combos(
    daily_budget: float,
    food_df: pd.DataFrame,
    meal_times: list[str],
    dietary_pref: str = None
) -> dict:
    original_df = food_df.copy()
    preference_ignored = False
    preference_warning = ""

    # Handle legacy integer or string parameter values robustly
    if isinstance(meal_times, int):
        meals_per_day = meal_times
        meal_times = []
        if meals_per_day >= 1:
            meal_times.append("breakfast")
        if meals_per_day >= 2:
            meal_times.append("lunch")
        if meals_per_day >= 3:
            meal_times.append("dinner")
        if meals_per_day >= 4:
            meal_times.append("snack")
        if not meal_times:
            meal_times = ["breakfast", "lunch", "dinner"]
    elif isinstance(meal_times, str):
        meal_times = [meal_times]
    elif meal_times is None:
        meal_times = ["breakfast", "lunch", "dinner"]

    if dietary_pref:
        pref_lower = dietary_pref.lower().strip()
        if pref_lower == "vegetarian":
            food_df = food_df[(food_df["veg"] == 1) | (food_df["tags"].str.contains("vegetarian", na=False, case=False))]
        elif pref_lower == "no pork":
            food_df = food_df[~food_df["tags"].str.contains("pork", na=False, case=False) | food_df["tags"].str.contains("no-pork", na=False, case=False)]
        else:
            food_df = food_df[food_df["tags"].str.contains(pref_lower, na=False, case=False)]
            
        if food_df.empty:
            food_df = original_df
            preference_ignored = True
            preference_warning = f"We couldn't find affordable meals matching your diet ({dietary_pref}), so we're showing all options."

    # Exclude provisions from combo building
    food_df = food_df[food_df["category"] != "provision"]
    drinks = food_df[food_df["category"] == "drink"].sort_values("price")

    meals_count = len(meal_times)
    per_meal_budget = round(daily_budget / meals_count, 2) if meals_count > 0 else daily_budget
    
    daily_plan = {}
    total_daily_cost = 0.0
    has_unaffordable_slot = False

    for slot in meal_times:
        raw_combos = _generate_combos_for_slot(per_meal_budget, food_df, slot)
        
        if not raw_combos:
            daily_plan[slot] = []
            has_unaffordable_slot = True
            continue
            
        final_combos = []
        seen_combos = set()
        
        for c in raw_combos:
            items = c["main_items"].copy()
            current_price = c["base_price"]
            current_protein = c["protein"]
            current_carbs = c["carbs"]
            
            # Add cheapest drink if it fits and not a snack
            if slot != "snack":
                for _, d_row in drinks.iterrows():
                    if current_price + d_row["price"] <= per_meal_budget:
                        items.append(d_row)
                        current_price += d_row["price"]
                        break
                    
            main_item_names = []
            for i in c["main_items"]:
                if i["item"] not in main_item_names:
                    main_item_names.append(i["item"])
                    
            main_names = " & ".join(main_item_names)
            extra_names = " + ".join([i["item"] for i in items if i["item"] not in main_item_names])
            
            name = main_names
            if extra_names:
                name += f" with {extra_names}"
                
            item_keys = tuple(sorted([i["item"] for i in items]))
            if item_keys in seen_combos:
                continue
            seen_combos.add(item_keys)

            price_penalty = 0
            if current_price < 500:
                price_penalty = (500 - current_price) / 100.0

            filling_score = (current_protein * 5) + (current_carbs * 5) - price_penalty
            if slot == "snack":
                filling_score = current_protein * 2 + current_carbs * 2
            
            final_combos.append({
                "name": name,
                "items": [{"vendor": i["vendor"], "item": i["item"], "price": float(i["price"])} for i in items],
                "total_price": float(current_price),
                "filling_score": round(filling_score, 2)
            })

        final_combos.sort(key=lambda x: x["filling_score"], reverse=True)
        best_combos = final_combos[:3]
        daily_plan[slot] = best_combos
        if best_combos:
            total_daily_cost += best_combos[0]["total_price"]
        else:
            has_unaffordable_slot = True

    survival_mode = has_unaffordable_slot or (total_daily_cost > daily_budget)
    
    # If survival mode is triggered, and dietary preference was active, try relaxing dietary preferences
    if survival_mode and dietary_pref and not preference_ignored:
        return generate_meal_combos(
            daily_budget=daily_budget,
            food_df=original_df,
            meal_times=meal_times,
            dietary_pref=None
        ) | {
            "preference_ignored": True,
            "preference_warning": f"We couldn't find affordable meals matching your diet ({dietary_pref}), so we're showing all options."
        }

    # Format survival message
    survival_message = "Here's your full day plan."
    if survival_mode:
        suggested_count = max(1, meals_count - 1)
        survival_message = f"Cannot afford {meals_count} meals today. Consider dropping to {suggested_count} meals."

    # Backward compatibility with legacy tests
    all_combos = []
    for slot_combos in daily_plan.values():
        if slot_combos:
            all_combos.extend(slot_combos)
    
    if len(meal_times) == 1:
        combos_legacy = daily_plan.get(meal_times[0], [])
    else:
        combos_legacy = all_combos

    return {
        "daily_budget": daily_budget,
        "meal_times": meal_times,
        "meals_per_day": meals_count, # for backward compatibility
        "per_meal_budget": per_meal_budget,
        "daily_plan": daily_plan,
        "total_daily_cost": round(total_daily_cost, 2),
        "survival_mode": survival_mode,
        "survival_message": survival_message,
        "message": survival_message, # for backward compatibility
        "preference_ignored": preference_ignored,
        "preference_warning": preference_warning,
        "combos": combos_legacy # for test_meals.py
    }
