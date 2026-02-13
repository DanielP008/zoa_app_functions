import firebase_admin
from firebase_admin import firestore
from datetime import datetime

class ZoaScheduler:
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

    def search(self, request_json):
        try:
            company_id = request_json.get('company_id')
            option = request_json.get('option')
            
            if option != "search":
                return {"error": "Opción no soportada"}, 400
            if not company_id:
                return {"error": "Se requiere 'company_id'"}, 400

            db = firestore.client()
            
            docs = (
                db.collection(u'clientIDs')
                .where(filter=firestore.FieldFilter("ids", "array_contains", company_id))
                .get()
            )

            if not docs:
                return {"error": f"Cuenta {company_id} no encontrada en Firebase"}, 404

            data = docs[0].to_dict() or {}
            domains = data.get('domains') or []

            target_domain = next((d for d in domains if d.get('phone_id') == company_id), None)
            
            if not target_domain and domains:
                target_domain = domains[0]

            scheduler_config = (target_domain or {}).get('scheduler') or data.get('scheduler', {})
            
            morning = scheduler_config.get('morning')
            afternoon = scheduler_config.get('afternoon')

            now_time = datetime.now().time()

            def is_now_in_range(time_range_str):
                if not time_range_str or " - " not in time_range_str:
                    return False
                try:
                    start_str, end_str = time_range_str.split(" - ")
                    start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
                    end_time = datetime.strptime(end_str.strip(), "%H:%M").time()
                    return start_time <= now_time <= end_time
                except Exception:
                    return False

            is_open = is_now_in_range(morning) or is_now_in_range(afternoon)
            
            return {
                "is_open": is_open,
            }, 200

        except Exception as e:
            return {"error": str(e)}, 500