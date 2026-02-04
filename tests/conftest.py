"""Pytest configuration and fixtures for ZOA API tests."""
import pytest
import os


@pytest.fixture(scope="session")
def api_config():
    """Configuration for API tests."""
    return {
        "base_url": os.environ.get("ZOA_TEST_URL", "http://localhost:8080"),
        "company_id": os.environ.get("ZOA_TEST_COMPANY_ID", "572778529248319"),
        "test_phone": os.environ.get("ZOA_TEST_PHONE", "+34622272095"),
        "test_email": os.environ.get("ZOA_TEST_EMAIL", "test@example.com"),
    }


@pytest.fixture
def headers(api_config):
    """Standard headers for API requests."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
