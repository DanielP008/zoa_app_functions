import os
import requests


class ZoaEmail:
    def __init__(self, token=None, api_base=None):
        self.token = token or os.getenv("TOKEN")
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def send(self, request_json):
        exclude = {"company_id", "action", "option", "token"}
        final_data = {k: v for k, v in request_json.items() if k not in exclude and v is not None}
        try:
            response = requests.post(self.api_base, headers=self.headers, json=final_data)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500
