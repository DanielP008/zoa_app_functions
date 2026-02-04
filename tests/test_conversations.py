"""Tests for WhatsApp conversations (WABA) endpoints."""
import pytest
import requests


class TestConversations:
    """Tests for conversation/messaging operations."""

    def test_send_text_message(self, api_config, headers):
        """Test sending a text message via WhatsApp."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "conversations",
            "option": "send",
            "type": "text",
            "to": api_config["test_phone"],
            "text": "Test message from automated tests"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        assert response.status_code in [200, 201], f"Failed with: {response.text}"
        data = response.json()
        assert "success" in data or "data" in data
    
    def test_send_buttons_text_message(self, api_config, headers):
        """Test sending a buttons_text message via WhatsApp."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "conversations",
            "option": "send",
            "type": "buttons_text",
            # For buttons_text we build conversation_id from company_id + phone
            "phone": api_config["test_phone"],
            "text": "Selecciona una opción",
            "bt1": "Opción 1",
            "bt2": "Opción 2",
            "bt3": "Opción 3"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # Expect 200/201 for success (same as plain text)
        assert response.status_code in [200, 201], f"Failed with: {response.text}"
        data = response.json()
        assert "success" in data or "data" in data

    def test_send_template_message(self, api_config, headers):
        """Test sending a WhatsApp template message."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "conversations",
            "option": "send",
            "type": "template",
            "to": api_config["test_phone"],
            "template_name": "welcome_message",
            "data": {
                "body": ["Test User"],
                "button": [],
                "header": []
            }
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # Template might not exist, so 404 is acceptable
        assert response.status_code in [200, 201, 404], f"Failed with: {response.text}"

    def test_assign_conversation(self, api_config, headers):
        """Test assigning a conversation to a user."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "conversations",
            "option": "assign",
            "phone": api_config["test_phone"],
            "manager_name": "Soporte Zoa"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # Conversation might not exist yet, 404 is acceptable
        assert response.status_code in [200, 404], f"Failed with: {response.text}"

    def test_update_conversation_status(self, api_config, headers):
        """Test updating conversation sales status."""
        payload = {
            "company_id": api_config["company_id"],
            "action": "conversations",
            "option": "status",
            "phone": api_config["test_phone"],
            "sales_status": "pending"
        }

        response = requests.post(
            api_config["base_url"],
            headers=headers,
            json=payload
        )

        # Conversation might not exist, 404 is acceptable
        assert response.status_code in [200, 404], f"Failed with: {response.text}"
