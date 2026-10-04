from __future__ import annotations

import httpx


class MurrError(Exception):
    """Base class for errors returned by the Murr server."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class TableNotFoundError(MurrError):
    """The table does not exist."""


class TableAlreadyExistsError(MurrError):
    """A table with this name already exists."""


class InvalidRequestError(MurrError):
    """The server rejected the request: bad schema, wrong key types, unknown column."""


class ServerError(MurrError):
    """The server failed to process the request."""


def raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    status = response.status_code
    try:
        message = response.json()["error"]
    except (ValueError, KeyError, TypeError):
        message = response.text or response.reason_phrase
    if status == 404:
        raise TableNotFoundError(status, message)
    if status == 409:
        raise TableAlreadyExistsError(status, message)
    if status < 500:
        raise InvalidRequestError(status, message)
    raise ServerError(status, message)
