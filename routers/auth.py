from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from auth import authenticate_user, create_access_token, create_user, user_profile_payload
from database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: str
    password: str
    monthly_allowance: float
    feeding_budget: float
    dietary_pref: str | None = None
    allowance_period: str = "monthly"
    meals_per_day: int = 3
    meal_times: list[str] = ["breakfast", "lunch", "dinner"]


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    profile: dict


@router.post("/signup", response_model=TokenResponse)
async def signup(data: SignupRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await create_user(
            email=data.email,
            password=data.password,
            monthly_allowance=data.monthly_allowance,
            feeding_budget=data.feeding_budget,
            dietary_pref=data.dietary_pref,
            allowance_period=data.allowance_period,
            meals_per_day=data.meals_per_day,
            meal_times=data.meal_times,
            db=db,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    token = create_access_token({"sub": data.email, "email": data.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": data.email,
        "profile": user_profile_payload(user),
    }


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(data.email, data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token({"sub": data.email, "email": data.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": data.email,
        "profile": user_profile_payload(user),
    }
