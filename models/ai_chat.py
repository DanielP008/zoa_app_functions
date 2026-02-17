import requests
import json
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
        logger.info(f"[AI_CHAT] Initialized ZoaAIChat with api_base={self.api_base}, token={'*' * 4}{self.token[-6:]}")

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
        logger.info(f"[AI_CHAT] ====== START ai_chat.send() ======")
        logger.info(f"[AI_CHAT] Raw request_json received: {json.dumps(request_json, ensure_ascii=False, default=str)}")

        # 1. Validate required fields
        user_id = request_json.get("user_id")
        logger.info(f"[AI_CHAT] Extracted user_id: {user_id}")
        if not user_id:
            logger.info(f"[AI_CHAT] VALIDATION FAILED: user_id is missing or empty")
            return {"error": "El campo 'user_id' es obligatorio."}, 400

        body = request_json.get("body")
        logger.info(f"[AI_CHAT] Extracted body: {body}")
        logger.info(f"[AI_CHAT] Body type (python): {type(body).__name__}")
        if not body:
            logger.info(f"[AI_CHAT] VALIDATION FAILED: body is missing or empty")
            return {"error": "El campo 'body' es obligatorio."}, 400

        # 2. Validate body format - must be a dict with 'data' key
        if not isinstance(body, dict) or "data" not in body:
            logger.info(f"[AI_CHAT] VALIDATION FAILED: body is not a dict with 'data' key. Got: {body}")
            return {"error": "El campo 'body' debe ser un diccionario con la clave 'data'. Ejemplo: {'data': 'tu mensaje'}"}, 400

        logger.info(f"[AI_CHAT] body['data'] content: {body['data']}")
        logger.info(f"[AI_CHAT] All validations passed")

        # 3. Prepare payload (exclude fields used only for routing)
        body_type = request_json.get("body_type", "text")
        logger.info(f"[AI_CHAT] body_type: {body_type}")

        # Only include the fields expected by the AI chat API
        payload = {
            "body_type": body_type,
            "body": body,
            "user_id": str(user_id)
        }

        # 4. Build endpoint URL
        base = self.api_base.rstrip('/')
        url = f"{base}/pipelines/assistant-chat/ai"

        logger.info(f"[AI_CHAT] Target URL: {url}")
        logger.info(f"[AI_CHAT] Request headers: Content-Type={self.headers['Content-Type']}, Accept={self.headers['Accept']}, apiKey=****{self.token[-6:]}")
        logger.info(f"[AI_CHAT] Final payload being sent: {json.dumps(payload, ensure_ascii=False, default=str)}")

        try:
            logger.info(f"[AI_CHAT] Sending POST request to ZOA API...")
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)

            logger.info(f"[AI_CHAT] Response HTTP status code: {response.status_code}")
            logger.info(f"[AI_CHAT] Response headers: {dict(response.headers)}")
            logger.info(f"[AI_CHAT] Response raw text: {response.text}")

            # Try to parse JSON response
            try:
                response_data = response.json()
                logger.info(f"[AI_CHAT] Response parsed as JSON: {json.dumps(response_data, ensure_ascii=False, default=str)}")
            except Exception as parse_err:
                response_data = {"response": response.text}
                logger.info(f"[AI_CHAT] Response is NOT JSON, wrapping raw text. Parse error: {parse_err}")

            if response.status_code >= 400:
                logger.info(f"[AI_CHAT] ZOA API returned error status {response.status_code}: {response_data}")
            else:
                logger.info(f"[AI_CHAT] SUCCESS - Message sent to AI chat. Status: {response.status_code}")

            logger.info(f"[AI_CHAT] ====== END ai_chat.send() ======")
            return response_data, response.status_code

        except requests.exceptions.Timeout:
            logger.info(f"[AI_CHAT] ERROR: Request timed out after 30s to {url}")
            logger.info(f"[AI_CHAT] ====== END ai_chat.send() (TIMEOUT) ======")
            return {"error": "Request timeout al enviar mensaje al asistente AI"}, 504
        except requests.exceptions.ConnectionError as conn_err:
            logger.info(f"[AI_CHAT] ERROR: Connection failed to {url}. Details: {conn_err}")
            logger.info(f"[AI_CHAT] ====== END ai_chat.send() (CONNECTION ERROR) ======")
            return {"error": f"Error de conexión al asistente AI: {str(conn_err)}"}, 502
        except Exception as e:
            logger.info(f"[AI_CHAT] ERROR: Unexpected exception: {type(e).__name__}: {str(e)}")
            logger.exception("[AI_CHAT] Full traceback:")
            logger.info(f"[AI_CHAT] ====== END ai_chat.send() (EXCEPTION) ======")
            return {"error": f"Error al enviar mensaje: {str(e)}"}, 500
