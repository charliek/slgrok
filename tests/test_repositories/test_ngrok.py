"""Tests for ngrok repository."""

import httpx
import pytest
from pytest_mock import MockerFixture

from slgrok.models.requests import CapturedRequest
from slgrok.repositories.ngrok import NgrokConnectionError, NgrokRepository


class TestNgrokRepository:
    """Tests for NgrokRepository."""

    def test_init(self) -> None:
        """Test repository initialization."""
        repo = NgrokRepository("http://localhost:4040")
        assert repo.base_url == "http://localhost:4040"
        repo.close()

    def test_init_strips_trailing_slash(self) -> None:
        """Test that trailing slash is stripped from base URL."""
        repo = NgrokRepository("http://localhost:4040/")
        assert repo.base_url == "http://localhost:4040"
        repo.close()

    def test_context_manager(self) -> None:
        """Test context manager usage."""
        with NgrokRepository("http://localhost:4040") as repo:
            assert repo.base_url == "http://localhost:4040"

    def test_get_requests_success(
        self,
        mocker: MockerFixture,
        sample_requests_json: dict,
    ) -> None:
        """Test successful request retrieval."""
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_requests_json
        mock_response.raise_for_status = mocker.Mock()

        mock_client = mocker.Mock()
        mock_client.get.return_value = mock_response

        with NgrokRepository("http://localhost:4040") as repo:
            repo._client = mock_client
            requests = repo.get_requests()

        assert len(requests) == 3
        assert all(isinstance(r, CapturedRequest) for r in requests)
        mock_client.get.assert_called_once_with(
            "http://localhost:4040/api/requests/http",
            params=None,
        )

    def test_get_requests_with_limit(
        self,
        mocker: MockerFixture,
        sample_requests_json: dict,
    ) -> None:
        """Test request retrieval with limit parameter."""
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_requests_json
        mock_response.raise_for_status = mocker.Mock()

        mock_client = mocker.Mock()
        mock_client.get.return_value = mock_response

        with NgrokRepository("http://localhost:4040") as repo:
            repo._client = mock_client
            repo.get_requests(limit=10)

        mock_client.get.assert_called_once_with(
            "http://localhost:4040/api/requests/http",
            params={"limit": 10},
        )

    def test_get_requests_with_tunnel_name(
        self,
        mocker: MockerFixture,
        sample_requests_json: dict,
    ) -> None:
        """Test request retrieval with tunnel name filter."""
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_requests_json
        mock_response.raise_for_status = mocker.Mock()

        mock_client = mocker.Mock()
        mock_client.get.return_value = mock_response

        with NgrokRepository("http://localhost:4040") as repo:
            repo._client = mock_client
            repo.get_requests(tunnel_name="my-api")

        mock_client.get.assert_called_once_with(
            "http://localhost:4040/api/requests/http",
            params={"tunnel_name": "my-api"},
        )

    def test_get_requests_connection_error(self, mocker: MockerFixture) -> None:
        """Test connection error handling."""
        mock_client = mocker.Mock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        with NgrokRepository("http://localhost:4040") as repo:
            repo._client = mock_client

            with pytest.raises(NgrokConnectionError) as exc_info:
                repo.get_requests()

        assert "Cannot connect to ngrok inspector" in str(exc_info.value)
        assert "http://localhost:4040" in str(exc_info.value)

    def test_get_request_success(
        self,
        mocker: MockerFixture,
        sample_requests_json: dict,
    ) -> None:
        """Test getting a specific request."""
        single_request = sample_requests_json["requests"][0]
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = single_request
        mock_response.raise_for_status = mocker.Mock()

        mock_client = mocker.Mock()
        mock_client.get.return_value = mock_response

        with NgrokRepository("http://localhost:4040") as repo:
            repo._client = mock_client
            request = repo.get_request("548fb5c700000001")

        assert isinstance(request, CapturedRequest)
        assert request.id == "548fb5c700000001"

    def test_get_request_not_found(self, mocker: MockerFixture) -> None:
        """Test handling of 404 response."""
        mock_response = mocker.Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found",
            request=mocker.Mock(),
            response=mock_response,
        )

        mock_client = mocker.Mock()
        mock_client.get.return_value = mock_response

        with NgrokRepository("http://localhost:4040") as repo:
            repo._client = mock_client

            with pytest.raises(ValueError) as exc_info:
                repo.get_request("nonexistent")

        assert "Request not found" in str(exc_info.value)

    def test_health_check_success(self, mocker: MockerFixture) -> None:
        """Test successful health check."""
        mock_response = mocker.Mock()
        mock_response.status_code = 200

        mock_client = mocker.Mock()
        mock_client.get.return_value = mock_response

        with NgrokRepository("http://localhost:4040") as repo:
            repo._client = mock_client
            assert repo.health_check() is True

    def test_health_check_failure(self, mocker: MockerFixture) -> None:
        """Test failed health check."""
        mock_client = mocker.Mock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        with NgrokRepository("http://localhost:4040") as repo:
            repo._client = mock_client
            assert repo.health_check() is False
