from tarfile import data_filter
import firebase_admin
from firebase_admin import firestore

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

            db = firestore.client()
            
            # Look up document in waba_accounts where doc ID is company_id
            doc_ref = db.collection(u'clientIDs').where("ids", "array_contains", company_id).get()

            if not doc_ref.exists:
                return {"error": f"Cuenta {company_id} no encontrada en Firebase"}, 404

            data = doc_ref.to_dict()

            scheduler = data.get('scheduler', {})
            
            return {
                "morning": scheduler.get('morning', "No definido"),
                "afternoon": scheduler.get('afternoon', "No definido")
            }, 200

        except Exception as e:
            print(f"Error en Scheduler: {str(e)}")
            return {"error": str(e)}, 500