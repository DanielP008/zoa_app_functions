import os
from datetime import datetime
import firebase_admin
from firebase_admin import firestore


class ZoaScheduler:
    def __init__(self, token=None, api_base=None):
        self.token = token or os.getenv("TOKEN")
        self.api_base = api_base or os.getenv("API_BASE")

    def search(self, request_json):
        company_id = str(request_json.get("company_id"))
        if request_json.get("option") != "search":
            return {"error": "Opción no soportada"}, 400
        if not company_id:
            return {"error": "Se requiere 'company_id'"}, 400
        try:
            db = firestore.client()
            docs = db.collection("clientIDs").where(
                filter=firestore.FieldFilter("ids", "array_contains", company_id)
            ).get()
            
            if not docs:
                return {"error": f"Cuenta {company_id} no encontrada en Firebase"}, 404

            data = docs[0].to_dict() or {}
            scheduler = data.get("scheduler", {})

            now = datetime.now().time()
            morning = scheduler.get("morning")
            afternoon = scheduler.get("afternoon")
            
            is_open = self._in_range(morning, now) or self._in_range(afternoon, now)
            
            return {
                "is_open": is_open,
                "schedule": {
                    "morning": morning,
                    "afternoon": afternoon
                }
            }, 200
        except Exception as e:
            return {"error": str(e)}, 500

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _in_range(time_range_str, now):
        if not time_range_str or " - " not in time_range_str:
            return False
        try:
            start_str, end_str = time_range_str.split(" - ")
            start = datetime.strptime(start_str.strip(), "%H:%M").time()
            end = datetime.strptime(end_str.strip(), "%H:%M").time()
            return start <= now <= end
        except Exception:
            return False
