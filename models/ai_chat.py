import requests
import logging

logger = logging.getLogger(__name__)

class ZoaAIChat:
    def __init__(self, token=None, api_base=None):
        import os
        # Use env vars directly (Global configuration)
        self.token = str(token or os.getenv("TOKEN")).strip()
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": self.token
        }

    def send(self, request_json):
        """
        Send a message to the AI chat assistant.

        Args:
            request_json (dict):
                - body (dict, required): The message body with 'data' key. Format: {"data": "message text"}
                - body_type (str, optional): Type of body content (default: 'text').
                - user_id (str, required): The user ID for the chat session.
                - company_id (str): Used for routing in main.py, excluded from API payload.

        Returns:
            tuple: (response_dict, status_code)
        """
        logger.info(f"[FLOW_ZOA_DEBUG] AI Chat Send called with data: {request_json}")
        
        # 1. Validate required fields
        user_id = request_json.get("user_id")
        if not user_id:
            logger.warning("[FLOW_ZOA_DEBUG] AI Chat Send failed: missing user_id")
            return {"error": "El campo 'user_id' es obligatorio."}, 400

        body = request_json.get("body")
        if not body:
            logger.warning("[FLOW_ZOA_DEBUG] AI Chat Send failed: missing body")
            return {"error": "El campo 'body' es obligatorio."}, 400

        # 2. Validate body format - must be a dict with 'data' key
        if not isinstance(body, dict) or "data" not in body:
            logger.warning(f"[FLOW_ZOA_DEBUG] AI Chat Send failed: invalid body format: {body}")
            return {"error": "El campo 'body' debe ser un diccionario con la clave 'data'. Ejemplo: {'data': 'tu mensaje'}"}, 400

        # 3. Prepare payload (exclude fields used only for routing)
        # Fields that must NOT go in the ZOA API body
        exclude = ['company_id', 'action', 'option', 'token']
        
        body_type = request_json.get("body_type", "text")

        # Only include the fields expected by the AI chat API
        payload = {
            "body_type": body_type,
            "body": body,
            "user_id": str(user_id)
        }

        # 3. Build endpoint URL
        base = self.api_base.rstrip('/')
        url = f"{base}/pipelines/assistant-chat/ai"

        try:
            logger.info(f"[FLOW_ZOA_DEBUG] Sending to {url} with user_id={user_id} and payload={payload}")
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            logger.info(f"[FLOW_ZOA_DEBUG] AI Chat Response status: {response.status_code}")
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                logger.info(f"[FLOW_ZOA_DEBUG] AI Chat Response data: {response_data}")
            except Exception:
                response_data = {"response": response.text}
                logger.info(f"[FLOW_ZOA_DEBUG] AI Chat Response text: {response.text}")
            
            return response_data, response.status_code

        except requests.exceptions.Timeout:
            logger.error("[FLOW_ZOA_DEBUG] AI Chat Request timeout")
            return {"error": "Request timeout al enviar mensaje al asistente AI"}, 504
        except Exception as e:
            logger.exception("[FLOW_ZOA_DEBUG] Error sending AI chat message")
            return {"error": f"Error al enviar mensaje: {str(e)}"}, 500
