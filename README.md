# ThemePulse

Live classroom theme extraction tool. A professor posts a question, students submit answers via a QR code link, and an LLM (via OpenRouter) auto-summarizes responses into themed cards with student attribution.

## How It Works

1. **Professor** creates a session with a question
2. **Students** scan the QR code or open the link to submit their answers
3. **AI** automatically summarizes responses into 4-6 key themes every 10 seconds
4. **Dashboard** displays theme cards with titles, descriptions, and student names

## Tech Stack

- **Backend**: Python / FastAPI with SSE for real-time updates
- **Frontend**: React / Vite / TypeScript
- **AI**: OpenRouter API with 5-model fallback chain
- **Deployment**: Railway (auto-deploy on push via GitHub)

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- An [OpenRouter](https://openrouter.ai/) API key

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Create .env file
cp .env.example .env
# Default VITE_API_URL=http://localhost:8000 should work for local dev

npm run dev
```

Visit `http://localhost:5173` to use the app.

## Environment Variables

### Backend

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | Your OpenRouter API key |
| `FRONTEND_URL` | No | Frontend URL for CORS/QR codes (defaults to `http://localhost:5173`) |

### Frontend

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | No | Backend API URL (defaults to `http://localhost:8000`) |

## Deployment (Railway)

### Using Railway CLI

```bash
# Login (if not already)
railway login

# Initialize project
railway init

# Link to the project
railway link

# Deploy
railway up
```

### Auto-Deploy on Push

Once the GitHub repo is connected to Railway, every push to `main` or merged PR triggers an automatic redeploy.

### Services

- **backend** — FastAPI app serving the API at `/api/*`
- **frontend** — Static React build served via `serve`

Set `OPENROUTER_API_KEY` in the backend service environment variables through the Railway dashboard or CLI.

## OpenRouter Models (Fallback Chain)

The app tries these models in order. If one fails, it automatically falls back to the next:

1. `google/gemini-2.0-flash-001`
2. `meta-llama/llama-3.1-8b-instruct`
3. `mistralai/mistral-7b-instruct`
4. `google/gemma-2-9b-it`
5. `qwen/qwen-2.5-7b-instruct`

## License

MIT
