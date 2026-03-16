import os
import requests
from models.contacts import ZoaContact
from models.cards import ZoaCard
from models.users import ZoaUser


class ZoaReadAll:
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
        empty = {
            "contact": {"name": "Desconocido"},
            "manager": {"name": "No asignado", "phone": None},
            "open_activities_count": 0,
            "activities_details": []
        }
        try:
            c_res, c_status = self.contact_manager.search(request_json)
            if c_status != 200 or not c_res.get("data"):
                return empty, 200

            data_c = c_res.get("data")
            contact = data_c[0] if isinstance(data_c, list) else data_c
            contact_id = contact.get("id")

            manager_name, manager_phone = "No asignado", None
            m_id = contact.get("user_id") or contact.get("manager_id")
            if m_id:
                u_res, u_status = self.user_manager.search({"id": m_id})
                if u_status == 200:
                    u = u_res.get("data")
                    u_obj = u[0] if isinstance(u, list) and u else u
                    if isinstance(u_obj, dict):
                        manager_name = f"{u_obj.get('first_name', '')} {u_obj.get('last_name', '')}".strip() or u_obj.get("name")
                        manager_phone = u_obj.get("mobile") or u_obj.get("phone")

            cards_open = []
            cards_res, cards_status = self.card_manager.list_by_contact(contact_id)
            if cards_status == 200 and cards_res.get("data"):
                stage_map = self._get_stage_map()
                raw = cards_res["data"]
                for card in (raw if isinstance(raw, list) else [raw]):
                    if card.get("status") not in ("won", "lost"):
                        cards_open.append({
                            "title": card.get("title"),
                            "type": card.get("card_type", "opportunity"),
                            "stage": stage_map.get(card.get("stage_id"), "N/A")
                        })

            return {
                "contact": {"id": contact_id, "name": contact.get("name"), "nif": contact.get("nif")},
                "manager": {"id": m_id, "name": manager_name, "phone": manager_phone},
                "open_activities_count": len(cards_open),
                "activities_details": cards_open
            }, 200
        except Exception as e:
            return {"error": str(e)}, 500

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_stage_map(self):
        stage_map = {}
        try:
            for p_type in ("sales", "management"):
                res = requests.get(f"{self.api_base}/pipelines/pipelines?type={p_type}", headers=self.headers)
                if res.status_code == 200:
                    for pipe in res.json().get("data", []):
                        for stage in pipe.get("stages", []):
                            stage_map[stage.get("id")] = stage.get("title") or stage.get("name")
        except Exception:
            pass
        return stage_map
