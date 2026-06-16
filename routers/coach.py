import os
from fastapi import APIRouter, Request, Depends
from openai import OpenAI
from pydantic import BaseModel

from auth import get_current_user, get_user_transactions
from schemas import CoachAdviceResponse
from utils.loader import get_feeding_spent, get_total_spent, get_days_elapsed
from utils.budget_calc import get_budget_summary_data, get_auto_adjust_data, get_period_days
from utils.meals_logic import generate_meal_combos

router = APIRouter()


class AdviceRequest(BaseModel):
    user_id: str | None = None
    recent_transactions: list[dict] = []
    chat_history: list[dict] = []


def build_state_text(profile: dict, transactions: list[dict], food_df) -> str:
    feeding_spent = get_feeding_spent(transactions)
    days_elapsed = get_days_elapsed(transactions)
    period_days = get_period_days(profile.get("allowance_period", "monthly"))
    days_remaining = max(0, period_days - days_elapsed)
    daily_burn_rate = feeding_spent / days_elapsed if days_elapsed else 0.0
    remaining_feeding = profile["feeding_budget"] - feeding_spent
    survival_threshold = float(
        food_df[(food_df["protein"] == 1) & (food_df["carbs"] == 1)]["price"].min()
    )
    survival_mode = days_remaining > 0 and (remaining_feeding / days_remaining) < survival_threshold
    if days_remaining == 0:
        survival_mode = remaining_feeding <= 0
    top_items = food_df.sort_values("price").head(6)
    catalog_rows = "\n".join(
        f"{row['item']} ({row['meal_type']}) - ₦{int(row['price'])} at {row['vendor']}"
        for _, row in top_items.iterrows()
    )
    return (
        f"Student state:\n"
        f"Allowance: ₦{profile['monthly_allowance']}\n"
        f"Feeding budget: ₦{profile['feeding_budget']}\n"
        f"Spent on feeding: ₦{feeding_spent}\n"
        f"Total spent: ₦{get_total_spent(transactions)}\n"
        f"Days elapsed: {days_elapsed}\n"
        f"Days remaining: {days_remaining}\n"
        f"Daily burn rate: ₦{round(daily_burn_rate, 2)}\n"
        f"Meal times: {', '.join(profile.get('meal_times', ['breakfast', 'lunch', 'dinner']))}\n"
        f"Dietary preference: {profile.get('dietary_pref', 'none')}\n"
        f"Survival mode: {survival_mode}\n"
        f"Budget catalog snapshot:\n{catalog_rows}\n"
    )


@router.post("/coach/advice")
def coach_advice(
    request: Request,
    body: AdviceRequest,
    current_user: dict = Depends(get_current_user),
) -> CoachAdviceResponse:
    profile = {
        "monthly_allowance": current_user["monthly_allowance"],
        "feeding_budget": current_user["feeding_budget"],
        "allowance_period": current_user.get("allowance_period", "monthly"),
        "dietary_pref": current_user.get("dietary_pref"),
        "meals_per_day": current_user.get("meals_per_day", 3),
        "meal_times": current_user.get("meal_times", ["breakfast", "lunch", "dinner"]),
    }
    transactions = get_user_transactions(current_user["email"])

    food_df = request.app.state.food_df
    state_text = build_state_text(profile, transactions, food_df)
    auto_adjust_plan = get_auto_adjust_data(profile, transactions, food_df)

    summary = get_budget_summary_data(profile, transactions, food_df)
    needed = bool(
        summary.get("survival_mode")
        or (auto_adjust_plan.get("new_daily_limit", 0) < summary.get("survival_threshold", 0))
    )

    plan_lines = [f"Auto-adjust plan:", f"New daily limit: ₦{auto_adjust_plan.get('new_daily_limit')}" ]
    if auto_adjust_plan.get("sacrifices"):
        plan_lines.append("Sacrifices: " + ", ".join(auto_adjust_plan.get("sacrifices")))
    if auto_adjust_plan.get("suggested_meals"):
        meals_text = ", ".join([
            f"{m.get('item')} at {m.get('vendor')} (₦{int(m.get('price', 0))})"
            for m in auto_adjust_plan.get("suggested_meals")[:3]
        ])
        plan_lines.append("Suggested meals: " + meals_text)

    # Generate combos for the system prompt
    daily_budget = auto_adjust_plan.get("new_daily_limit", 0)
    combo_data = generate_meal_combos(
        daily_budget=daily_budget, 
        food_df=food_df, 
        meal_times=profile.get("meal_times", ["breakfast", "lunch", "dinner"]), 
        dietary_pref=profile.get("dietary_pref")
    )
    
    if combo_data.get("survival_mode"):
        plan_lines.append(
            "CRITICAL SURVIVAL MODE: The student's daily budget is too low for their requested number of meals. "
            "You MUST honestly tell the student they cannot afford a proper meal for every slot today. "
            "Suggest dropping a specific meal (e.g., 'Maybe skip breakfast today, my dear?') but never suggest dropping all meals without offering provision alternatives (like garri, sugar, cornflakes, custard, golden morn)."
        )
    else:
        if combo_data.get("preference_ignored"):
            plan_lines.append(f"NOTE: The student's dietary preference ({profile.get('dietary_pref')}) was ignored because no affordable meals matched it. Explain this to the student kindly.")
        plan_lines.append("Recommended daily meal plan:")
        for idx, (slot_type, combos) in enumerate(combo_data.get("daily_plan", {}).items()):
            if combos:
                plan_lines.append(f"{idx+1}. {slot_type.capitalize()} options:")
                for c_idx, combo in enumerate(combos):
                    plan_lines.append(f"   Option {c_idx+1}: {combo['name']} - ₦{combo['total_price']} (filling score: {combo['filling_score']})")
            else:
                plan_lines.append(f"{idx+1}. {slot_type.capitalize()}: No affordable options.")

    system_prompt = (
        "You are Coach Ngozi, a friendly, street-smart Nigerian aunty who knows Bingham University campus food like the back of your hand.\n"
        "You speak warmly in a mix of English and Pidgin.\n"
        "Your job:\n"
        "Help students manage their feeding budget so they never go hungry.\n"
        "When a student asks about saving, you first calculate how much they can realistically save without harming their health. If the saving target is too aggressive, you disagree firmly and explain why.\n"
        "You know all the life hack spots: Bingham Village is where students get cheap akara, moi-moi, awara, bread, yam, okpa, masa, and suya.\n"
        "You recommend real combos: e.g. 'If you get akara and bread with pap, e go cost you around ₦900 and e go belle full.'\n"
        "When the budget is very tight, you suggest eating provisions (garri, sugar, cornflakes, custard, golden morn) for one or two days to stretch the money. You frame this as a temporary measure.\n"
        "You always mention the exact vendor or location (e.g. 'Mama Bose at Bingham Village') when giving a meal suggestion.\n"
        "You never recommend unrealistic snacks like a single sweet or sachet water as a meal. If the budget is too low for a proper meal, you say so honestly and offer a provision day plan.\n"
        "You are conversational and engaging; you don't just give a budget report. You ask about the student's day, their cravings, and whether they are trying to save for something special.\n\n"
        f"BUDGET STATE & MEAL COMBOS:\n{state_text}\n" + "\n".join(plan_lines)
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(body.chat_history)

    assistant_message = None
    api_key = os.getenv("GROQ_API_KEY")
    openai_fallback_message = "Coach Ngozi is taking a short break. How can I help you today?"

    if api_key:
        try:
            print("coach/advice: using Groq (llama-3.3-70b)")
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=400,
                temperature=0.7,
            )
            msg = response.choices[0].message
            assistant_message = (msg.content if hasattr(msg, "content") else msg.get("content", "")).strip()
        except Exception as exc:
            print(f"coach/advice: Groq request failed, using offline fallback: {exc}")
            assistant_message = openai_fallback_message
    else:
        print("coach/advice: GROQ_API_KEY missing, using offline fallback")
        assistant_message = openai_fallback_message

    suggested = [
        {
            "vendor": m.get("vendor"),
            "item": m.get("item"),
            "price": m.get("price"),
        }
        for m in auto_adjust_plan.get("suggested_meals", [])
    ]

    auto_adjust_output = None
    if needed:
        auto_adjust_output = {
            "needed": True,
            "new_daily_limit": auto_adjust_plan.get("new_daily_limit", 0),
            "sacrifices": auto_adjust_plan.get("sacrifices", []),
            "suggested_meals": suggested,
        }

    return CoachAdviceResponse(message=assistant_message, auto_adjust=auto_adjust_output)
