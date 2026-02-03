"""Tests for departments and readall endpoints."""
import pytest
import requests


class TestDepartments:
    """Tests for department/team operations."""

    def test_search_department_by_contact(self, api_config, headers):
        """Test searching department info for a contact."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "departments",
            "option": "search",
            "phone": api_config["test_phone"]
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200 for success, 404 if contact or manager not found
        assert response.status_code in [200, 404], f"Failed with: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            # Check expected fields
            assert "team" in data or "primary_manager_extension" in data


class TestReadAll:
    """Tests for aggregated contact information."""

    def test_readall_contact_info(self, api_config, headers):
        """Test getting aggregated contact information."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "readall",
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
        
        # Check expected structure
        assert "contact" in data
        assert "manager" in data
        assert "open_activities_count" in data
        assert "activities_details" in data

    def test_readall_with_nif(self, api_config, headers):
        """Test readall search by NIF."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "readall",
            "option": "search",
            "nif": "12345678A"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200 for success, contact might not exist
        assert response.status_code == 200, f"Failed with: {response.text}"
