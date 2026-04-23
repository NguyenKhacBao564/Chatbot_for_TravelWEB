from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from pipelines.tour_pipeline import TourRetrievalPipeline


app = FastAPI(title="Vietnamese Travel Chatbot API")
pipeline = None


class QueryRequest(BaseModel):
    query: str
    user_id: str = "default_user"


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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
