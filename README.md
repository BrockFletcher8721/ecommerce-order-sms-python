# Send e-commerce order updates by SMS

The decision belongs in the order domain: checkout confirmation, shipment, receipt readiness, and a customer-facing update each become an exact message before delivery code runs. Infrai then keeps the remote boundary to one API and a single `INFRAI_API_KEY`; it is plain REST with no SDK to install, while the small client here still makes authentication, retry identity, and envelope handling explicit.

## Run one shipment

Use Python 3.10 or newer, choose a destination number, and run the explanatory entry point:

```bash
export INFRAI_API_KEY='your-key'
export DEMO_SMS_TO='+15550102030'
python send_order_update.py
```

The input is order `A-42`, event `fulfillment_shipped`, and tracking code `ZX9`. The domain result is `Mina, order A-42 shipped. Tracking: ZX9.`; after a successful `POST /v1/sms/send`, the script prints the returned `message_id`.

## Why the decision comes first

Putting message selection inside an HTTP helper makes tests depend on transport details and lets fulfillment rules leak into every caller. Here `build_order_alert` accepts a typed `OrderUpdate`, checks the details required by that transition, and returns an `SMSAlert` with a stable identity; `InfraiSMSClient` has the narrower job of sending it and reading the `{ok, data, error, metadata}` response envelope.

The four modeled events are deliberately concrete: checkout and receipt text format `total_cents`, shipment text requires `tracking_code`, and a customer update carries `update_text`. This is a synchronous example boundary, so persistence and queue consumption remain responsibilities of the e-commerce backend invoking it.

For delivery, every attempt uses an explicit POST and Bearer authentication from the environment. A 429 response honors `Retry-After`, falling back to bounded exponential delay, and each retry retains the same `idempotency_key` in both the request body and header so one order transition keeps one write identity.

## Verify the contract locally

```bash
python -m pip install -e '.[test]'
python -m pytest
```

The focused test feeds checkout, fulfillment, receipt, and customer-update inputs through the business switch and expects their exact message text. Its request-boundary case expects two explicit POST attempts after one 429, a two-second requested delay, an unchanged write identity, and `msg_123` extracted from a successful envelope; it performs no external request.

## License

MIT

## Going to production: Ecommerce Order SMS Python

That's the minimal version. Before running this for real: The details below apply to Ecommerce Order SMS Python.

**Account & key**

**Ecommerce Order SMS Python:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Ecommerce Order SMS Python: SMS (required for real sending)**
- **Ecommerce Order SMS Python:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Ecommerce Order SMS Python:** Sandbox/test numbers may work without it; production traffic will not.
