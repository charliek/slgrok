"""Formatter service for markdown output."""

import base64
import json
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
        lines.append(f"**Status:** {status}")
        lines.append(f"**Duration:** {self._format_duration(request.duration)}")
        lines.append(f"**Timestamp:** {self._format_timestamp(request.start)}")
        lines.append(f"**Tunnel:** {request.tunnel_name}")
        lines.append(f"**Remote:** {request.remote_addr}")
        lines.append("")

        # Request headers
        if options.show_headers:
            lines.append("### Request Headers")
            lines.append("```")
            lines.extend(self._format_headers(request.request.headers, options.headers_filter))
            lines.append("```")
            lines.append("")

        # Request body
        request_body = self._decode_body(request.request.raw)
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
            lines.append("```")
            lines.extend(self._format_headers(request.response.headers, options.headers_filter))
            lines.append("```")
            lines.append("")

        # Response body
        if request.response:
            response_body = self._decode_body(request.response.raw)
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
        for i, request in enumerate(requests):
            lines.append("---")
            lines.append("")
            lines.append(self.format_request(request, options))
            if i < len(requests) - 1:
                lines.append("")

        return "\n".join(lines)

    def _decode_body(self, raw: str | None) -> str:
        """Decode a base64-encoded body.

        Args:
            raw: Base64 encoded body, can be None

        Returns:
            Decoded body string
        """
        if not raw:
            return ""
        try:
            decoded = base64.b64decode(raw)
            return decoded.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def _format_body(self, body: str, content_type: str, options: FormatOptions) -> str:
        """Format a body string according to options.

        Args:
            body: The body string
            content_type: The content type
            options: Formatting options

        Returns:
            Formatted body string
        """
        result = body

        # Pretty print JSON if requested
        if options.pretty_print and "json" in content_type.lower():
            try:
                parsed = json.loads(body)
                result = json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                pass  # Keep original if not valid JSON

        # Truncate if requested
        if options.truncate is not None and len(result) > options.truncate:
            result = result[: options.truncate] + f"\n... (truncated, {len(body)} total chars)"

        return result

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
            if filter_list is not None:
                if not any(f.lower() == name.lower() for f in filter_list):
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
