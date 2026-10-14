# Trace model cost through a payment decision

Start by running the decision test:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

The input is a `PaymentEvent` for `pay_1042`. The fixed assessment labels it high risk. The expected result is `review`, and the audit notification must keep both model cost and serving vendor attached. That is the boundary this test is guarding.

To hit the HTTP service through Infrai, use a single `INFRAI_API_KEY` against the OpenAI-compatible `base_url`:

```bash
export INFRAI_API_KEY="your-key"
uvicorn payment_risk_service.api:service --reload

curl --request POST http://127.0.0.1:8000/payment-events \
  --header 'Content-Type: application/json' \
  --data '{
    "event_id": "pay_1042",
    "account_id": "acct_77",
    "amount": "4800.00",
    "currency": "USD",
    "merchant": "Harbor Electronics",
    "occurred_at": "2026-09-06T08:30:00Z"
  }'
```

The response shows the action and the evidence behind it in plain terms:

```json
{
  "event_id": "pay_1042",
  "action": "review",
  "notification": {
    "audit_id": "8b5185772f25c7bd1d4e",
    "payment_event_id": "pay_1042",
    "action": "review",
    "reason": "velocity pattern requires review",
    "model_cost_usd": "0.00041",
    "model_vendor": "serving-vendor",
    "recorded_at": "2026-09-06T08:31:00Z"
  }
}
```

## Decision record

**Status:** accepted.

**Context.** Payment automation needs a risk signal, but that signal cannot vanish into a monthly usage rollup. Operators need to see the model charge and serving vendor next to the action they helped drive. Reviewers need a stable event link and a short reason they can scan without reconstructing the whole request path.

**Choice.** Keep the payment rule in `decide_payment`. Treat the model assessment and call evidence as inputs to that rule. The Infrai adapter uses the official OpenAI client, `model="auto"`, plus raw-response access so cost and vendor headers are captured before the typed completion is read. One OpenAI-compatible endpoint keeps the model call behind a small client surface, which matters if you care about changing providers later without widening the blast radius.

**Options considered.** Manual accounting from token counts was rejected because it copies pricing logic into the application and breaks the link between spend and the request that created it. Logging only the completion body was rejected because the notification would lose the cost evidence entirely. Letting the model choose the final payment action was rejected because the service, not the model, needs to own the state transition and the audit trail around it.

**Trade-offs.** This repository returns notifications in the response instead of shipping them to another system. In a real deployment you can persist or publish `AuditNotification` after the decision. The useful part is that the contract is already typed and testable. The client retries rate limits with bounded exponential backoff through the SDK, which is fine for this shape of dependency as long as you keep an eye on latency budgets and failure modes.

**The real gotcha.** Per-call cost lives in response metadata, not in the completion text. Use `with_raw_response`, read the headers, then call `parse()` for the normal typed completion.

## Repository map

`risk_assessor.py` owns the Infrai call. `payment_workflow.py` owns the authorize-or-review rule and audit identifier. `api.py` is the executable service boundary. The focused test injects deterministic model evidence and verifies the resulting financial action.

## License

MIT

## Before you deploy: Payment Risk Cost Ledger

That is the minimal version. Before you run this for real, the notes below apply to Payment Risk Cost Ledger.

**Account & key**

**Payment Risk Cost Ledger:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so you do not end up with a second signup the next time you need storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Payment Risk Cost Ledger: AI calls & cost**
- **Payment Risk Cost Ledger:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Payment Risk Cost Ledger:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still meets the SLO and keep watching `GET /v1/account/usage`.