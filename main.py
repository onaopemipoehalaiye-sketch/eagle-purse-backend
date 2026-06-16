from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import profile, budget, meals, coach, auth, transactions
from utils.loader import load_food_catalog

BASE_DIR = Path(__file__).parent

load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="EaglePurse API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
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
