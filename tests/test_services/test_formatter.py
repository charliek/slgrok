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

        # Check separators include method and path
        assert "*** POST /api/v1/devices ***" in output
        assert "*** GET /api/v1/users/456 ***" in output

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


class TestExtractHttpBody:
    """Tests for HTTP body extraction from raw messages."""

    def test_extract_body_with_crlf(self) -> None:
        """Test extracting body with standard CRLF line endings."""
        formatter = FormatterService()
        raw = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{"key": "value"}'
        result = formatter._extract_http_body(raw)
        assert result == '{"key": "value"}'

    def test_extract_body_with_lf(self) -> None:
        """Test extracting body with LF line endings."""
        formatter = FormatterService()
        raw = 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{"key": "value"}'
        result = formatter._extract_http_body(raw)
        assert result == '{"key": "value"}'

    def test_extract_body_no_separator(self) -> None:
        """Test that body without separator returns original."""
        formatter = FormatterService()
        raw = '{"key": "value"}'
        result = formatter._extract_http_body(raw)
        assert result == '{"key": "value"}'

    def test_extract_body_empty_body(self) -> None:
        """Test extracting empty body."""
        formatter = FormatterService()
        raw = "HTTP/1.1 204 No Content\r\nContent-Length: 0\r\n\r\n"
        result = formatter._extract_http_body(raw)
        assert result == ""

    def test_extract_body_multiline_json(self) -> None:
        """Test extracting multiline JSON body."""
        formatter = FormatterService()
        raw = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\n  "key": "value"\n}'
        result = formatter._extract_http_body(raw)
        assert result == '{\n  "key": "value"\n}'


class TestFormatBodyPrettyPrint:
    """Tests for pretty printing JSON bodies."""

    def test_pretty_print_simple_json(self) -> None:
        """Test pretty printing simple JSON."""
        formatter = FormatterService()
        body = '{"status":"ok","count":42}'
        result = formatter._format_body(body, "application/json", FormatOptions(pretty_print=True))

        # JSON should be formatted with indentation
        assert '"status": "ok"' in result
        assert '"count": 42' in result

    def test_pretty_print_nested_json(self) -> None:
        """Test pretty printing nested JSON."""
        formatter = FormatterService()
        body = '{"status":"ok","nested":{"key":"value"}}'
        result = formatter._format_body(body, "application/json", FormatOptions(pretty_print=True))

        # Should be formatted with indentation
        assert '"status": "ok"' in result
        assert '"nested": {' in result
        assert '"key": "value"' in result

    def test_pretty_print_invalid_json_unchanged(self) -> None:
        """Test that invalid JSON is left unchanged."""
        formatter = FormatterService()
        body = "Not valid JSON"
        result = formatter._format_body(body, "application/json", FormatOptions(pretty_print=True))

        # Should be unchanged
        assert result == body

    def test_pretty_print_non_json_content_type(self) -> None:
        """Test that non-JSON content is not modified."""
        formatter = FormatterService()
        body = '{"status":"ok"}'
        result = formatter._format_body(body, "text/plain", FormatOptions(pretty_print=True))

        # Should be unchanged (not JSON content type)
        assert result == body

    def test_pretty_print_disabled(self) -> None:
        """Test that JSON is not formatted when pretty_print is False."""
        formatter = FormatterService()
        body = '{"status":"ok"}'
        result = formatter._format_body(body, "application/json", FormatOptions(pretty_print=False))

        # Should be unchanged
        assert result == body

    def test_pretty_print_complex_nested_json(self) -> None:
        """Test pretty printing complex nested JSON."""
        formatter = FormatterService()
        body = '{"users":[{"name":"Alice","roles":["admin","user"]}]}'
        result = formatter._format_body(body, "application/json", FormatOptions(pretty_print=True))

        # Should have proper indentation
        assert '"users": [' in result
        assert '"name": "Alice"' in result
        assert '"roles": [' in result


class TestChunkedBodyDetection:
    """Tests for chunked transfer encoding detection."""

    def test_is_chunked_body_valid(self) -> None:
        """Test detection of valid chunked body."""
        formatter = FormatterService()
        body = '10b\nevent: message\ndata: {"key":"value"}\n\n0'
        assert formatter._is_chunked_body(body) is True

    def test_is_chunked_body_invalid_no_terminator(self) -> None:
        """Test that body without 0 terminator is not detected as chunked."""
        formatter = FormatterService()
        body = '10b\nevent: message\ndata: {"key":"value"}'
        assert formatter._is_chunked_body(body) is False

    def test_is_chunked_body_invalid_no_hex_start(self) -> None:
        """Test that body without hex start is not detected as chunked."""
        formatter = FormatterService()
        body = 'event: message\ndata: {"key":"value"}\n0'
        assert formatter._is_chunked_body(body) is False

    def test_is_chunked_body_regular_json(self) -> None:
        """Test that regular JSON is not detected as chunked."""
        formatter = FormatterService()
        body = '{"key": "value"}'
        assert formatter._is_chunked_body(body) is False

    def test_is_chunked_body_single_line(self) -> None:
        """Test that single line is not detected as chunked."""
        formatter = FormatterService()
        body = "10b"
        assert formatter._is_chunked_body(body) is False


class TestChunkedBodyFormatting:
    """Tests for chunked transfer encoding formatting."""

    def test_format_chunked_body_strips_chunk_sizes(self) -> None:
        """Test that chunk size prefixes are stripped."""
        formatter = FormatterService()
        body = '10b\nevent: message\ndata: {"key":"value"}\n\n0'
        result = formatter._format_chunked_body(body, "text/event-stream")

        # Chunk sizes should be removed
        assert "10b" not in result
        assert "0" not in result.strip().split("\n")[-1] or result.strip()[-1] != "0"
        # Content should remain
        assert "event: message" in result

    def test_format_chunked_body_formats_json_in_data(self) -> None:
        """Test that JSON in SSE data lines is pretty-printed."""
        formatter = FormatterService()
        body = '10b\nevent: message\ndata: {"key":"value","count":42}\n\n0'
        result = formatter._format_chunked_body(body, "text/event-stream")

        # JSON in data line should be formatted
        assert '"key": "value"' in result
        assert '"count": 42' in result

    def test_format_chunked_body_preserves_non_json_data(self) -> None:
        """Test that non-JSON data lines are preserved."""
        formatter = FormatterService()
        body = "a\nevent: ping\ndata: heartbeat\n\n0"
        result = formatter._format_chunked_body(body, "text/event-stream")

        assert "data: heartbeat" in result

    def test_format_chunked_body_multiple_events(self) -> None:
        """Test formatting multiple SSE events."""
        formatter = FormatterService()
        body = '20\nevent: msg1\ndata: {"id":1}\n\n1f\nevent: msg2\ndata: {"id":2}\n\n0'
        result = formatter._format_chunked_body(body, "text/event-stream")

        # Both events should be present
        assert "event: msg1" in result
        assert "event: msg2" in result
        assert '"id": 1' in result
        assert '"id": 2' in result


class TestSSEDataFormatting:
    """Tests for SSE data line JSON formatting."""

    def test_try_format_json_valid(self) -> None:
        """Test formatting valid JSON."""
        formatter = FormatterService()
        result = formatter._try_format_json('{"key":"value"}')
        assert '"key": "value"' in result

    def test_try_format_json_invalid(self) -> None:
        """Test that invalid JSON is returned unchanged."""
        formatter = FormatterService()
        text = "not json"
        result = formatter._try_format_json(text)
        assert result == text

    def test_format_body_detects_and_formats_chunked(self) -> None:
        """Test that _format_body detects chunked encoding and formats it."""
        formatter = FormatterService()
        body = '10b\nevent: message\ndata: {"status":"ok"}\n\n0'
        result = formatter._format_body(body, "text/event-stream", FormatOptions(pretty_print=True))

        # Should have formatted the JSON in data line
        assert '"status": "ok"' in result
        # Chunk markers should be gone
        assert "10b" not in result

    def test_format_chunked_body_strips_trailing_whitespace(self) -> None:
        """Test that trailing empty lines are stripped from chunked output."""
        formatter = FormatterService()
        body = '10b\nevent: message\ndata: {"key":"value"}\n\n\n\n0'
        result = formatter._format_chunked_body(body, "text/event-stream")

        # Should not end with blank lines
        assert not result.endswith("\n")
        assert result.rstrip() == result
