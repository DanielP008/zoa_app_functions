import requests

class ZoaTags:
    def __init__(self, token=None, api_base=None):
        import os
        # Use env vars directly (Global configuration)
        self.token = token or os.getenv("TOKEN")
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": f"{self.token}"
        }

    def search(self, request_json=None):
        """
        Gets all tags for the tenant.
        Endpoint: GET /api/pipelines/tags
        """
        url = f"{self.api_base}/pipelines/tags"
        
        try:
            print(f"DEBUG: Consultando etiquetas en {url}")
            response = requests.get(url, headers=self.headers)
            
            # Return json and status code for main.py to handle
            return response.json(), response.status_code
            
        except Exception as e:
            return {"error": f"Error al obtener etiquetas: {str(e)}"}, 500
    
    def create(self, request_json):
        url = f"{self.api_base}/pipelines/tags"
        
        # Type must be 'sales' so it appears in the card selector
        tag_type = request_json.get("type", "sales") 
        
        payload = {
            "name": request_json.get("name"),
            "type": tag_type,
            "color": request_json.get("color", "#04A37C")
        }

        if not payload["name"]:
            return {"error": "El nombre es obligatorio"}, 400

        try:
            print(f"DEBUG: Creando etiqueta '{payload['name']}' con tipo '{payload['type']}'")
            response = requests.post(url, headers=self.headers, json=payload)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500