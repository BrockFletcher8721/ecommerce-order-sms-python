from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OrderEvent(str, Enum):
    CHECKOUT_CONFIRMED = "checkout_confirmed"
    FULFILLMENT_SHIPPED = "fulfillment_shipped"
    RECEIPT_READY = "receipt_ready"
    CUSTOMER_UPDATE = "customer_update"


@dataclass(frozen=True)
class OrderUpdate:
    order_id: str
    customer_name: str
    phone: str
    event: OrderEvent
    total_cents: int | None = None
    tracking_code: str | None = None
    update_text: str | None = None


@dataclass(frozen=True)
class SMSAlert:
    to: str
    body: str
    idempotency_key: str


def build_order_alert(update: OrderUpdate) -> SMSAlert:
    """Turn a customer-visible order transition into one deterministic alert."""
    if not update.order_id.strip() or not update.phone.strip():
        raise ValueError("order_id and phone are required")

    prefix = f"{update.customer_name}, " if update.customer_name.strip() else ""
    if update.event is OrderEvent.CHECKOUT_CONFIRMED:
        if update.total_cents is None or update.total_cents < 0:
            raise ValueError("checkout confirmation requires total_cents")
        body = (
            f"{prefix}order {update.order_id} is confirmed. "
            f"Total: ${update.total_cents / 100:.2f}."
        )
    elif update.event is OrderEvent.FULFILLMENT_SHIPPED:
        if not update.tracking_code:
            raise ValueError("shipment requires tracking_code")
        body = (
            f"{prefix}order {update.order_id} shipped. "
            f"Tracking: {update.tracking_code}."
        )
    elif update.event is OrderEvent.RECEIPT_READY:
        if update.total_cents is None or update.total_cents < 0:
            raise ValueError("receipt requires total_cents")
        body = (
            f"{prefix}receipt for order {update.order_id} is ready. "
            f"Paid: ${update.total_cents / 100:.2f}."
        )
    else:
        if not update.update_text:
            raise ValueError("customer update requires update_text")
        body = f"{prefix}order {update.order_id}: {update.update_text}"

    return SMSAlert(
        to=update.phone,
        body=body,
        idempotency_key=f"order:{update.order_id}:{update.event.value}",
    )
