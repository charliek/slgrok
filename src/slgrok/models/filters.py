"""Filter models for request queries."""

import re
from datetime import timedelta
from typing import Literal

from pydantic import BaseModel, field_validator


class TimeWindow(BaseModel):
    """Time window for filtering requests."""

    value: int
    unit: Literal["s", "m", "h"]

    @classmethod
    def parse(cls, value: str) -> "TimeWindow":
        """Parse shorthand like '5s', '2m', '1h'."""
        match = re.match(r"^(\d+)([smh])$", value.strip().lower())
        if not match:
            raise ValueError(
                f"Invalid time window format: {value}. Use format like '5s', '2m', '1h'"
            )
        return cls(value=int(match.group(1)), unit=match.group(2))  # type: ignore[arg-type]

    def to_timedelta(self) -> timedelta:
        """Convert to timedelta."""
        match self.unit:
            case "s":
                return timedelta(seconds=self.value)
            case "m":
                return timedelta(minutes=self.value)
            case "h":
                return timedelta(hours=self.value)
            case _:
                raise ValueError(f"Unknown unit: {self.unit}")


class StatusCodeFilter(BaseModel):
    """Filter for HTTP status codes."""

    exact: list[int] = []
    ranges: list[str] = []  # e.g., "4xx", "5xx"
    errors_only: bool = False

    @field_validator("ranges")
    @classmethod
    def validate_ranges(cls, v: list[str]) -> list[str]:
        """Validate status code ranges."""
        valid_ranges = {"1xx", "2xx", "3xx", "4xx", "5xx"}
        for r in v:
            if r.lower() not in valid_ranges:
                raise ValueError(f"Invalid status range: {r}. Use 1xx, 2xx, 3xx, 4xx, or 5xx")
        return [r.lower() for r in v]

    def matches(self, status_code: int) -> bool:
        """Check if a status code matches the filter."""
        # If errors_only is set, status must be >= 400
        if self.errors_only and status_code < 400:
            return False

        # If no specific filters, match all (or just errors if errors_only)
        if not self.exact and not self.ranges:
            return True

        # Check exact matches
        if status_code in self.exact:
            return True

        # Check range matches
        range_prefix = f"{status_code // 100}xx"
        return range_prefix in self.ranges

    @classmethod
    def from_string(cls, value: str, errors_only: bool = False) -> "StatusCodeFilter":
        """Parse a status filter string like '404', '4xx', or '5xx'."""
        value = value.strip().lower()

        # Check if it's a range (e.g., "4xx")
        if re.match(r"^[1-5]xx$", value):
            return cls(ranges=[value], errors_only=errors_only)

        # Try to parse as exact status code
        try:
            code = int(value)
            if 100 <= code <= 599:
                return cls(exact=[code], errors_only=errors_only)
            raise ValueError(f"Status code must be between 100 and 599: {value}")
        except ValueError:
            raise ValueError(
                f"Invalid status filter: {value}. Use a number (404) or range (4xx)"
            ) from None


class RequestFilters(BaseModel):
    """Combined filters for request queries."""

    limit: int | None = None
    status: StatusCodeFilter | None = None
    path_pattern: str | None = None
    domain: str | None = None
    tunnel_name: str | None = None
    time_window: TimeWindow | None = None
