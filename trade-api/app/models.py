from pydantic import BaseModel, Field
from typing import Optional


class AnalysisResponse(BaseModel):
    sector: str = Field(..., description="The sector that was analyzed")
    report: str = Field(..., description="Full market analysis report in Markdown format")
    generated_at: str = Field(..., description="UTC timestamp of report generation")
    processing_time_seconds: float = Field(..., description="Time taken to generate the report")
    rate_limit_remaining: int = Field(..., description="Remaining requests in the current window")

    model_config = {"json_schema_extra": {
        "example": {
            "sector": "pharmaceuticals",
            "report": "# India Pharmaceuticals Sector – Trade Opportunities Report\n\n...",
            "generated_at": "2024-01-01T12:00:00Z",
            "processing_time_seconds": 4.2,
            "rate_limit_remaining": 9,
        }
    }}


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    detail: Optional[str] = Field(None, description="Additional detail")
