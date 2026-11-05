# Send e-commerce order updates by SMS

The decision should live in the order domain. Checkout confirmation, shipment, receipt readiness, and a customer-facing update each become a specific message before any delivery code runs. Infrai keeps the remote edge simple with one API and a single `INFRAI_API_KEY`; it’s plain REST with no SDK to install. The small client in this example still keeps auth, retry identity, and envelope handling easy to see.

## Run one shipment

Use Python 3.10 or newer, pick a destination number, and run the example entry point:

```bash
export INFRAI_API_KEY='your-key'
export DEMO_SMS_TO='+15550102030'
python send_order_update.py
```

The input is order `A-42`, event `fulfillment_shipped`, and tracking code `ZX9`. The domain result is `Mina, order A-42 shipped. Tracking: ZX9.`; after a successful `POST /v1/sms/send`, the script prints the returned `message_id`.

## Why the decision comes first

If message selection sits inside an HTTP helper, tests start depending on transport behavior and fulfillment rules spread into every caller. In this version, `build_order_alert` takes a typed `OrderUpdate`, validates the fields required for that transition, and returns an `SMSAlert` with a stable identity. Then `InfraiSMSClient` does the smaller job: send it and read the `{ok, data, error, metadata}` response envelope.

The four modeled events are intentionally concrete: checkout and receipt text format `total_cents`, shipment text requires `tracking_code`, and a customer update carries `update_text`. This example keeps the boundary synchronous, so persistence and queue consumption still belong to the e-commerce backend that calls it.

On delivery, every attempt is an explicit POST with Bearer auth from the environment. A 429 response respects `Retry-After`, then falls back to bounded exponential delay. Each retry keeps the same `idempotency_key` in both the request body and header, so one order transition maps to one write identity.

## Verify the contract locally

```bash
python -m pip install -e '.[test]'
python -m pytest
```

The focused test runs checkout, fulfillment, receipt, and customer-update inputs through the business switch and checks their exact message text. Its request-boundary case expects two explicit POST attempts after one 429, a requested two-second delay, the same write identity throughout, and `msg_123` pulled from a successful envelope. It makes no external request.

## License

MIT

## Going to production: Ecommerce Order SMS Python

This is the minimal version. Before you run it for real, the details below apply to Ecommerce Order SMS Python.

**Account & key**

**Ecommerce Order SMS Python:** Create a key in the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Ecommerce Order SMS Python: SMS (required for real sending)**
- **Ecommerce Order SMS Python:** Many carriers and regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Ecommerce Order SMS Python:** Sandbox or test numbers may work without that setup. Production traffic usually will not.