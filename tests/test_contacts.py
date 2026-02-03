"""Tests for contacts endpoints."""
import pytest
import requests


class TestContacts:
    """Tests for contact management operations."""

    def test_search_contact_by_phone(self, api_config, headers):
        """Test searching for a contact by phone number."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "contacts",
            "option": "search",
            "phone": api_config["test_phone"]
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code == 200, f"Failed with: {response.text}"
        data = response.json()
        assert "data" in data

    def test_search_contact_by_email(self, api_config, headers):
        """Test searching for a contact by email."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "contacts",
            "option": "search",
            "email": api_config["test_email"]
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code == 200, f"Failed with: {response.text}"
        data = response.json()
        assert "data" in data

    def test_create_contact(self, api_config, headers):
        """Test creating a new contact."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "contacts",
            "option": "create",
            "name": "Test User Automated",
            "email": "test_automated@example.com",
            "mobile": "+34600000000",
            "contact_type": "particular"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 201 for created, 200 for success, 409 for duplicate
        assert response.status_code in [200, 201, 409], f"Failed with: {response.text}"

    def test_update_contact(self, api_config, headers):
        """Test updating an existing contact."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "contacts",
            "option": "update",
            "phone": api_config["test_phone"],
            "new_name": "Updated Test User"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200 for success, 404 if contact doesn't exist
        assert response.status_code in [200, 404], f"Failed with: {response.text}"
