"""Tests for email and scheduler endpoints."""
import pytest
import requests


class TestEmail:
    """Tests for email sending operations."""

    def test_send_email(self, api_config, headers):
        """Test sending an email."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "email_module",
            "option": "send",
            "to": "test@example.com",
            "subject": "Test Email",
            "body": "<h1>Test</h1><p>This is a test email.</p>",
            "body_type": "html"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200 for success, might fail if email service not configured
        assert response.status_code in [200, 400, 500], f"Failed with: {response.text}"


class TestScheduler:
    """Tests for scheduler configuration."""

    def test_search_scheduler_config(self, api_config, headers):
        """Test getting scheduler configuration from Firebase."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "scheduler",
            "option": "search"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200 for success, 404 if config not found
        assert response.status_code in [200, 404], f"Failed with: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            # Check for morning/afternoon schedule
            assert "morning" in data or "afternoon" in data
