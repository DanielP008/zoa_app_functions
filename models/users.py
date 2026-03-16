import os
import requests
from urllib.parse import quote


class ZoaUser:
    def __init__(self, token=None, api_base=None):
        self.token = token or os.getenv("TOKEN")
        self.api_base = api_base or os.getenv("API_BASE")
        self.base_url = f"{self.api_base}/pipelines/users"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": self.token
        }

    def search(self, request_json):
        user_id = request_json.get("id")
        name = request_json.get("manager_name") or request_json.get("name")
        try:
            if name and not user_id:
                response = requests.get(f"{self.base_url}/name/{quote(name.strip())}", headers=self.headers)
                return response.json(), response.status_code

            response = requests.get(self.base_url, headers=self.headers)
            if response.status_code != 200:
                return {"error": "No se pudo obtener la lista de usuarios"}, response.status_code

            users_list = response.json().get("data", [])
            if user_id:
                found = next((u for u in users_list if str(u.get("id")) == str(user_id)), None)
                if found:
                    return {"success": True, "data": found}, 200
            return {"success": True, "data": users_list}, 200
        except Exception as e:
            return {"error": str(e)}, 500
