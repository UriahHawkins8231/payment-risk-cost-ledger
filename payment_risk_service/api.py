from fastapi import FastAPI, HTTPException
from openai import APIStatusError

from .models import PaymentDecision, PaymentEvent
from .payment_workflow import decide_payment
from .risk_assessor import AssessmentError, InfraiRiskAssessor


service = FastAPI(title="Payment risk cost ledger")


@service.post("/payment-events", response_model=PaymentDecision)
def receive_payment(event: PaymentEvent) -> PaymentDecision:
    try:
        return decide_payment(event, InfraiRiskAssessor())
    except AssessmentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except APIStatusError as exc:
        status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
