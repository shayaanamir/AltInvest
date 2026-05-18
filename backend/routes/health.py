from fastapi import APIRouter
from models.schemas import HealthResponse

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok", "version": "1.0"}
