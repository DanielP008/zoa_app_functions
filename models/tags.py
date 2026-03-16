import os
import requests


class ZoaTags:
    def __init__(self, token=None, api_base=None):
        self.token = token or os.getenv("TOKEN")
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": self.token
        }

    def search(self, request_json=None):
        try:
            response = requests.get(f"{self.api_base}/pipelines/tags", headers=self.headers)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": f"Error al obtener etiquetas: {str(e)}"}, 500

    def create(self, request_json):
        name = request_json.get("name")
        if not name:
            return {"error": "El nombre es obligatorio"}, 400
        payload = {
            "name": name,
            "type": request_json.get("type", "sales"),
            "color": request_json.get("color", "#04A37C")
        }
        try:
            response = requests.post(f"{self.api_base}/pipelines/tags", headers=self.headers, json=payload)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500
