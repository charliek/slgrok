"""Tests for formatter service."""

import base64

from slgrok.models.output import FormatOptions
from slgrok.models.requests import CapturedRequest
from slgrok.services.formatter import FormatterService


class TestFormatterService:
    """Tests for FormatterService."""

    def test_format_request_basic(self, sample_request: CapturedRequest) -> None:
        """Test basic request formatting."""
        formatter = FormatterService()
        output = formatter.format_request(sample_request, FormatOptions())

        # Check header
        assert "## POST /api/v1/devices" in output
        assert "**Status:** 200 OK" in output
        assert "**Duration:**" in output
        assert "**Timestamp:**" in output
        assert "**Tunnel:** command_line" in output
        assert "**Remote:** 192.168.100.25" in output

        # Check sections
        assert "### Request Headers" in output
        assert "### Request Body" in output
        assert "### Response Headers" in output
        assert "### Response Body" in output

    def test_format_request_masks_auth_header(
        self,
        sample_request: CapturedRequest,
    ) -> None:
        """Test that authorization header is masked."""
        formatter = FormatterService()
        output = formatter.format_request(sample_request, FormatOptions())

        assert "Authorization: ***" in output
        assert "Bearer token123" not in output

    def test_format_request_decodes_body(
        self,
        sample_request: CapturedRequest,
    ) -> None:
        """Test that body is base64 decoded."""
        formatter = FormatterService()
        output = formatter.format_request(sample_request, FormatOptions())

        # The raw body is base64 encoded {"deviceId": "123"}
        assert "deviceId" in output

    def test_format_request_pretty_print(
        self,
        sample_request: CapturedRequest,
    ) -> None:
        """Test pretty printing JSON bodies."""
        formatter = FormatterService()
        output = formatter.format_request(
            sample_request,
            FormatOptions(pretty_print=True),
        )

        # Pretty printed JSON should have indentation
        assert '  "deviceId"' in output or '"deviceId":' in output

    def test_format_request_truncate(
        self,
        sample_request: CapturedRequest,
    ) -> None:
        """Test body truncation."""
        formatter = FormatterService()
        output = formatter.format_request(
            sample_request,
            FormatOptions(truncate=5),
        )

        assert "truncated" in output

    def test_format_requests_multiple(
        self,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test formatting multiple requests."""
        formatter = FormatterService()
        output = formatter.format_requests(
            sample_requests,
            FormatOptions(),
        )

        # Check header
        assert "# ngrok Inspector - 3 requests" in output
        assert "**Retrieved:**" in output

        # Check all requests are included
        assert "## POST /api/v1/devices" in output
        assert "## GET /api/v1/users/456" in output
        assert "## POST /webhook/events" in output

        # Check separators
        assert "---" in output

    def test_format_requests_with_filters_summary(
        self,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test formatting with filters summary."""
        formatter = FormatterService()
        output = formatter.format_requests(
            sample_requests,
            FormatOptions(),
            filters_summary="errors only, path=/api/*",
        )

        assert "**Filters:** errors only, path=/api/*" in output

    def test_format_duration_microseconds(self) -> None:
        """Test duration formatting for microseconds."""
        formatter = FormatterService()
        assert "µs" in formatter._format_duration(500)

    def test_format_duration_milliseconds(self) -> None:
        """Test duration formatting for milliseconds."""
        formatter = FormatterService()
        result = formatter._format_duration(234000000)  # 234ms
        assert "234ms" in result

    def test_format_duration_seconds(self) -> None:
        """Test duration formatting for seconds."""
        formatter = FormatterService()
        result = formatter._format_duration(1500000000)  # 1.5s
        assert "1.50s" in result

    def test_decode_body_valid(self) -> None:
        """Test decoding valid base64."""
        formatter = FormatterService()
        raw = base64.b64encode(b'{"test": "value"}').decode()
        result = formatter._decode_body(raw)
        assert result == '{"test": "value"}'

    def test_decode_body_empty(self) -> None:
        """Test decoding empty body."""
        formatter = FormatterService()
        assert formatter._decode_body("") == ""

    def test_get_code_block_lang(self) -> None:
        """Test code block language detection."""
        formatter = FormatterService()
        assert formatter._get_code_block_lang("application/json") == "json"
        assert formatter._get_code_block_lang("text/xml") == "xml"
        assert formatter._get_code_block_lang("text/html") == "html"
        assert formatter._get_code_block_lang("text/plain") == ""
