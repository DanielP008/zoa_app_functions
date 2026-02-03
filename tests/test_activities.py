"""Tests for activities endpoints."""
import pytest
import requests
from datetime import datetime, timedelta


class TestActivities:
    """Tests for activity/calendar operations."""

    def test_search_activities_by_contact(self, api_config, headers):
        """Test searching activities for a contact."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "activities",
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

    def test_create_activity(self, api_config, headers):
        """Test creating a standalone activity."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        payload = {
            "company_id": api_config["company_id"],
            "action": "activities",
            "option": "create",
            "title": f"Test Call {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "phone": api_config["test_phone"],
            "type_of_activity": "llamada",
            "date": tomorrow,
            "start_time": "10:00",
            "duration": "30",
            "description": "Automated test activity"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200/201 for success, 404 if contact not found
        assert response.status_code in [200, 201, 404], f"Failed with: {response.text}"

    def test_create_meeting_activity(self, api_config, headers):
        """Test creating a meeting activity."""
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        payload = {
            "company_id": api_config["company_id"],
            "action": "activities",
            "option": "create",
            "title": "Client Meeting",
            "phone": api_config["test_phone"],
            "type_of_activity": "reunion",
            "date": next_week,
            "start_time": "15:00",
            "duration": "60",
            "location": "Office",
            "guests_names": "Soporte Zoa"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code in [200, 201, 404], f"Failed with: {response.text}"

    def test_update_activity(self, api_config, headers):
        """Test updating an activity."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "activities",
            "option": "update",
            "title": "Test Call",
            "phone": api_config["test_phone"],
            "completed": "completed"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200 for success, 404 if activity not found
        assert response.status_code in [200, 404], f"Failed with: {response.text}"
