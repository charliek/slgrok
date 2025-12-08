"""Inspector service for fetching and filtering requests."""

import fnmatch
import re
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from urllib.parse import urlparse

from slgrok.models.filters import RequestFilters
from slgrok.models.output import debug_log
from slgrok.models.requests import CapturedRequest
from slgrok.repositories.ngrok import NgrokRepository


class InspectorService:
    """Service for inspecting captured requests."""

    def __init__(self, repository: NgrokRepository):
        self.repository = repository

    def get_requests(self, filters: RequestFilters) -> list[CapturedRequest]:
        """Fetch and filter captured requests.

        Args:
            filters: Filters to apply to requests

        Returns:
            Filtered list of captured requests
        """
        # Fetch from repository with API-supported filters
        requests = self.repository.get_requests(
            limit=None,  # Get all, filter locally for accurate results
            tunnel_name=filters.tunnel_name,
        )

        # Apply local filters
        filtered = self._apply_filters(requests, filters)

        # Apply limit after filtering
        if filters.limit is not None:
            filtered = filtered[: filters.limit]

        return filtered

    def tail_requests(
        self,
        filters: RequestFilters,
        poll_interval: float = 1.0,
        debug: bool = False,
    ) -> Iterator[CapturedRequest]:
        """Watch for new requests in real-time.

        Args:
            filters: Filters to apply to requests
            poll_interval: Seconds between polls
            debug: Whether to enable debug logging

        Yields:
            New captured requests as they arrive
        """
        seen_ids: set[str] = set()

        # Get initial requests to populate seen set
        initial = self.repository.get_requests(tunnel_name=filters.tunnel_name)
        for req in initial:
            seen_ids.add(req.id)

        if debug:
            debug_log(f"tail: initialized with {len(seen_ids)} existing requests")

        while True:
            requests = self.repository.get_requests(tunnel_name=filters.tunnel_name)

            # Find new requests
            new_requests = [r for r in requests if r.id not in seen_ids]

            if debug and new_requests:
                debug_log(f"tail: found {len(new_requests)} new request(s) in poll")

            # Filter and yield new requests
            filtered = self._apply_filters(new_requests, filters, debug)
            for req in filtered:
                seen_ids.add(req.id)
                if debug:
                    has_response = req.response is not None
                    has_body = False
                    body_len = 0
                    if req.response is not None and req.response.raw is not None:
                        has_body = True
                        body_len = len(req.response.raw)
                    debug_log(
                        f"tail: yielding {req.id} - has_response={has_response}, "
                        f"has_raw_body={has_body}, raw_len={body_len}"
                    )
                yield req

            time.sleep(poll_interval)

    def _apply_filters(
        self,
        requests: list[CapturedRequest],
        filters: RequestFilters,
        debug: bool = False,
    ) -> list[CapturedRequest]:
        """Apply filters to a list of requests.

        Args:
            requests: List of requests to filter
            filters: Filters to apply
            debug: Whether to enable debug logging

        Returns:
            Filtered list of requests
        """
        result = requests
        initial_count = len(result)

        # Filter by status code
        if filters.status is not None:
            result = [
                r
                for r in result
                if r.response is not None and filters.status.matches(r.response.status_code)
            ]
            if debug and len(result) != initial_count:
                debug_log(f"filter: status filter reduced {initial_count} -> {len(result)}")

        # Filter by path pattern
        if filters.path_pattern is not None:
            before = len(result)
            result = [r for r in result if self._matches_path(r.request.uri, filters.path_pattern)]
            if debug and len(result) != before:
                debug_log(f"filter: path filter reduced {before} -> {len(result)}")

        # Filter by domain
        if filters.domain is not None:
            before = len(result)
            result = [r for r in result if self._matches_domain(r, filters.domain)]
            if debug and len(result) != before:
                debug_log(f"filter: domain filter reduced {before} -> {len(result)}")

        # Filter by time window
        if filters.time_window is not None:
            before = len(result)
            cutoff = datetime.now(UTC) - filters.time_window.to_timedelta()
            result = [r for r in result if r.start >= cutoff]
            if debug and len(result) != before:
                debug_log(f"filter: time_window filter reduced {before} -> {len(result)}")

        return result

    def _matches_path(self, uri: str, pattern: str) -> bool:
        """Check if a URI matches a path pattern.

        Supports both glob patterns (with *) and regex.

        Args:
            uri: The request URI
            pattern: The pattern to match against

        Returns:
            True if the URI matches the pattern
        """
        # Extract path from URI
        parsed = urlparse(uri)
        path = parsed.path

        # Try glob first if pattern contains glob chars
        if "*" in pattern or "?" in pattern:
            return fnmatch.fnmatch(path, pattern)

        # Otherwise try regex
        try:
            return bool(re.search(pattern, path))
        except re.error:
            # If invalid regex, do literal match
            return pattern in path

    def _matches_domain(self, request: CapturedRequest, domain: str) -> bool:
        """Check if a request matches a domain filter.

        Args:
            request: The captured request
            domain: The domain to filter by

        Returns:
            True if the request is for the specified domain
        """
        # Check the Host header
        host_header = request.request.headers.root.get("Host", [])
        if host_header:
            host = host_header[0].lower()
            return domain.lower() in host

        return False
