"""Shared test fixtures."""

import json
from pathlib import Path

import pytest

from slgrok.models.requests import CapturedRequest, CapturedRequestList


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_requests_json(fixtures_dir: Path) -> dict:
    """Load sample requests JSON fixture."""
    with open(fixtures_dir / "requests.json") as f:
        return json.load(f)


@pytest.fixture
def sample_requests(sample_requests_json: dict) -> list[CapturedRequest]:
    """Parse sample requests into models."""
    data = CapturedRequestList.model_validate(sample_requests_json)
    return data.requests


@pytest.fixture
def sample_request(sample_requests: list[CapturedRequest]) -> CapturedRequest:
    """Return the first sample request."""
    return sample_requests[0]
