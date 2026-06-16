from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from auth import authenticate_user, create_access_token, create_user, user_profile_payload

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
def signup(data: SignupRequest):
    try:
        user = create_user(
            email=data.email,
            password=data.password,
            monthly_allowance=data.monthly_allowance,
            feeding_budget=data.feeding_budget,
            dietary_pref=data.dietary_pref,
            allowance_period=data.allowance_period,
            meals_per_day=data.meals_per_day,
            meal_times=data.meal_times,
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
def login(data: LoginRequest):
    user = authenticate_user(data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token({"sub": data.email, "email": data.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": data.email,
        "profile": user_profile_payload(user),
    }
