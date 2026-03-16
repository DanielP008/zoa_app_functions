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
        :param request_json: Diccionario con 'card_id' y ('tags_name' o 'tag_id').
        """
        card_id = request_json.get("card_id")
        tags_name = request_json.get("tags_name")
        tag_id = request_json.get("tag_id")
        
        if not card_id:
            return {"error": "El card_id es obligatorio"}, 400

        # 1. Resolver los IDs de las etiquetas
        if tag_id:
            # Si ya nos pasan IDs, nos aseguramos de que sea una lista
            final_tag_ids = tag_id if isinstance(tag_id, list) else [tag_id]
        elif tags_name:
            # Si nos pasan nombres, los resolvemos a IDs
            final_tag_ids = self._resolve_tag_ids(tags_name)
        else:
            return {"error": "Se requiere 'tags_name' o 'tag_id'"}, 400
        
        # 2. Realizar el PATCH a la card para actualizar sus etiquetas
        payload = {"tag_id": final_tag_ids}
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
