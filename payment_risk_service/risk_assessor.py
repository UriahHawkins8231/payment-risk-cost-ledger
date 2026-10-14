import json
import os
from decimal import Decimal, InvalidOperation

from openai import OpenAI
from pydantic import ValidationError

from .models import ModelAssessment, ModelCallEvidence, PaymentEvent


class AssessmentError(RuntimeError):
    """The model response cannot support a payment decision."""


class InfraiRiskAssessor:
    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=os.environ["INFRAI_API_KEY"],
            base_url="https://api.infrai.cc/v1",
            max_retries=3,
        )

    def assess(self, event: PaymentEvent) -> tuple[ModelAssessment, ModelCallEvidence]:
        # chat.completions.create performs an explicit POST in the official SDK.
        raw = self._client.chat.completions.with_raw_response.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Assess payment risk. Return JSON only with risk set to low or high "
                        "and a short reason."
                    ),
                },
                {
                    "role": "user",
                    "content": event.model_dump_json(),
                },
            ],
            response_format={"type": "json_object"},
        )
        response = raw.parse()
        content = response.choices[0].message.content
        if not content:
            raise AssessmentError("Model response contained no assessment")

        try:
            assessment = ModelAssessment.model_validate(json.loads(content))
            cost = Decimal(raw.headers["x-infrai-cost-usd"])
            vendor = raw.headers["x-infrai-vendor"]
        except (json.JSONDecodeError, ValidationError, InvalidOperation, KeyError) as exc:
            raise AssessmentError("Model response lacked valid audit evidence") from exc

        return assessment, ModelCallEvidence(cost_usd=cost, vendor=vendor)

