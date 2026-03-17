# Trade Opportunities API

A **FastAPI** service that analyses market data for Indian sectors and returns
structured trade-opportunity reports powered by **Google Gemini AI** and live
**DuckDuckGo** web search.

---

## Features

| Feature | Implementation |
|---|---|
| REST API | FastAPI (async) |
| AI Analysis | Google Gemini 1.5 Flash |
| Web Research | DuckDuckGo HTML search (no API key) |
| Authentication | JWT guest tokens (HS256) |
| Rate Limiting | Sliding-window, 10 req / 60 s per user |
| Session Tracking | In-memory per-user history |
| Storage | In-memory only (no database) |
| Docs | Auto-generated Swagger UI & ReDoc |

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- A free [Google Gemini API key](https://aistudio.google.com/app/apikey)

### 2. Clone & install

```bash
git clone <repo-url>
cd trade-api
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY
```

> On Linux/macOS you can also export directly:
> ```bash
> export GEMINI_API_KEY="your_key_here"
> ```

### 4. Run the server

```bash
python run.py
# or
uvicorn app.main:app --reload
```

Server starts at **http://localhost:8000**

---

## API Usage

### Step 1 – Get a guest token

```bash
curl -X POST http://localhost:8000/auth/guest
```

**Response:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 86400,
  "sub": "guest:abc123..."
}
```

---

### Step 2 – Analyse a sector

```bash
curl -H "Authorization: Bearer <your_token>" \
     http://localhost:8000/analyze/pharmaceuticals
```

**Valid sector examples:**
`pharmaceuticals`, `technology`, `agriculture`, `textiles`,
`automotive`, `renewable-energy`, `defence`, `chemicals`

**Response:**
```json
{
  "sector": "pharmaceuticals",
  "report": "# India Pharmaceuticals Sector – Trade Opportunities Report\n\n## 1. Executive Summary\n...",
  "generated_at": "2024-01-15T10:30:00Z",
  "processing_time_seconds": 5.3,
  "rate_limit_remaining": 9
}
```

The `report` field is a full **Markdown document** that can be saved directly as a `.md` file:

```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/analyze/agriculture \
     | python3 -c "import sys,json; print(json.load(sys.stdin)['report'])" \
     > agriculture_report.md
```

---

## Interactive API Docs

| URL | Description |
|---|---|
| http://localhost:8000/docs | Swagger UI (try it live) |
| http://localhost:8000/redoc | ReDoc documentation |
| http://localhost:8000/health | Health check |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Application                  │
│                                                         │
│  POST /auth/guest  ──►  auth.py (JWT mint)              │
│                                                         │
│  GET /analyze/{sector}                                  │
│       │                                                 │
│       ├── auth.py          verify JWT                   │
│       ├── rate_limiter.py  sliding-window check         │
│       ├── session_manager  record request               │
│       └── analyzer.py                                   │
│               │                                         │
│               ├── data_collector.py                     │
│               │       └── DuckDuckGo HTML search        │
│               │           (4 parallel queries)          │
│               │                                         │
│               └── Gemini 1.5 Flash API                  │
│                       └── returns Markdown report       │
└─────────────────────────────────────────────────────────┘
```

### Module responsibilities

| File | Responsibility |
|---|---|
| `app/main.py` | FastAPI app, routing, middleware |
| `app/auth.py` | JWT creation & verification |
| `app/rate_limiter.py` | Sliding-window rate limiter |
| `app/session_manager.py` | In-memory session & history store |
| `app/data_collector.py` | Async DuckDuckGo web search |
| `app/analyzer.py` | Gemini API integration & prompt engineering |
| `app/models.py` | Pydantic request/response schemas |

---

## Security

- **Authentication**: Every analysis request requires a valid Bearer JWT.
- **Input Validation**: Sector name is validated (length, character whitelist).
- **Rate Limiting**: 10 requests per 60-second window per user+IP combination.
- **Error Handling**: All external API failures are caught; meaningful HTTP errors are returned.
- **Secret management**: JWT secret and API key are loaded from env vars, never hard-coded.

> **Production note**: Set a strong `JWT_SECRET` and store `GEMINI_API_KEY`
> in a secrets manager (AWS Secrets Manager, Vault, etc.).

---

## Project Structure

```
trade-api/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app entry
│   ├── auth.py            # JWT auth
│   ├── rate_limiter.py    # Rate limiting
│   ├── session_manager.py # Session tracking
│   ├── data_collector.py  # Web search
│   ├── analyzer.py        # Gemini AI
│   └── models.py          # Pydantic models
├── run.py                 # Dev server launcher
├── requirements.txt
├── .env.example
└── README.md
```

---

## Error Reference

| Status | Meaning |
|---|---|
| 400 | Invalid sector name (length or characters) |
| 401 | Missing, expired, or invalid JWT |
| 429 | Rate limit exceeded – see `retry-after` hint in message |
| 500 | Gemini API failure or unexpected error |
