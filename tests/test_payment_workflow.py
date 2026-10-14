from datetime import datetime, timezone
from decimal import Decimal

from payment_risk_service.models import (
    ModelAssessment,
    ModelCallEvidence,
    PaymentAction,
    PaymentEvent,
    RiskLevel,
)
from payment_risk_service.payment_workflow import decide_payment


class FixedHighRiskAssessor:
    def assess(self, event: PaymentEvent) -> tuple[ModelAssessment, ModelCallEvidence]:
        assert event.event_id == "pay_1042"
        return (
            ModelAssessment(risk=RiskLevel.HIGH, reason="velocity pattern requires review"),
            ModelCallEvidence(cost_usd=Decimal("0.00041"), vendor="sample-vendor"),
        )


def test_high_risk_payment_records_cost_and_enters_review() -> None:
    event = PaymentEvent(
        event_id="pay_1042",
        account_id="acct_77",
        amount=Decimal("4800.00"),
        currency="USD",
        merchant="Harbor Electronics",
        occurred_at=datetime(2026, 9, 6, 8, 30, tzinfo=timezone.utc),
    )
    recorded_at = datetime(2026, 9, 6, 8, 31, tzinfo=timezone.utc)

    decision = decide_payment(event, FixedHighRiskAssessor(), recorded_at)

    assert decision.action is PaymentAction.REVIEW
    assert decision.notification.payment_event_id == "pay_1042"
    assert decision.notification.model_cost_usd == Decimal("0.00041")
    assert decision.notification.model_vendor == "sample-vendor"
    assert decision.notification.recorded_at == recorded_at
    assert len(decision.notification.audit_id) == 20

