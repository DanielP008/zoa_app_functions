"""Tests for WABA message retrieval via conversations endpoint."""
import pytest
import requests


class TestWabaMessages:
    """Tests for fetching a WABA message by its wamid through the conversations action."""

    def test_search_message_by_wamid(self, api_config, headers):
        """Test retrieving a WABA message by wamid — inspect the raw response."""
        # Replace with a real wamid to test against the live API
        test_wamid = "wamid.HBgNNTQ5MTEzMzgzMTcwNRUCABIYFjNFQjA4NTE0MDZGOUFENDdDMENBOEUA"

        payload = {
            "company_id": "521783407682043",
            "action": "conversations",
            "option": "search",
            "wamid": test_wamid
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        print(f"\n--- WABA Message Search Response ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        print(f"------------------------------------")

        # We accept multiple status codes since the wamid may or may not exist
        assert response.status_code in [200, 404, 400], (
            f"Unexpected status {response.status_code}: {response.text}"
        )

    def test_search_missing_wamid(self, api_config, headers):
        """Test that missing wamid returns 400."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "conversations",
            "option": "search",
            # wamid intentionally omitted
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        print(f"\n--- Missing wamid Response ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        print(f"------------------------------")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
