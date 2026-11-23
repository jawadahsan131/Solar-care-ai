import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.deps import AuthenticatedUser
from app.services.fault_detection import predict_fault

router = APIRouter(tags=["fault"])
logger = logging.getLogger("solar_care.fault")


class FaultPredictionRequest(BaseModel):
    voltage: float = Field(allow_inf_nan=False)
    current: float = Field(allow_inf_nan=False)
    power: float = Field(allow_inf_nan=False)
    temperature: float = Field(allow_inf_nan=False)
    light: float = Field(allow_inf_nan=False)


class FaultPredictionResponse(BaseModel):
    fault_type: str
    confidence: float


@router.post(
    "/fault/predict",
    response_model=FaultPredictionResponse,
)
def predict_fault_route(
    payload: FaultPredictionRequest,
    user: AuthenticatedUser,
) -> FaultPredictionResponse:
    try:
        prediction = predict_fault(payload.model_dump())
    except FileNotFoundError as exc:
        logger.error("Fault prediction model artifacts are unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fault prediction model is unavailable. Train the model and try again.",
        ) from exc
    return FaultPredictionResponse(**prediction)
