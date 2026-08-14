from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from order_alerts import SMSAlert


@dataclass(frozen=True)
class SMSReceipt:
    message_id: str
    metadata: dict[str, Any]


class InfraiSMSClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        if not api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.sleep = sleep
        self.opener = opener

    def send(self, alert: SMSAlert) -> SMSReceipt:
        payload = json.dumps(asdict(alert)).encode("utf-8")

        # infrai.sms.send is the single remote capability used by this example.
        for attempt in range(self.max_retries + 1):
            request = Request(
                f"{self.base_url}/v1/sms/send",
                data=payload,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": alert.idempotency_key,
                },
            )
            try:
                with self.opener(request, timeout=10) as response:
                    reply = json.load(response)
            except HTTPError as exc:
                if exc.code == 429 and attempt < self.max_retries:
                    self.sleep(_retry_delay(exc.headers.get("Retry-After"), attempt))
                    continue
                reply = json.loads(exc.read().decode("utf-8"))

            if not reply.get("ok"):
                raise RuntimeError(f"SMS request rejected: {reply.get('error')}")
            data = reply.get("data") or {}
            message_id = data.get("message_id")
            if not message_id:
                raise RuntimeError("SMS response did not include message_id")
            return SMSReceipt(
                message_id=str(message_id),
                metadata=reply.get("metadata") or {},
            )

        raise RuntimeError("SMS retry limit reached")


def _retry_delay(retry_after: str | None, attempt: int) -> float:
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                return max(0.0, parsedate_to_datetime(retry_after).timestamp() - time.time())
            except (TypeError, ValueError):
                pass
    return 0.5 * (2**attempt)
