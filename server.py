import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
import uvicorn

from pipelines.tour_pipeline import TourRetrievalPipeline


app = FastAPI(title="Vietnamese Travel Chatbot API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:4173",
        "http://localhost:5173",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
pipeline = None


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    user_id: str = Field(default="default_user", min_length=1, max_length=100)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be empty")
        return stripped

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("user_id must not be empty")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", stripped):
            raise ValueError("user_id must contain only letters, numbers, underscores, or hyphens")
        return stripped


class ResetSessionRequest(BaseModel):
    user_id: str = Field(default="default_user", min_length=1, max_length=100)

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("user_id must not be empty")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", stripped):
            raise ValueError("user_id must contain only letters, numbers, underscores, or hyphens")
        return stripped


def get_pipeline() -> TourRetrievalPipeline:
    global pipeline
    if pipeline is None:
        pipeline = TourRetrievalPipeline()
    return pipeline


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def handle_query(request: QueryRequest):
    return get_pipeline().get_tour_response(request.query, user_id=request.user_id)


@app.post("/reset")
async def reset_session(request: ResetSessionRequest):
    get_pipeline().reset_session(request.user_id)
    return {
        "status": "ok",
        "message": "Session reset successfully.",
        "user_id": request.user_id,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
