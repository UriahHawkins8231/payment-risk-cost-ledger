from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    HIGH = "high"


class PaymentAction(str, Enum):
    AUTHORIZE = "authorize"
    REVIEW = "review"


class PaymentEvent(BaseModel):
    event_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    merchant: str = Field(min_length=1)
    occurred_at: datetime


class ModelAssessment(BaseModel):
    risk: RiskLevel
    reason: str = Field(min_length=1)


class ModelCallEvidence(BaseModel):
    cost_usd: Decimal
    vendor: str


class AuditNotification(BaseModel):
    audit_id: str
    payment_event_id: str
    action: PaymentAction
    reason: str
    model_cost_usd: Decimal
    model_vendor: str
    recorded_at: datetime


class PaymentDecision(BaseModel):
    event_id: str
    action: PaymentAction
    notification: AuditNotification

