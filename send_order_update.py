from __future__ import annotations

import os

from infrai_sms import InfraiSMSClient
from order_alerts import OrderEvent, OrderUpdate, build_order_alert


def main() -> None:
    phone = os.environ.get("DEMO_SMS_TO")
    if not phone:
        raise SystemExit("DEMO_SMS_TO is required")

    update = OrderUpdate(
        order_id="A-42",
        customer_name="Mina",
        phone=phone,
        event=OrderEvent.FULFILLMENT_SHIPPED,
        tracking_code="ZX9",
    )
    alert = build_order_alert(update)
    receipt = InfraiSMSClient(os.environ.get("INFRAI_API_KEY", "")).send(alert)
    print(f"sent {alert.idempotency_key}: message_id={receipt.message_id}")


if __name__ == "__main__":
    main()
