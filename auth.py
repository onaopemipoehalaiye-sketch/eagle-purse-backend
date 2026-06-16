import json
import os
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv("SECRET_KEY", "eaglepurse-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ---------------------------------------------------------------------------
# File-based persistence so users and transactions survive server restarts
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent / "data"
USERS_FILE = _DATA_DIR / "users.json"
TRANSACTIONS_FILE = _DATA_DIR / "user_transactions.json"

write_lock = threading.Lock()


def _load_users() -> dict[str, dict[str, Any]]:
    if USERS_FILE.exists():
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_users() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with write_lock:
        fd, tmp = tempfile.mkstemp(dir=_DATA_DIR, suffix=".tmp")
        try:
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(users, f, indent=2, default=str)
            os.replace(tmp, USERS_FILE)
        except Exception:
            os.unlink(tmp)
            raise


def _load_transactions() -> dict[str, list[dict[str, Any]]]:
    if TRANSACTIONS_FILE.exists():
        with open(TRANSACTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_transactions() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with write_lock:
        fd, tmp = tempfile.mkstemp(dir=_DATA_DIR, suffix=".tmp")
        try:
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(user_transactions, f, indent=2, default=str)
            os.replace(tmp, TRANSACTIONS_FILE)
        except Exception:
            os.unlink(tmp)
            raise


users: dict[str, dict[str, Any]] = _load_users()
user_transactions: dict[str, list[dict[str, Any]]] = _load_transactions()


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


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


def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    return users.get(email)


def get_user_transactions(email: str) -> list[dict[str, Any]]:
    return user_transactions.get(email, [])


def create_user(
    email: str,
    password: str,
    monthly_allowance: float,
    feeding_budget: float,
    dietary_pref: str | None = None,
    allowance_period: str = "monthly",
    meals_per_day: int = 3,
    meal_times: list[str] | None = None,
    transactions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if email in users:
        raise ValueError("Email already registered")

    password_hash = get_password_hash(password)
    actual_meal_times = meal_times if meal_times is not None else ["breakfast", "lunch", "dinner"]
    user = {
        "email": email,
        "password_hash": password_hash,
        "monthly_allowance": monthly_allowance,
        "feeding_budget": feeding_budget,
        "dietary_pref": dietary_pref,
        "allowance_period": allowance_period,
        "meals_per_day": len(actual_meal_times),
        "meal_times": actual_meal_times,
    }
    users[email] = user
    user_transactions[email] = transactions or []
    _save_users()
    _save_transactions()
    return user


def verify_user(email: str, password: str) -> Optional[dict[str, Any]]:
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def authenticate_user(email: str, password: str) -> Optional[dict[str, Any]]:
    return verify_user(email, password)


def user_profile_payload(user: dict[str, Any]) -> dict[str, Any]:
    actual_meal_times = user.get("meal_times")
    if actual_meal_times is None:
        # Backward compatibility fallback
        old_meals = user.get("meals_per_day", 3)
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
            
    return {
        "email": user["email"],
        "monthly_allowance": user["monthly_allowance"],
        "feeding_budget": user["feeding_budget"],
        "dietary_pref": user.get("dietary_pref"),
        "allowance_period": user.get("allowance_period", "monthly"),
        "meals_per_day": len(actual_meal_times),
        "meal_times": actual_meal_times,
    }


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    payload = decode_access_token(token)
    email = payload.get("sub") or payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
