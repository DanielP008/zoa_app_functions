"""Integration tests for scheduler endpoint via Docker container."""
import pytest
import requests


class TestScheduler:
    """Integration tests for the scheduler endpoint against the running service."""

    # Company ID with scheduler config in Firestore (waba_accounts)
    SCHEDULER_COMPANY_ID = "9827699917317289"

    def test_search_scheduler(self, api_config, headers):
        """Test scheduler search returns is_open status."""
        payload = {
            "company_id": self.SCHEDULER_COMPANY_ID,
            "action": "scheduler",
            "option": "search",
        }

        print(f"\n[SCHEDULER_TEST] Calling {api_config['base_url']} with company_id: {self.SCHEDULER_COMPANY_ID}")

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload,
        )

        print(f"[SCHEDULER_TEST] Status: {response.status_code}, Body: {response.text}")

        assert response.status_code == 200, f"Failed with: {response.text}"
        data = response.json()
        assert "is_open" in data
        assert isinstance(data["is_open"], bool) 

        print(f"[SCHEDULER_TEST] all data: {data}")

        print(f"[SCHEDULER_TEST] is_open: {data['is_open']}")
