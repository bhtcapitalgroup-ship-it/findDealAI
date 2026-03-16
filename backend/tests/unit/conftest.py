"""Minimal conftest for unit tests — override the autouse DB fixture."""

import pytest


@pytest.fixture(autouse=True)
def setup_database():
    """Override the parent conftest's setup_database — unit tests don't need DB."""
    yield
