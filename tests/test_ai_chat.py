"""Tests for AI Chat assistant endpoints."""
import pytest
import requests


class TestAIChat:
    """Tests for AI Chat operations."""

    def test_send_text_message(self, api_config, headers):
        """Test sending a text message to the AI chat assistant."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "ai_chat",
            "option": "send",
            "user_id": "202",
            "body": {
                "data": "Hola, ¿cómo estás?"
            }
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code in [200, 201], f"Failed with: {response.text}"
        data = response.json()
        # Verify response structure (adjust based on actual API response)
        assert data is not None

    def test_send_message_with_body_type(self, api_config, headers):
        """Test sending a message with explicit body_type."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "ai_chat",
            "option": "send",
            "user_id": "202",
            "body": {
                "data": "Hola de nuevo"
            },
            "body_type": "text"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code in [200, 201], f"Failed with: {response.text}"
        data = response.json()
        assert data is not None

    def test_send_without_user_id(self, api_config, headers):
        """Test that sending without user_id returns error."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "ai_chat",
            "option": "send",
            "body": {
                "data": "Test message"
            }
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "user_id" in data["error"].lower()

    def test_send_without_body(self, api_config, headers):
        """Test that sending without body returns error."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "ai_chat",
            "option": "send",
            "user_id": "202"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "body" in data["error"].lower()

    def test_send_with_invalid_body_format(self, api_config, headers):
        """Test that sending body without 'data' key returns error."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "ai_chat",
            "option": "send",
            "user_id": "202",
            "body": {
                "message": "Invalid format"  # Wrong key - should be 'data'
            }
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "data" in data["error"].lower()
