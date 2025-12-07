"""Pydantic models for ngrok request data."""

from datetime import datetime

from pydantic import BaseModel, RootModel


class HttpHeaders(RootModel[dict[str, list[str]]]):
    """HTTP headers as returned by ngrok API."""

    pass


class RequestData(BaseModel):
    """Incoming HTTP request data."""

    method: str
    proto: str
    headers: HttpHeaders
    uri: str
    raw: str | None = None  # Base64 encoded, can be null


class ResponseData(BaseModel):
    """HTTP response data."""

    status: str
    status_code: int
    proto: str
    headers: HttpHeaders
    raw: str | None = None  # Base64 encoded, can be null


class CapturedRequest(BaseModel):
    """A captured request/response pair from ngrok inspector."""

    uri: str
    id: str
    tunnel_name: str
    remote_addr: str
    start: datetime
    duration: int  # nanoseconds
    request: RequestData
    response: ResponseData | None = None


class CapturedRequestList(BaseModel):
    """Response from GET /api/requests/http."""

    uri: str
    requests: list[CapturedRequest]
