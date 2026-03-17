import os
import requests
from models.contacts import ZoaContact
from models.cards import ZoaCard
from models.users import ZoaUser


class ZoaActivity:
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
        contact_id = self._resolve_contact_id(request_json)
        if not contact_id:
            return {"error": "No se encontró el contacto para recuperar sus actividades"}, 404
        try:
            response = requests.get(f"{self.api_base}/pipelines/activities/contact/{contact_id}", headers=self.headers)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def create(self, request_json):
        contact_id = self._resolve_contact_id(request_json)

        card_id = None
        card_name = request_json.get("card_name")
        if card_name:
            card_id = self._resolve_card_id(card_name)

        user_id = self._resolve_user_id(request_json.get("manager_name") or request_json.get("user_name"))
        guests_ids = self._resolve_guests(request_json.get("guests_names"))

        payload = {
            "title": request_json.get("title"),
            "type_of_activity": request_json.get("type_of_activity", "llamada"),
            "contact_id": contact_id,
            "card_id": card_id,
            "type": request_json.get("type", "sales"),
            "date": request_json.get("date"),
            "start_time": request_json.get("start_time"),
            "duration": str(request_json.get("duration") or "30"),
            "completed": request_json.get("completed", "not_completed"),
            "description": request_json.get("description"),
            "comment": request_json.get("comment"),
            "location": request_json.get("location"),
            "videocall_link": request_json.get("videocall_link"),
            "all_day": str(request_json.get("all_day", "")).lower() == "true",
            "guests": guests_ids,
            "repeat": str(request_json.get("repeat", "")).lower() == "true",
            "repetition_type": request_json.get("repetition_type"),
            "repetitions_number": int(request_json.get("repetitions_number")) if request_json.get("repetitions_number") else None,
            "days": request_json.get("days", []),
            "end_type": request_json.get("end_type", "never"),
            "end_date": request_json.get("end_date"),
            "end_after_occurrences": request_json.get("end_after_occurrences"),
            "user_id": user_id
        }
        payload = {k: v for k, v in payload.items() if v is not None and v != ""}
        try:
            response = requests.post(f"{self.api_base}/pipelines/activities", headers=self.headers, json=payload)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def update(self, request_json):
        activity_id = request_json.get("activity_id")
        target_title = request_json.get("title")

        if not activity_id and target_title:
            if any(request_json.get(k) for k in ["phone", "email", "nif"]):
                act_res, act_status = self.search(request_json)
                if act_status == 200:
                    found = next((a for a in act_res.get("data", []) if a.get("title") == target_title), None)
                    if found:
                        activity_id = found.get("id")

            if not activity_id:
                try:
                    response = requests.get(f"{self.api_base}/pipelines/activities", headers=self.headers)
                    if response.status_code == 200:
                        found = next((a for a in response.json().get("data", []) if a.get("title") == target_title), None)
                        if found:
                            activity_id = found.get("id")
                except Exception:
                    pass

        if not activity_id:
            return {"error": f"No se pudo localizar ninguna actividad con el título '{target_title}'"}, 404

        guests_ids = self._resolve_guests(request_json.get("guests_names"))
        patch = {}
        for field in ["title", "description", "completed", "date", "start_time", "duration"]:
            val = request_json.get(f"new_{field}") or request_json.get(field)
            if val is not None and val != "":
                patch[field] = val
        if guests_ids:
            patch["guests"] = guests_ids

        try:
            response = requests.patch(f"{self.api_base}/pipelines/activities/{activity_id}", headers=self.headers, json=patch)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    # ── Internal ──────────────────────────────────────────────────────────────

    def _resolve_contact_id(self, request_json):
        if not any(request_json.get(k) for k in ["phone", "email", "nif", "mobile"]):
            return None
        c_res, c_status = self.contact_manager.search(request_json)
        if c_status != 200 or not isinstance(c_res, dict):
            return None
        data = c_res.get("data")
        if isinstance(data, list) and data:
            return data[0].get("id")
        if isinstance(data, dict):
            return data.get("id")
        return None

    def _resolve_card_id(self, card_name):
        card_res, card_status = self.card_manager.search({"title": card_name})
        if card_status != 200 or not isinstance(card_res, dict):
            return None
        data = card_res.get("data")
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
        u_data = u_res.get("data")
        if isinstance(u_data, list) and u_data:
            return u_data[0].get("id")
        if isinstance(u_data, dict):
            return u_data.get("id")
        return None

    def _resolve_guests(self, guests_names):
        if not guests_names:
            return []
        ids = []
        for name in (n.strip() for n in guests_names.split(",") if n.strip()):
            uid = self._resolve_user_id(name)
            if uid:
                ids.append(uid)
        return ids
