"""Tests for cardact (card + activity) endpoint."""
import pytest
import requests
from datetime import datetime, timedelta


class TestCardAct:
    """Tests for combined card and activity creation."""

    def test_create_opportunity_with_activity(self, api_config, headers):
        """Test creating an opportunity with an associated activity."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        payload = {
            "company_id": api_config["company_id"],
            "action": "cardact",
            "option": "create",
            "title": f"Opp + Activity 2 {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "phone": api_config["test_phone"],
            "card_type": "opportunity",
            "pipeline_name": "Ventas",
            "stage_name": "Perdido",
            "amount": 5000,
            "description": "Test opportunity with activity",
            "type_of_activity": "reunion",
            "activity_title": "Follow-up reunion",
            "activity_description": "Revisar con el cliente",
            "date": tomorrow,
            "start_time": "14:00",
            "duration": "30",
            "guests_names": "Alejandro Martínez, Julio Martinez",    # names of the users to invite to the activity
            "manager_name": "Miguel Gil" #same user as the one who created the card
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200 for success, 404 if contact/pipeline not found
        assert response.status_code in [200, 201, 404], f"Failed with: {response.text}"
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "data" in data
            # Check if activity was also created
            if "activity_result" in data:
                assert data["activity_result"] is not None

    def test_create_task_with_activity(self, api_config, headers):
        """Test creating a task with an associated activity."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        payload = {
            "company_id": api_config["company_id"],
            "action": "cardact",
            "option": "create",
            "title": f"Task + Activity {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "phone": api_config["test_phone"],
            "card_type": "task",
            "description": "Test task with activity",
            "type_of_activity": "reunion",
            "activity_title": "Planning meeting",
            "activity_description": "Revisar con el cliente",
            "date": tomorrow,
            "start_time": "14:00",
            "duration": "60",
            "guests_names": "Alejandro Martínez, Julio Martinez",    # names of the users to invite to the activity
            "manager_name": "Miguel Gil" #same user as the one who created the card
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # 200 for success, 404 if contact/pipeline not found
        assert response.status_code in [200, 201, 404], f"Failed with: {response.text}"

    def test_create_card_only_no_activity(self, api_config, headers):
        """Test creating a card without activity (no type_of_activity)."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "cardact",
            "option": "create",
            "title": f"Card Only {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "phone": api_config["test_phone"],
            "card_type": "opportunity",
            "amount": 3000
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code in [200, 201, 404], f"Failed with: {response.text}"
        
        if response.status_code in [200, 201]:
            data = response.json()
            # Should not have activity_result
            assert "activity_result" not in data or data.get("activity_result") is None
