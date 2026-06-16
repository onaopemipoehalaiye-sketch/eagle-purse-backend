import os
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Transaction, User

SECRET_KEY = os.getenv("SECRET_KEY", "eaglepurse-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ---------------------------------------------------------------------------
# DB helpers — all async
# ---------------------------------------------------------------------------

async def get_user_by_email(email: str, db: AsyncSession) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_transactions(email: str, db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(
        select(Transaction).where(Transaction.user_email == email)
    )
    rows = result.scalars().all()
    return [
        {
            "date": tx.date,
            "category": tx.category,
            "vendor": tx.vendor,
            "item": tx.item,
            "amount": tx.amount,
        }
        for tx in rows
    ]


async def create_user(
    email: str,
    password: str,
    monthly_allowance: float,
    feeding_budget: float,
    db: AsyncSession,
    dietary_pref: str | None = None,
    allowance_period: str = "monthly",
    meals_per_day: int = 3,
    meal_times: list[str] | None = None,
) -> User:
    existing = await get_user_by_email(email, db)
    if existing:
        raise ValueError("Email already registered")

    actual_meal_times = meal_times if meal_times is not None else ["breakfast", "lunch", "dinner"]
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        monthly_allowance=monthly_allowance,
        feeding_budget=feeding_budget,
        dietary_pref=dietary_pref,
        allowance_period=allowance_period,
        meals_per_day=len(actual_meal_times),
        meal_times=actual_meal_times,
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(email: str, password: str, db: AsyncSession) -> Optional[User]:
    user = await get_user_by_email(email, db)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def user_profile_payload(user: User) -> dict[str, Any]:
    meal_times = user.meal_times or ["breakfast", "lunch", "dinner"]
    return {
        "email": user.email,
        "monthly_allowance": user.monthly_allowance,
        "feeding_budget": user.feeding_budget,
        "dietary_pref": user.dietary_pref,
        "allowance_period": user.allowance_period or "monthly",
        "meals_per_day": len(meal_times),
        "meal_times": meal_times,
    }


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    email = payload.get("sub") or payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_by_email(email, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
