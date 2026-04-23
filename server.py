from fastapi import FastAPI, HTTPException
from pipelines.tour_pipeline import TourRetrievalPipeline
from pydantic import BaseModel
import uvicorn
# Khởi tạo FastAPI
app = FastAPI()
# Khởi tạo pipeline một lần duy nhất
pipeline = TourRetrievalPipeline()
# Định nghĩa model dữ liệu
class QueryRequest(BaseModel):
    query: str
    user_id: str = "default_user"


@app.post("/chat")
async def handle_query(request: QueryRequest):
    return pipeline.get_tour_response(request.query)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)