"""
One-shot migration script: reads data/users.json and data/user_transactions.json
and inserts all records into the PostgreSQL database.

Run AFTER running: alembic upgrade head

Usage:
    python migrate_json_to_db.py
"""

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

from database import AsyncSessionLocal
from models import Transaction, User
from auth import get_password_hash

USERS_FILE = BASE_DIR / "data" / "users.json"
TRANSACTIONS_FILE = BASE_DIR / "data" / "user_transactions.json"


async def migrate():
    users_data: dict = {}
    transactions_data: dict = {}

    if USERS_FILE.exists():
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users_data = json.load(f)
        print(f"Found {len(users_data)} users in {USERS_FILE}")
    else:
        print(f"No users file found at {USERS_FILE}, skipping.")

    if TRANSACTIONS_FILE.exists():
        with open(TRANSACTIONS_FILE, "r", encoding="utf-8") as f:
            transactions_data = json.load(f)
        print(f"Found {len(transactions_data)} user transaction sets in {TRANSACTIONS_FILE}")
    else:
        print(f"No transactions file found at {TRANSACTIONS_FILE}, skipping.")

    async with AsyncSessionLocal() as session:
        user_count = 0
        tx_count = 0

        for email, user_dict in users_data.items():
            from sqlalchemy import select
            result = await session.execute(select(User).where(User.email == email))
            existing = result.scalar_one_or_none()
            if existing:
                print(f"  [SKIP] User {email} already exists in DB.")
                continue

            meal_times = user_dict.get("meal_times") or ["breakfast", "lunch", "dinner"]
            user = User(
                email=email,
                password_hash=user_dict.get("password_hash", get_password_hash("changeme")),
                monthly_allowance=float(user_dict.get("monthly_allowance", 0)),
                feeding_budget=float(user_dict.get("feeding_budget", 0)),
                dietary_pref=user_dict.get("dietary_pref"),
                allowance_period=user_dict.get("allowance_period", "monthly"),
                meals_per_day=len(meal_times),
                meal_times=meal_times,
            )
            session.add(user)
            user_count += 1
            print(f"  [INSERT] User: {email}")

        await session.flush()  # flush users before inserting FKs

        for email, tx_list in transactions_data.items():
            if email not in users_data and email not in []:
                print(f"  [WARN] Transactions for {email} but no matching user — skipping.")
                continue
            for tx in tx_list:
                transaction = Transaction(
                    user_email=email,
                    date=str(tx.get("date", "")),
                    category=tx.get("category", ""),
                    vendor=tx.get("vendor", ""),
                    item=tx.get("item", ""),
                    amount=float(tx.get("amount", 0)),
                )
                session.add(transaction)
                tx_count += 1

        await session.commit()
        print(f"\n✅ Migration complete: {user_count} users and {tx_count} transactions inserted.")


if __name__ == "__main__":
    asyncio.run(migrate())
