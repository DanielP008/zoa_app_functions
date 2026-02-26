import requests
import json
import os


class ZoaAIChat:
    def __init__(self, token=None, api_base=None):
        self.token = str(token or os.getenv("TOKEN")).strip()
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": self.token
        }

    def _post_to_ai_chat(self, payload):
        """Common POST to the AI chat endpoint."""
        base = self.api_base.rstrip("/")
        url = f"{base}/pipelines/assistant-chat/ai"

        try:
            print(f"[AI_CHAT] POST {url}", flush=True)
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)

            try:
                response_data = response.json()
            except Exception:
                response_data = {"response": response.text}

            return response_data, response.status_code

        except requests.exceptions.Timeout:
            return {"error": "Request timeout al enviar mensaje al asistente AI"}, 504
        except Exception as e:
            return {"error": str(e)}, 500

    # ------------------------------------------------------------------
    # option = "send"  ->  text / button messages
    # ------------------------------------------------------------------
    def send(self, request_json):
        """
        Send a text or button message to the AI chat.

        Expected fields:
        - user_id (required)
        - body_type: "text" or "button"
        - body: {"data": "message"} for text, {"data": {"title": "..."}} for button
        """
        user_id = request_json.get("user_id")
        if not user_id:
            return {"error": "El campo 'user_id' es obligatorio."}, 400

        body = request_json.get("body")
        if not body or not isinstance(body, dict) or "data" not in body:
            return {"error": "El campo 'body' debe ser un dict con clave 'data'."}, 400

        body_type = request_json.get("body_type", "text")

        payload = {
            "body_type": body_type,
            "body": body,
            "user_id": str(user_id)
        }

        return self._post_to_ai_chat(payload)

    # ------------------------------------------------------------------
    # option = "create"  ->  create a new tarificacion sheet
    # ------------------------------------------------------------------
    def create(self, request_json):
        """
        Create a new tarificacion sheet (auto_sheet / home_sheet).

        Expected fields:
        - user_id (required)
        - body_type: "auto_sheet" or "home_sheet" (required)
        - call_id (required)
        - complete: "true" / "false" (default "false")
        - data: dict with the sheet data (vehiculo, tomador, etc.)
        """
        user_id = request_json.get("user_id")
        body_type = request_json.get("body_type")
        call_id = request_json.get("call_id")

        if not user_id:
            return {"error": "El campo 'user_id' es obligatorio."}, 400
        if not body_type:
            return {"error": "El campo 'body_type' es obligatorio (auto_sheet / home_sheet)."}, 400
        if not call_id:
            return {"error": "El campo 'call_id' es obligatorio."}, 400

        complete_str = str(request_json.get("complete", "false")).lower()
        sheet_data = request_json.get("data", {})

        payload = {
            "body_type": body_type,
            "action": "create",
            "call_id": call_id,
            "user_id": str(user_id),
            "complete": complete_str,
            "body": {
                "data": sheet_data
            }
        }

        return self._post_to_ai_chat(payload)

    # ------------------------------------------------------------------
    # option = "update"  ->  update an existing tarificacion sheet
    # ------------------------------------------------------------------
    def update(self, request_json):
        """
        Update an existing tarificacion sheet (auto_sheet / home_sheet).

        Expected fields:
        - user_id (required)
        - body_type: "auto_sheet" or "home_sheet" (required)
        - call_id (required)
        - complete: "true" / "false" (default "true")
        - data: dict with the updated sheet data
        """
        user_id = request_json.get("user_id")
        body_type = request_json.get("body_type")
        call_id = request_json.get("call_id")

        if not user_id:
            return {"error": "El campo 'user_id' es obligatorio."}, 400
        if not body_type:
            return {"error": "El campo 'body_type' es obligatorio (auto_sheet / home_sheet)."}, 400
        if not call_id:
            return {"error": "El campo 'call_id' es obligatorio."}, 400

        complete_str = str(request_json.get("complete", "true")).lower()
        sheet_data = request_json.get("data", {})

        payload = {
            "body_type": body_type,
            "action": "update",
            "call_id": call_id,
            "user_id": str(user_id),
            "complete": complete_str,
            "body": {
                "data": sheet_data
            }
        }

        return self._post_to_ai_chat(payload)
