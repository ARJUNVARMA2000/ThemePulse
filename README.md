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
- **Deployment**: Railway (single service, auto-deploy on push via GitHub)

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
npm run dev
```

The Vite dev server starts at `http://localhost:5173` and proxies `/api` requests to the backend at `http://localhost:8000`.

## Environment Variables

| Variable | Required | Where | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | Yes | Backend / Railway | Your OpenRouter API key |

## Deployment (Railway)

The app deploys as a **single service**: the Dockerfile builds the React frontend, then runs FastAPI which serves both the API and the static files.

### Using Railway CLI

```bash
railway login
railway init -n ThemePulse
railway up
railway domain          # generate a public URL
```

Set your OpenRouter API key:
```bash
railway variables --set "OPENROUTER_API_KEY=sk-or-v1-your-key"
```

### Auto-Deploy on Push

Connect your GitHub repo in the Railway dashboard. Every push to `main` or merged PR triggers an automatic redeploy.

## OpenRouter Models (Fallback Chain)

The app tries these models in order. If one fails, it automatically falls back to the next:

1. `google/gemini-2.0-flash-001`
2. `meta-llama/llama-3.1-8b-instruct`
3. `mistralai/mistral-7b-instruct`
4. `google/gemma-2-9b-it`
5. `qwen/qwen-2.5-7b-instruct`

## License

MIT
