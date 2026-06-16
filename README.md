# EaglePurse Backend

This is the FastAPI backend for EaglePurse: AI Budget Coach.

## Run locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set your OpenAI API key in `.env`:

```text
OPENAI_API_KEY=your-key-here
```

3. Start the API:

```bash
uvicorn main:app --reload
```

## Endpoints

- `GET /` - health check
- `GET /api/profile/{user_id}` - demo profile and transactions
- `POST /api/profile/update` - update demo profile budget values
- `GET /api/budget/summary` - budget summary for demo user
- `POST /api/budget/auto-adjust` - auto-adjust budget recommendations
- `GET /api/coach/meal-plan` - meal recommendation based on budget
- `POST /api/coach/advice` - AI coach advice using OpenAI
"# Eagle-purse-backend" 
"# eagle-purse-backend" 
"# eagle-purse-backend" 
"# eagle-purse-backend" 
"# eagle-purse-backend" 
