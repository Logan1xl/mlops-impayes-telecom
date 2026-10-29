"""Contrats d'entrée/sortie de l'API (validation Pydantic = 1re ligne de défense)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CustomerFeatures(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "tenure_months": 47, "avg_monthly_spend_ngn": 38033.69, "recharge_frequency_per_month": 19,
        "payment_consistency_score": 0.61, "late_payment_count": 1,
        "operator": "MTN", "account_type": "prepaid"}})

    tenure_months: int = Field(..., ge=1, le=240, description="Ancienneté du client en mois")
    avg_monthly_spend_ngn: float = Field(..., ge=0, le=1_000_000, description="Dépense mensuelle moyenne (NGN)")
    recharge_frequency_per_month: int = Field(..., ge=0, le=31, description="Nombre de recharges par mois")
    payment_consistency_score: float = Field(..., ge=0, le=1, description="Régularité des paiements [0-1]")
    late_payment_count: int = Field(..., ge=0, le=50, description="Nombre de retards de paiement")
    operator: Literal["MTN", "Airtel", "Glo", "9mobile"]
    account_type: Literal["prepaid", "postpaid"]


class PredictionRequest(CustomerFeatures):
    customer_ref: str | None = Field(None, max_length=64,
                                     description="Référence opaque (jamais le numéro de téléphone)")


class BatchRequest(BaseModel):
    customers: list[PredictionRequest] = Field(..., min_length=1, max_length=1000)


class PredictionResponse(BaseModel):
    request_id: str
    customer_ref: str | None
    default_risk: Literal["low", "medium", "high"]
    probabilities: dict[str, float]
    model_name: str
    model_version: int | str
    latency_ms: float


class BatchResponse(BaseModel):
    predictions: list[PredictionResponse]


class Feedback(BaseModel):
    request_id: str
    actual_default_risk: Literal["low", "medium", "high"]


class ModelInfo(BaseModel):
    model_name: str
    model_version: int | str
    model_type: str | None
    run_id: str | None
    trained_at: str | None
    data_version: str | None
    classes: list[str]
    features: list[str]
