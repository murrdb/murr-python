from __future__ import annotations

import httpx

ARROW_IPC_MIME = "application/vnd.apache.arrow.stream"


def raise_for_status(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    try:
        msg = response.json()["error"]
    except Exception:
        msg = response.text or f"HTTP {response.status_code}"
    if response.status_code == 404:
        raise FileNotFoundError(msg)
    if response.status_code == 409:
        raise ValueError(msg)
    raise RuntimeError(msg)
