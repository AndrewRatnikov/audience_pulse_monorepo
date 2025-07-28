from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from pydantic import BaseModel
from .config import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

app = FastAPI(
  title="Audience Pulse Backend API (MVP)",
  description="API for analyzing public social media data.",
  version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
  logger.info("Root endpoint accessed.")
  return {"message": "Audience Pulse API is live"}


class AnalyzeRequestModel(BaseModel):
    link: str

@app.post("/analyze")
async def analyze_placeholder(requested_data: AnalyzeRequestModel):
    logger.info(f"Received analysis request for link: {requested_data.link}")
    return {"status": "Analysis request received (placeholder)", "link": requested_data.link}