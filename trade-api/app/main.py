"""
Trade Opportunities API
FastAPI service that analyzes market data and provides trade opportunity insights
for specific sectors in India.
"""

import time
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth import create_guest_token, verify_token, TokenResponse
from app.rate_limiter import RateLimiter
from app.analyzer import TradeAnalyzer
from app.session_manager import SessionManager
from app.models import AnalysisResponse, ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# In-memory stores (no database)
rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
session_manager = SessionManager()
analyzer = TradeAnalyzer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Trade Opportunities API starting up...")
    yield
    logger.info("Trade Opportunities API shutting down...")


app = FastAPI(
    title="Trade Opportunities API",
    description=(
        "Analyzes market data and provides trade opportunity insights "
        "for specific sectors in India. Powered by Gemini AI."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            status_code=exc.status_code,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error. Please try again later.",
            status_code=500,
        ).model_dump(),
    )


# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.post(
    "/auth/guest",
    response_model=TokenResponse,
    summary="Get a guest access token",
    tags=["Authentication"],
)
async def get_guest_token():
    """
    Obtain a guest JWT token to authenticate subsequent API calls.
    Tokens are valid for 24 hours.
    """
    token_data = create_guest_token()
    session_id = str(uuid.uuid4())
    session_manager.create_session(session_id, token_data["sub"])
    logger.info("Guest token issued for session %s", session_id)
    return token_data


# ── Core endpoint ─────────────────────────────────────────────────────────────

@app.get(
    "/analyze/{sector}",
    response_model=AnalysisResponse,
    summary="Analyze trade opportunities for a sector",
    tags=["Analysis"],
    responses={
        200: {"description": "Structured markdown market analysis report"},
        400: {"model": ErrorResponse, "description": "Invalid sector name"},
        401: {"model": ErrorResponse, "description": "Missing or invalid token"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def analyze_sector(
    sector: str,
    request: Request,
    authorization: str = Header(..., description="Bearer <token>"),
):
    """
    Analyze trade opportunities for the given Indian market sector.

    - **sector**: Name of the sector (e.g. `pharmaceuticals`, `technology`, `agriculture`)

    Returns a comprehensive markdown report covering:
    - Market overview
    - Export/import opportunities
    - Key players
    - Risks & challenges
    - Strategic recommendations
    """
    # ── Authenticate ──────────────────────────────────────────────────────────
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format. Use: Bearer <token>")

    token = authorization.split(" ", 1)[1]
    payload = verify_token(token)
    user_id: str = payload.get("sub", "unknown")

    # ── Rate-limit ────────────────────────────────────────────────────────────
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{user_id}:{client_ip}"

    allowed, remaining, reset_in = rate_limiter.check(rate_key)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {reset_in} seconds.",
        )

    # ── Validate sector ───────────────────────────────────────────────────────
    cleaned = sector.strip().lower()
    if not cleaned or len(cleaned) < 2 or len(cleaned) > 60:
        raise HTTPException(
            status_code=400,
            detail="Sector name must be between 2 and 60 characters.",
        )
    if not all(c.isalpha() or c in " -_" for c in cleaned):
        raise HTTPException(
            status_code=400,
            detail="Sector name may only contain letters, spaces, hyphens, or underscores.",
        )

    # ── Session tracking ──────────────────────────────────────────────────────
    session_manager.record_request(user_id, cleaned)
    logger.info("Sector analysis requested | user=%s sector=%s ip=%s", user_id, cleaned, client_ip)

    start = time.time()

    # ── Run analysis ──────────────────────────────────────────────────────────
    try:
        report_md = await analyzer.generate_report(cleaned)
    except Exception as exc:
        logger.exception("Analysis failed for sector '%s': %s", cleaned, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis pipeline failed: {exc}",
        ) from exc

    elapsed = round(time.time() - start, 2)
    logger.info("Report generated | sector=%s elapsed=%ss", cleaned, elapsed)

    return AnalysisResponse(
        sector=cleaned,
        report=report_md,
        generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        processing_time_seconds=elapsed,
        rate_limit_remaining=remaining,
    )


# ── Health / info endpoints ───────────────────────────────────────────────────

@app.get("/health", tags=["System"], summary="Health check")
async def health():
    return {"status": "ok", "timestamp": time.time()}


@app.get("/", tags=["System"], summary="API info")
async def root():
    return {
        "name": "Trade Opportunities API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "usage": {
            "step1": "POST /auth/guest  → obtain Bearer token",
            "step2": "GET /analyze/{sector} with Authorization: Bearer <token>",
        },
    }
