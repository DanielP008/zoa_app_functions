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

    def update(self, request_json):
        """
        Actualiza las etiquetas de una card específica.
        :param request_json: Diccionario con 'card_id' y 'tags_name'.
        """
        card_id = request_json.get("card_id")
        tags_name = request_json.get("tags_name")
        
        if not card_id:
            return {"error": "El card_id es obligatorio"}, 400

        # 1. Resolver los IDs de las etiquetas basándose en sus nombres
        tag_ids = self._resolve_tag_ids(tags_name)
        
        # 2. Realizar el PATCH a la card para actualizar sus etiquetas
        payload = {"tag_id": tag_ids}
        try:
            url = f"{self.api_base}/pipelines/cards/{card_id}"
            response = requests.patch(url, headers=self.headers, json=payload)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": f"Error al actualizar etiquetas de la card: {str(e)}"}, 500

    # ── Internal ──────────────────────────────────────────────────────────────

    def _resolve_tag_ids(self, tags_name):
        if not tags_name:
            return []
        
        if isinstance(tags_name, str):
            names = [t.strip().lower() for t in tags_name.split(",") if t.strip()]
        elif isinstance(tags_name, list):
            names = [str(t).strip().lower() for t in tags_name if str(t).strip()]
        else:
            return []

        tags_res, status = self.search()
        if status != 200:
            return []
            
        tag_map = {t.get("name", "").lower().strip(): t.get("id") for t in tags_res.get("data", [])}
        return [tag_map[n] for n in names if n in tag_map]
