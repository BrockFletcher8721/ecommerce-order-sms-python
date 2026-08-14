from __future__ import annotations

import io
import json
from urllib.error import HTTPError

import pytest

from infrai_sms import InfraiSMSClient
from order_alerts import OrderEvent, OrderUpdate, build_order_alert


@pytest.mark.parametrize(
    ("event", "details", "expected"),
    [
        (OrderEvent.CHECKOUT_CONFIRMED, {"total_cents": 2599}, "Mina, order A-42 is confirmed. Total: $25.99."),
        (OrderEvent.FULFILLMENT_SHIPPED, {"tracking_code": "ZX9"}, "Mina, order A-42 shipped. Tracking: ZX9."),
        (OrderEvent.RECEIPT_READY, {"total_cents": 2599}, "Mina, receipt for order A-42 is ready. Paid: $25.99."),
        (OrderEvent.CUSTOMER_UPDATE, {"update_text": "Pickup is ready."}, "Mina, order A-42: Pickup is ready."),
    ],
)
def test_customer_visible_order_decision(event, details, expected):
    update = OrderUpdate("A-42", "Mina", "+15550102030", event, **details)
    alert = build_order_alert(update)
    assert alert.body == expected
    assert alert.idempotency_key == f"order:A-42:{event.value}"


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_request_retries_429_and_reads_envelope():
    calls = []
    delays = []

    def opener(request, timeout):
        calls.append(request)
        if len(calls) == 1:
            raise HTTPError(
                request.full_url,
                429,
                "rate limited",
                {"Retry-After": "2"},
                io.BytesIO(b'{"ok":false,"error":{"message":"rate limited"}}'),
            )
        return Response(json.dumps({
            "ok": True,
            "data": {"message_id": "msg_123"},
            "error": None,
            "metadata": {"vendor": "selected"},
        }).encode())

    alert = build_order_alert(OrderUpdate(
        "A-42", "Mina", "+15550102030", OrderEvent.FULFILLMENT_SHIPPED,
        tracking_code="ZX9",
    ))
    receipt = InfraiSMSClient(
        "test-key", opener=opener, sleep=delays.append, max_retries=1,
    ).send(alert)

    assert receipt.message_id == "msg_123"
    assert delays == [2.0]
    assert [request.method for request in calls] == ["POST", "POST"]
    assert calls[0].full_url.endswith("/v1/sms/send")
    assert calls[0].headers["Idempotency-key"] == calls[1].headers["Idempotency-key"]
    assert json.loads(calls[0].data) == {
        "to": "+15550102030",
        "body": "Mina, order A-42 shipped. Tracking: ZX9.",
        "idempotency_key": "order:A-42:fulfillment_shipped",
    }
