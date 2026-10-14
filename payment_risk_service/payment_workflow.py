from datetime import datetime, timezone
from hashlib import sha256
from typing import Protocol

from .models import (
    AuditNotification,
    ModelAssessment,
    ModelCallEvidence,
    PaymentAction,
    PaymentDecision,
    PaymentEvent,
    RiskLevel,
)


class RiskAssessor(Protocol):
    def assess(self, event: PaymentEvent) -> tuple[ModelAssessment, ModelCallEvidence]:
        """Return a typed assessment and its call evidence."""


def decide_payment(
    event: PaymentEvent,
    assessor: RiskAssessor,
    recorded_at: datetime | None = None,
) -> PaymentDecision:
    assessment, evidence = assessor.assess(event)
    action = (
        PaymentAction.REVIEW
        if assessment.risk is RiskLevel.HIGH
        else PaymentAction.AUTHORIZE
    )
    audit_id = sha256(
        f"{event.event_id}:{action.value}:{assessment.reason}".encode()
    ).hexdigest()[:20]
    notification = AuditNotification(
        audit_id=audit_id,
        payment_event_id=event.event_id,
        action=action,
        reason=assessment.reason,
        model_cost_usd=evidence.cost_usd,
        model_vendor=evidence.vendor,
        recorded_at=recorded_at or datetime.now(timezone.utc),
    )
    return PaymentDecision(
        event_id=event.event_id,
        action=action,
        notification=notification,
    )
