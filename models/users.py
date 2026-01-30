import requests
from urllib.parse import quote

class ZoaUser:
    def __init__(self, token):
        from config import API_BASE
        self.token = token
        self.api_base = API_BASE
        self.base_url = f"{self.api_base}/pipelines/users"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": f"{self.token}"
        }

    def search(self, request_json):
        user_id = request_json.get("id")
        name = request_json.get("manager_name") or request_json.get("name")
        
        try:
            # Si tenemos nombre, usamos el endpoint de búsqueda por nombre
            if name and not user_id:
                url = f"{self.base_url}/name/{quote(name.strip())}"
                response = requests.get(url, headers=self.headers)
                return response.json(), response.status_code

            # Si tenemos ID (o nada), traemos la lista completa para filtrar
            # Ya que no existe GET /users/{id} según tu documentación
            response = requests.get(self.base_url, headers=self.headers)
            if response.status_code == 200:
                users_list = response.json().get("data", [])
                if user_id:
                    # Buscamos el objeto que coincida con el ID
                    user_found = next((u for u in users_list if str(u.get("id")) == str(user_id)), None)
                    if user_found:
                        return {"success": True, "data": user_found}, 200
                return {"success": True, "data": users_list}, 200
            
            return {"error": "No se pudo obtener la lista de usuarios"}, response.status_code
        except Exception as e:
            return {"error": str(e)}, 500