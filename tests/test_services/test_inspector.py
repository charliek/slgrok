"""Tests for inspector service."""

from datetime import timedelta

import pytest
from pytest_mock import MockerFixture

from slgrok.models.filters import RequestFilters, StatusCodeFilter, TimeWindow
from slgrok.models.requests import CapturedRequest
from slgrok.services.inspector import InspectorService


class TestInspectorService:
    """Tests for InspectorService."""

    def test_get_requests_no_filters(
        self,
        mocker: MockerFixture,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test getting requests without filters."""
        mock_repo = mocker.Mock()
        mock_repo.get_requests.return_value = sample_requests

        service = InspectorService(mock_repo)
        result = service.get_requests(RequestFilters())

        assert len(result) == 3
        mock_repo.get_requests.assert_called_once_with(limit=None, tunnel_name=None)

    def test_get_requests_with_limit(
        self,
        mocker: MockerFixture,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test getting requests with limit."""
        mock_repo = mocker.Mock()
        mock_repo.get_requests.return_value = sample_requests

        service = InspectorService(mock_repo)
        result = service.get_requests(RequestFilters(limit=2))

        assert len(result) == 2

    def test_get_requests_filter_by_status_exact(
        self,
        mocker: MockerFixture,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test filtering by exact status code."""
        mock_repo = mocker.Mock()
        mock_repo.get_requests.return_value = sample_requests

        service = InspectorService(mock_repo)
        filters = RequestFilters(status=StatusCodeFilter(exact=[404]))
        result = service.get_requests(filters)

        assert len(result) == 1
        assert result[0].response is not None
        assert result[0].response.status_code == 404

    def test_get_requests_filter_by_status_range(
        self,
        mocker: MockerFixture,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test filtering by status code range."""
        mock_repo = mocker.Mock()
        mock_repo.get_requests.return_value = sample_requests

        service = InspectorService(mock_repo)
        filters = RequestFilters(status=StatusCodeFilter(ranges=["4xx"]))
        result = service.get_requests(filters)

        assert len(result) == 1
        assert result[0].response is not None
        assert result[0].response.status_code == 404

    def test_get_requests_filter_errors_only(
        self,
        mocker: MockerFixture,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test filtering for errors only."""
        mock_repo = mocker.Mock()
        mock_repo.get_requests.return_value = sample_requests

        service = InspectorService(mock_repo)
        filters = RequestFilters(status=StatusCodeFilter(errors_only=True))
        result = service.get_requests(filters)

        assert len(result) == 2
        for req in result:
            assert req.response is not None
            assert req.response.status_code >= 400

    def test_get_requests_filter_by_path_glob(
        self,
        mocker: MockerFixture,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test filtering by path pattern (glob)."""
        mock_repo = mocker.Mock()
        mock_repo.get_requests.return_value = sample_requests

        service = InspectorService(mock_repo)
        filters = RequestFilters(path_pattern="/api/v1/*")
        result = service.get_requests(filters)

        assert len(result) == 2
        for req in result:
            assert req.request.uri.startswith("/api/v1/")

    def test_get_requests_filter_by_path_regex(
        self,
        mocker: MockerFixture,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test filtering by path pattern (regex)."""
        mock_repo = mocker.Mock()
        mock_repo.get_requests.return_value = sample_requests

        service = InspectorService(mock_repo)
        filters = RequestFilters(path_pattern=r"devices|users")
        result = service.get_requests(filters)

        assert len(result) == 2

    def test_get_requests_filter_by_tunnel(
        self,
        mocker: MockerFixture,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test filtering by tunnel name is passed to repository."""
        # Tunnel filtering is handled by the ngrok API, not locally
        # So we mock the repository returning filtered results
        filtered_requests = [r for r in sample_requests if r.tunnel_name == "my-api"]
        mock_repo = mocker.Mock()
        mock_repo.get_requests.return_value = filtered_requests

        service = InspectorService(mock_repo)
        filters = RequestFilters(tunnel_name="my-api")
        result = service.get_requests(filters)

        # Verify tunnel_name was passed to repository
        mock_repo.get_requests.assert_called_once_with(limit=None, tunnel_name="my-api")
        assert len(result) == 1
        assert result[0].tunnel_name == "my-api"

    def test_get_requests_filter_by_domain(
        self,
        mocker: MockerFixture,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test filtering by domain."""
        mock_repo = mocker.Mock()
        mock_repo.get_requests.return_value = sample_requests

        service = InspectorService(mock_repo)
        filters = RequestFilters(domain="api.ngrok.io")
        result = service.get_requests(filters)

        assert len(result) == 1

    def test_get_requests_combined_filters(
        self,
        mocker: MockerFixture,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test combining multiple filters."""
        mock_repo = mocker.Mock()
        mock_repo.get_requests.return_value = sample_requests

        service = InspectorService(mock_repo)
        filters = RequestFilters(
            status=StatusCodeFilter(errors_only=True),
            path_pattern="/api/*",
        )
        result = service.get_requests(filters)

        # Only the 404 on /api/v1/users/456 should match
        assert len(result) == 1
        assert result[0].response is not None
        assert result[0].response.status_code == 404


class TestStatusCodeFilter:
    """Tests for StatusCodeFilter."""

    def test_matches_exact(self) -> None:
        """Test exact status code matching."""
        filter = StatusCodeFilter(exact=[404, 500])
        assert filter.matches(404) is True
        assert filter.matches(500) is True
        assert filter.matches(200) is False

    def test_matches_range(self) -> None:
        """Test range matching."""
        filter = StatusCodeFilter(ranges=["4xx"])
        assert filter.matches(400) is True
        assert filter.matches(404) is True
        assert filter.matches(499) is True
        assert filter.matches(500) is False
        assert filter.matches(200) is False

    def test_matches_errors_only(self) -> None:
        """Test errors_only flag."""
        filter = StatusCodeFilter(errors_only=True)
        assert filter.matches(400) is True
        assert filter.matches(500) is True
        assert filter.matches(200) is False
        assert filter.matches(399) is False

    def test_from_string_exact(self) -> None:
        """Test parsing exact status code."""
        filter = StatusCodeFilter.from_string("404")
        assert filter.exact == [404]
        assert filter.matches(404) is True
        assert filter.matches(500) is False

    def test_from_string_range(self) -> None:
        """Test parsing range."""
        filter = StatusCodeFilter.from_string("5xx")
        assert filter.ranges == ["5xx"]
        assert filter.matches(500) is True
        assert filter.matches(503) is True
        assert filter.matches(404) is False

    def test_from_string_invalid(self) -> None:
        """Test invalid status string."""
        with pytest.raises(ValueError):
            StatusCodeFilter.from_string("invalid")


class TestTimeWindow:
    """Tests for TimeWindow."""

    def test_parse_seconds(self) -> None:
        """Test parsing seconds."""
        tw = TimeWindow.parse("30s")
        assert tw.value == 30
        assert tw.unit == "s"

    def test_parse_minutes(self) -> None:
        """Test parsing minutes."""
        tw = TimeWindow.parse("5m")
        assert tw.value == 5
        assert tw.unit == "m"

    def test_parse_hours(self) -> None:
        """Test parsing hours."""
        tw = TimeWindow.parse("2h")
        assert tw.value == 2
        assert tw.unit == "h"

    def test_to_timedelta_seconds(self) -> None:
        """Test converting seconds to timedelta."""
        tw = TimeWindow(value=30, unit="s")
        assert tw.to_timedelta() == timedelta(seconds=30)

    def test_to_timedelta_minutes(self) -> None:
        """Test converting minutes to timedelta."""
        tw = TimeWindow(value=5, unit="m")
        assert tw.to_timedelta() == timedelta(minutes=5)

    def test_to_timedelta_hours(self) -> None:
        """Test converting hours to timedelta."""
        tw = TimeWindow(value=2, unit="h")
        assert tw.to_timedelta() == timedelta(hours=2)

    def test_parse_invalid(self) -> None:
        """Test parsing invalid format."""
        with pytest.raises(ValueError):
            TimeWindow.parse("invalid")

        with pytest.raises(ValueError):
            TimeWindow.parse("5d")  # Invalid unit
