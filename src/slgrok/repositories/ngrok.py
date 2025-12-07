"""ngrok API repository."""

import httpx

from slgrok.models.requests import CapturedRequest, CapturedRequestList


class NgrokConnectionError(Exception):
    """Raised when unable to connect to ngrok inspector."""

    def __init__(self, base_url: str, original_error: Exception | None = None):
        self.base_url = base_url
        self.original_error = original_error
        message = f"""Cannot connect to ngrok inspector at {base_url}

Possible causes:
  • ngrok is not running
  • ngrok is running on a different port (use --base-url)
  • The inspector interface is disabled

Start ngrok with: ngrok http <port>"""
        super().__init__(message)


class NgrokRepository:
    """Repository for ngrok inspector API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=10.0)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "NgrokRepository":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def health_check(self) -> bool:
        """Check if ngrok inspector is reachable."""
        try:
            response = self._client.get(f"{self.base_url}/api/status")
            return response.status_code == 200
        except httpx.ConnectError:
            return False

    def get_requests(
        self,
        limit: int | None = None,
        tunnel_name: str | None = None,
    ) -> list[CapturedRequest]:
        """Fetch captured requests from ngrok inspector.

        Args:
            limit: Maximum number of requests to return
            tunnel_name: Filter by tunnel name

        Returns:
            List of captured requests
        """
        params: dict[str, str | int] = {}
        if limit is not None:
            params["limit"] = limit
        if tunnel_name is not None:
            params["tunnel_name"] = tunnel_name

        try:
            response = self._client.get(
                f"{self.base_url}/api/requests/http",
                params=params if params else None,
            )
            response.raise_for_status()
            data = CapturedRequestList.model_validate(response.json())
            return data.requests
        except httpx.ConnectError as e:
            raise NgrokConnectionError(self.base_url, e) from e

    def get_request(self, request_id: str) -> CapturedRequest:
        """Fetch a specific request by ID.

        Args:
            request_id: The request ID to fetch

        Returns:
            The captured request
        """
        try:
            response = self._client.get(f"{self.base_url}/api/requests/http/{request_id}")
            response.raise_for_status()
            return CapturedRequest.model_validate(response.json())
        except httpx.ConnectError as e:
            raise NgrokConnectionError(self.base_url, e) from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Request not found: {request_id}") from e
            raise
