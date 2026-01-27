import requests

class ZoaTags:
    def __init__(self, token):
        self.token = token
        self.api_base = "https://api.zoasuite.com/api"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": f"{self.token}"
        }

    def search(self, request_json=None):
        """
        Obtiene todas las etiquetas del tenant.
        Endpoint: GET /api/pipelines/tags
        """
        url = f"{self.api_base}/pipelines/tags"
        
        try:
            print(f"DEBUG: Consultando etiquetas en {url}")
            response = requests.get(url, headers=self.headers)
            
            # Devolvemos el json y el status code para que el main.py lo gestione
            return response.json(), response.status_code
            
        except Exception as e:
            return {"error": f"Error al obtener etiquetas: {str(e)}"}, 500
    
    def create(self, request_json):
        url = f"{self.api_base}/pipelines/tags"
        
        # CAMBIO CLAVE: El tipo debe ser 'sales' para que aparezca en el selector de las cards
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