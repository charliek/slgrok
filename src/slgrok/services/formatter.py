"""Formatter service for markdown output."""

import base64
import json
import re
from datetime import UTC, datetime

from slgrok.models.output import FormatOptions
from slgrok.models.requests import CapturedRequest, HttpHeaders


class FormatterService:
    """Service for formatting captured requests as markdown."""

    def format_request(self, request: CapturedRequest, options: FormatOptions) -> str:
        """Format a single captured request as markdown.

        Args:
            request: The captured request to format
            options: Formatting options

        Returns:
            Markdown formatted string
        """
        lines: list[str] = []

        # Header with method, path, and status
        method = request.request.method
        path = request.request.uri
        status = request.response.status if request.response else "No Response"

        lines.append(f"## {method} {path}")
        lines.append(f"**ID:** `{request.id}`")
        lines.append(f"**Status:** {status}")
        lines.append(f"**Duration:** {self._format_duration(request.duration)}")
        lines.append(f"**Timestamp:** {self._format_timestamp(request.start)}")
        lines.append(f"**Tunnel:** {request.tunnel_name}")
        lines.append(f"**Remote:** {request.remote_addr}")
        lines.append("")

        # Request headers
        if options.show_headers:
            lines.append("### Request Headers")
            lines.extend(self._format_headers(request.request.headers, options.headers_filter))
            lines.append("")

        # Request body (extract just the body from raw HTTP message)
        request_raw = self._decode_body(request.request.raw)
        request_body = self._extract_http_body(request_raw) if request_raw else ""
        if request_body:
            lines.append("### Request Body")
            content_type = self._get_content_type(request.request.headers)
            body_formatted = self._format_body(request_body, content_type, options)
            lang = self._get_code_block_lang(content_type)
            lines.append(f"```{lang}")
            lines.append(body_formatted)
            lines.append("```")
            lines.append("")

        # Response headers
        if request.response and options.show_headers:
            lines.append("### Response Headers")
            lines.extend(self._format_headers(request.response.headers, options.headers_filter))
            lines.append("")

        # Response body (extract just the body from raw HTTP message)
        if request.response:
            response_raw = self._decode_body(request.response.raw)
            response_body = self._extract_http_body(response_raw) if response_raw else ""
            if response_body:
                lines.append("### Response Body")
                content_type = self._get_content_type(request.response.headers)
                body_formatted = self._format_body(response_body, content_type, options)
                lang = self._get_code_block_lang(content_type)
                lines.append(f"```{lang}")
                lines.append(body_formatted)
                lines.append("```")
                lines.append("")

        return "\n".join(lines)

    def format_requests(
        self,
        requests: list[CapturedRequest],
        options: FormatOptions,
        filters_summary: str | None = None,
    ) -> str:
        """Format multiple captured requests as markdown.

        Args:
            requests: The captured requests to format
            options: Formatting options
            filters_summary: Optional summary of applied filters

        Returns:
            Markdown formatted string
        """
        lines: list[str] = []

        # Summary header
        count = len(requests)
        plural = "s" if count != 1 else ""
        lines.append(f"# ngrok Inspector - {count} request{plural}")
        lines.append("")

        if filters_summary:
            lines.append(f"**Filters:** {filters_summary}")

        lines.append(f"**Retrieved:** {self._format_timestamp(datetime.now(UTC))}")
        lines.append("")

        # Format each request
        for request in requests:
            separator = self._build_separator(f"{request.request.method} {request.request.uri}")
            lines.append(separator)
            lines.append("")
            lines.append(self.format_request(request, options))

        return "\n".join(lines)

    def _build_separator(self, label: str, width: int = 80) -> str:
        """Build a visual separator line with a centered label.

        Args:
            label: The label to center in the separator
            width: Total width of the separator line

        Returns:
            Separator string like "******** POST /api ********"
        """
        # Account for spaces around label
        label_with_spaces = f" {label} "
        remaining = width - len(label_with_spaces)
        if remaining < 2:
            return f"* {label} *"
        left = remaining // 2
        right = remaining - left
        return f"{'*' * left}{label_with_spaces}{'*' * right}"

    def _decode_body(self, raw: str | None) -> str:
        """Decode a base64-encoded body.

        Args:
            raw: Base64 encoded body, can be None

        Returns:
            Decoded body string (full HTTP message)
        """
        if not raw:
            return ""
        try:
            decoded = base64.b64decode(raw)
            return decoded.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def _extract_http_body(self, raw_message: str) -> str:
        """Extract just the body from a raw HTTP message.

        The raw message includes HTTP headers. The body starts after
        the blank line (\\r\\n\\r\\n or \\n\\n).

        Args:
            raw_message: Full HTTP message with headers

        Returns:
            Just the body portion, or empty string if not found
        """
        # Try \r\n\r\n first (standard HTTP)
        if "\r\n\r\n" in raw_message:
            return raw_message.split("\r\n\r\n", 1)[1]
        # Fall back to \n\n
        if "\n\n" in raw_message:
            return raw_message.split("\n\n", 1)[1]
        # No separator found, return as-is
        return raw_message

    def _format_body(self, body: str, content_type: str, options: FormatOptions) -> str:
        """Format a body string according to options.

        Args:
            body: The body string (already extracted, no HTTP headers)
            content_type: The content type
            options: Formatting options

        Returns:
            Formatted body string
        """
        result = body

        if options.pretty_print:
            # Check if this looks like chunked transfer encoding
            if self._is_chunked_body(body):
                result = self._format_chunked_body(body, content_type)
            elif "json" in content_type.lower():
                # Pretty print JSON if requested
                try:
                    parsed = json.loads(body)
                    result = json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    pass  # Keep original if not valid JSON

        # Truncate if requested
        if options.truncate is not None and len(result) > options.truncate:
            result = result[: options.truncate] + f"\n... (truncated, {len(body)} total chars)"

        return result

    def _is_chunked_body(self, body: str) -> bool:
        """Check if a body looks like chunked transfer encoding.

        Chunked bodies start with a hex size followed by content,
        and end with a '0' terminator.

        Args:
            body: The body to check

        Returns:
            True if body appears to be chunked encoding
        """
        lines = body.strip().split("\n")
        if len(lines) < 2:
            return False

        # First line should be hex chunk size
        first_line = lines[0].strip()
        if not re.match(r"^[0-9a-fA-F]+$", first_line):
            return False

        # Last non-empty line should be '0' terminator
        last_line = lines[-1].strip()
        return last_line == "0"

    def _format_chunked_body(self, body: str, _content_type: str) -> str:
        """Format a chunked transfer encoded body.

        Strips chunk size prefixes and terminating chunk, then formats
        SSE data lines if present.

        Args:
            body: The chunked body
            _content_type: The content type (unused, reserved for future use)

        Returns:
            Formatted body with JSON pretty-printed in data lines
        """
        lines = body.split("\n")
        result_lines: list[str] = []
        i = 0

        while i < len(lines):
            line = lines[i].rstrip("\r")

            # Skip hex chunk size lines
            if re.match(r"^[0-9a-fA-F]+$", line.strip()):
                # Skip terminating '0' chunk
                if line.strip() == "0":
                    i += 1
                    continue
                i += 1
                continue

            # Handle SSE data lines
            if line.startswith("data:"):
                data_content = line[5:].strip()
                formatted_data = self._try_format_json(data_content)
                if formatted_data != data_content:
                    # Multi-line formatted JSON - indent continuation lines
                    json_lines = formatted_data.split("\n")
                    result_lines.append(f"data: {json_lines[0]}")
                    for json_line in json_lines[1:]:
                        result_lines.append(f"      {json_line}")
                else:
                    result_lines.append(f"data: {formatted_data}")
            else:
                result_lines.append(line)

            i += 1

        # Strip trailing empty lines
        while result_lines and not result_lines[-1].strip():
            result_lines.pop()

        return "\n".join(result_lines)

    def _try_format_json(self, text: str) -> str:
        """Try to parse and format text as JSON.

        Args:
            text: Text that might be JSON

        Returns:
            Pretty-printed JSON if valid, otherwise original text
        """
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            return text

    def _format_headers(
        self,
        headers: HttpHeaders,
        filter_list: list[str] | None,
    ) -> list[str]:
        """Format headers for display.

        Args:
            headers: The headers to format
            filter_list: Optional list of header names to include

        Returns:
            List of formatted header lines
        """
        lines: list[str] = []
        for name, values in headers.root.items():
            # Apply filter if specified
            if filter_list is not None and not any(f.lower() == name.lower() for f in filter_list):
                continue

            # Mask sensitive headers
            display_values = values
            if name.lower() in ("authorization", "x-api-key", "cookie", "set-cookie"):
                display_values = ["***"]

            for value in display_values:
                lines.append(f"{name}: {value}")

        return lines

    def _format_duration(self, nanoseconds: int) -> str:
        """Format duration in human-readable form.

        Args:
            nanoseconds: Duration in nanoseconds

        Returns:
            Human-readable duration string
        """
        ms = nanoseconds / 1_000_000
        if ms < 1:
            return f"{nanoseconds / 1_000:.2f}µs"
        if ms < 1000:
            return f"{ms:.0f}ms"
        return f"{ms / 1000:.2f}s"

    def _format_timestamp(self, dt: datetime) -> str:
        """Format a timestamp for display.

        Args:
            dt: The datetime to format

        Returns:
            ISO format timestamp string
        """
        return dt.isoformat()

    def _get_content_type(self, headers: HttpHeaders) -> str:
        """Extract content type from headers.

        Args:
            headers: The headers dict

        Returns:
            Content type string or empty string
        """
        content_types = headers.root.get("Content-Type", [])
        return content_types[0] if content_types else ""

    def _get_code_block_lang(self, content_type: str) -> str:
        """Get the appropriate code block language for a content type.

        Args:
            content_type: The content type

        Returns:
            Code block language identifier
        """
        ct = content_type.lower()
        if "json" in ct:
            return "json"
        if "xml" in ct:
            return "xml"
        if "html" in ct:
            return "html"
        if "javascript" in ct:
            return "javascript"
        if "css" in ct:
            return "css"
        return ""
