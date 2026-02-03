"""Tests for users and tags endpoints."""
import pytest
import requests
from datetime import datetime


class TestUsers:
    """Tests for user search operations."""

    def test_search_user_by_name(self, api_config, headers):
        """Test searching for a user by name."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "users",
            "option": "search",
            "name": "Soporte Zoa"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code == 200, f"Failed with: {response.text}"
        data = response.json()
        assert "data" in data

    def test_search_all_users(self, api_config, headers):
        """Test searching all users."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "users",
            "option": "search"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code == 200, f"Failed with: {response.text}"
        data = response.json()
        assert "data" in data


class TestTags:
    """Tests for tag management operations."""

    def test_search_tags(self, api_config, headers):
        """Test searching all tags."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "tags",
            "option": "search"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code == 200, f"Failed with: {response.text}"
        data = response.json()
        assert "data" in data

    def test_create_tag(self, api_config, headers):
        """Test creating a new tag."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "tags",
            "option": "create",
            "name": f"Test Tag {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "type": "sales",
            "color": "#FF5722"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200/201 for success, 409 for duplicate
        assert response.status_code in [200, 201, 409], f"Failed with: {response.text}"
