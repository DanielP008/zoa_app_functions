import os
import requests
from datetime import datetime
from models.contacts import ZoaContact
from models.cards import ZoaCard
from models.users import ZoaUser


class ZoaNote:
    def __init__(self, token=None, api_base=None):
        self.token = token or os.getenv("TOKEN")
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": self.token
        }
        self.contact_manager = ZoaContact(self.token, api_base)
        self.card_manager = ZoaCard(self.token, api_base)
        self.user_manager = ZoaUser(self.token, api_base)

    def search(self, request_json):
        contact_id = self._get_contact_id(request_json)
        if not contact_id:
            return {"error": "No se localizó el contacto para obtener sus notas"}, 404
        try:
            response = requests.get(f"{self.api_base}/pipelines/notes/contact/{contact_id}", headers=self.headers)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def create(self, request_json):
        contact_id = self._get_contact_id(request_json)
        if not contact_id:
            return {"error": "No se puede identificar al contacto"}, 404

        card_id = request_json.get("card_id")
        if not card_id:
            card_res, card_status = self.card_manager.search({"contact_id": contact_id})
            if card_status == 200:
                cards = card_res.get("data", [])
                if cards:
                    card_id = cards[0].get("id")

        user_id = request_json.get("user_id") or self._resolve_user_id(
            request_json.get("manager_name") or request_json.get("user_name")
        )

        payload = {
            "contact_id": contact_id,
            "card_id": card_id,
            "user_id": user_id,
            "content": request_json.get("content"),
            "date": request_json.get("date", datetime.now().strftime("%Y-%m-%d")),
            "is_pinned": request_json.get("is_pinned", False)
        }
        try:
            response = requests.post(f"{self.api_base}/pipelines/notes", headers=self.headers, json=payload)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def update(self, request_json):
        search_res, status = self.search(request_json)
        if status != 200:
            return search_res, status

        notes_list = search_res.get("data")
        if not isinstance(notes_list, list):
            return {"error": "La API no devolvió una lista de notas válida"}, 500

        target_date = request_json.get("date")
        old_content = request_json.get("old_content")
        note_id = None
        for note in notes_list:
            if note.get("date") != target_date:
                continue
            if old_content:
                if old_content.lower() in note.get("content", "").lower():
                    note_id = note.get("id")
                    break
            else:
                note_id = note.get("id")
                break

        if not note_id:
            return {"error": f"No se encontró nota en fecha {target_date}"}, 404

        user_id = self._resolve_user_id(request_json.get("manager_name"))
        payload = {
            "content": request_json.get("new_content") or request_json.get("content"),
            "is_pinned": request_json.get("is_pinned"),
            "user_id": user_id
        }
        clean = {k: v for k, v in payload.items() if v is not None}
        try:
            response = requests.patch(f"{self.api_base}/pipelines/notes/{note_id}", headers=self.headers, json=clean)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_contact_id(self, request_json):
        if request_json.get("contact_id"):
            return request_json["contact_id"]
        c_res, c_status = self.contact_manager.search(request_json)
        if c_status != 200 or not isinstance(c_res, dict):
            return None
        data = c_res.get("data", [])
        if isinstance(data, list) and data:
            return data[0].get("id")
        if isinstance(data, dict):
            return data.get("id")
        return None

    def _resolve_user_id(self, name):
        if not name:
            return None
        u_res, u_status = self.user_manager.search({"name": name})
        if u_status != 200:
            return None
        u_data = u_res.get("data", [])
        if isinstance(u_data, list) and u_data:
            return u_data[0].get("id")
        if isinstance(u_data, dict):
            return u_data.get("id")
        return None
