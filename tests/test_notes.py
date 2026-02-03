"""Tests for notes endpoints."""
import pytest
import requests
from datetime import datetime


class TestNotes:
    """Tests for note management operations."""

    def test_search_notes(self, api_config, headers):
        """Test searching notes for a contact."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "notes",
            "option": "search",
            "phone": api_config["test_phone"]
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200 for success, 404 if contact not found
        assert response.status_code in [200, 404], f"Failed with: {response.text}"

    def test_create_note(self, api_config, headers):
        """Test creating a note for a contact."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "notes",
            "option": "create",
            "phone": api_config["test_phone"],
            "content": f"Test note created at {datetime.now()}",
            "date": datetime.now().strftime("%Y-%m-%d")
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200/201 for success, 404 if contact not found
        assert response.status_code in [200, 201, 404], f"Failed with: {response.text}"

    def test_create_pinned_note(self, api_config, headers):
        """Test creating a pinned note."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "notes",
            "option": "create",
            "phone": api_config["test_phone"],
            "content": "Important pinned note",
            "is_pinned": True
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code in [200, 201, 404], f"Failed with: {response.text}"

    def test_update_note(self, api_config, headers):
        """Test updating a note."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "notes",
            "option": "update",
            "phone": api_config["test_phone"],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "new_content": "Updated note content"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200 for success, 404 if note not found
        assert response.status_code in [200, 404], f"Failed with: {response.text}"
