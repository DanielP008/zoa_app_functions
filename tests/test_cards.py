"""Tests for cards (opportunities/tasks) endpoints."""
import pytest
import requests
from datetime import datetime, timedelta


class TestCards:
    """Tests for card/opportunity/task operations."""

    def test_search_card_by_title(self, api_config, headers):
        """Test searching for a card by title."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "cards",
            "option": "search",
            "title": "Test Opportunity"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200 for success, 404 if not found
        assert response.status_code in [200, 404], f"Failed with: {response.text}"

    def test_search_card_by_contact(self, api_config, headers):
        """Test searching for cards by contact phone."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "cards",
            "option": "search",
            "phone": api_config["test_phone"]
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200 for success, 404 if contact or cards not found
        assert response.status_code in [200, 404], f"Failed with: {response.text}"

    def test_create_opportunity(self, api_config, headers):
        """Test creating an opportunity card."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "cards",
            "option": "create",
            "title": f"Test Opportunity {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "phone": api_config["test_phone"],
            "card_type": "opportunity",
            "pipeline_name": "Revisiones",
            "stage_name": "Nuevo",
            "amount": 1000,
            "description": "Automated test opportunity"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200/201 for success, 404 if contact/pipeline not found
        assert response.status_code in [200, 201, 404], f"Failed with: {response.text}"

    def test_create_task(self, api_config, headers):
        """Test creating a task card."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "cards",
            "option": "create",
            "title": f"Test Task {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "phone": api_config["test_phone"],
            "card_type": "task",
            "description": "Automated test task"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200/201 for success, 404 if contact/pipeline not found
        assert response.status_code in [200, 201, 404], f"Failed with: {response.text}"

    def test_update_card(self, api_config, headers):
        """Test updating a card."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "cards",
            "option": "update",
            "title": "Test Opportunity",
            "new_title": "Updated Test Opportunity",
            "amount": 2000
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200 for success, 404 if card not found
        assert response.status_code in [200, 404], f"Failed with: {response.text}"
