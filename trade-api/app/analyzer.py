"""
AI Analyzer – uses Google Gemini API to generate structured
trade-opportunity reports from collected web data.
"""

import os
import logging
import textwrap
from typing import Optional

import httpx

from app.data_collector import collect_sector_data

logger = logging.getLogger(__name__)

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)
_TIMEOUT = 60  # seconds


def _build_prompt(sector: str, web_data: str) -> str:
    return textwrap.dedent(f"""
        You are a senior trade and market analyst specialising in the Indian economy.
        Your task is to produce a **comprehensive, actionable trade opportunities report**
        for the **{sector.title()} sector in India**.

        Use the web research snippets below as supplementary context. Synthesise them with
        your own knowledge to produce an authoritative report. Do NOT simply paraphrase
        the snippets; provide genuine analytical depth.

        ---
        ## Web Research Snippets
        {web_data}
        ---

        ## Report Structure (use exactly these headings)

        # India {sector.title()} Sector – Trade Opportunities Report

        ## 1. Executive Summary
        A 3–4 sentence overview of the sector's current trade standing.

        ## 2. Market Overview
        - Market size (current & projected)
        - Key growth drivers
        - Recent policy developments (e.g. PLI schemes, FTAs, tariff changes)

        ## 3. Export Opportunities
        - Top export destinations and demand trends
        - High-potential product/service sub-categories
        - Competitive advantages India holds

        ## 4. Import Opportunities & Dependencies
        - Critical imports and sourcing gaps
        - Potential for import substitution

        ## 5. Key Players & Ecosystem
        - Major Indian companies / MSMEs
        - Government bodies & industry associations

        ## 6. Risks & Challenges
        - Regulatory, logistical, geopolitical, or competitive risks

        ## 7. Strategic Recommendations
        - 3–5 concrete, actionable recommendations for exporters/investors

        ## 8. Data Snapshot
        Present a small markdown table with key metrics (market size, CAGR, top export
        partner, top import partner, notable government scheme).

        ---
        Write in crisp, professional English. Use bullet points within sections where
        appropriate. Include approximate figures where known; flag uncertainty clearly.
        Do not add any text before the `#` heading or after the table.
    """).strip()


async def _call_gemini(prompt: str) -> str:
    """Call the Gemini API and return the generated text."""
    if not _GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please export it before starting the server."
        )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 4096,
        },
    }
    params = {"key": _GEMINI_API_KEY}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(_GEMINI_URL, json=payload, params=params)

    if resp.status_code != 200:
        body = resp.text[:400]
        logger.error("Gemini API error %s: %s", resp.status_code, body)
        raise RuntimeError(f"Gemini API returned {resp.status_code}: {body}")

    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()
    except (KeyError, IndexError) as exc:
        logger.error("Unexpected Gemini response structure: %s", data)
        raise RuntimeError("Could not parse Gemini response.") from exc


class TradeAnalyzer:
    """Orchestrates data collection → LLM analysis → report generation."""

    async def generate_report(self, sector: str) -> str:
        # 1. Collect web data
        logger.info("Collecting web data for sector: %s", sector)
        web_data = await collect_sector_data(sector)
        summary_text: str = web_data["summary_text"]

        # 2. Build prompt
        prompt = _build_prompt(sector, summary_text)

        # 3. Call Gemini
        logger.info("Calling Gemini API for sector: %s", sector)
        report = await _call_gemini(prompt)

        return report
