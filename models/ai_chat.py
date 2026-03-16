import os
import requests


class ZoaAIChat:
    def __init__(self, token=None, api_base=None):
        self.token = str(token or os.getenv("TOKEN")).strip()
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": self.token
        }

    def send(self, request_json):
        user_id = request_json.get("user_id")
        if not user_id:
            return {"error": "El campo 'user_id' es obligatorio."}, 400
        body = request_json.get("body")
        if not body or not isinstance(body, dict) or "data" not in body:
            return {"error": "El campo 'body' debe ser un dict con clave 'data'."}, 400
        return self._post({
            "body_type": request_json.get("body_type", "text"),
            "body": body,
            "user_id": str(user_id)
        })

    def create(self, request_json):
        return self._sheet_action("create", request_json, default_complete="false")

    def update(self, request_json):
        return self._sheet_action("update", request_json, default_complete="true")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _sheet_action(self, action, request_json, default_complete="false"):
        user_id = request_json.get("user_id")
        body_type = request_json.get("body_type")
        call_id = request_json.get("call_id")
        if not user_id:
            return {"error": "El campo 'user_id' es obligatorio."}, 400
        if not body_type:
            return {"error": "El campo 'body_type' es obligatorio (auto_sheet / home_sheet)."}, 400
        if not call_id:
            return {"error": "El campo 'call_id' es obligatorio."}, 400
        return self._post({
            "body_type": body_type,
            "action": action,
            "call_id": call_id,
            "user_id": str(user_id),
            "complete": str(request_json.get("complete", default_complete)).lower(),
            "body": {"data": request_json.get("data", {})}
        })

    def _post(self, payload):
        url = f"{self.api_base.rstrip('/')}/pipelines/assistant-chat/ai"
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            try:
                return response.json(), response.status_code
            except Exception:
                return {"response": response.text}, response.status_code
        except requests.exceptions.Timeout:
            return {"error": "Request timeout al enviar mensaje al asistente AI"}, 504
        except Exception as e:
            return {"error": str(e)}, 500
