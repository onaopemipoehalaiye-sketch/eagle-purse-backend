from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os

from routers import profile, budget, meals, coach, auth, transactions
from utils.loader import load_food_catalog

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="EaglePurse API")

# Session middleware is required by SQLAdmin authentication
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "eaglepurse-secret-key"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://eagle-purse-frontend.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount SQLAdmin — must be done after middleware is added
from database import engine
from admin import create_admin
create_admin(app, engine)


@app.on_event("startup")
async def startup_event():
    # Auto-create tables if they don't exist (safe to run every startup)
    from models import Base
    from database import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.food_df = load_food_catalog()


@app.get("/")
def root():
    return {"message": "EaglePurse API running"}


app.include_router(auth.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(budget.router, prefix="/api")
app.include_router(meals.router, prefix="/api")
app.include_router(coach.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
