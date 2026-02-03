import firebase_admin
from firebase_admin import firestore

class ZoaScheduler:
    def __init__(self, token=None, api_base=None):
        from config import API_BASE, TOKEN
        self.token = token or TOKEN
        self.api_base = api_base or API_BASE
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
            doc_ref = db.collection(u'waba_accounts').document(company_id).get()

            if not doc_ref.exists:
                return {"error": f"Cuenta {company_id} no encontrada en Firebase"}, 404

            data = doc_ref.to_dict()
            domains = data.get('domains', [])

            # Navigate structure: domains (array) -> 0 -> scheduler (map)
            # Buscamos el dominio que coincida con el phone_id solicitado
            target_domain = next((d for d in domains if d.get('phone_id') == company_id), None)
            
            # If no exact ID match, try first as default
            if not target_domain and domains:
                target_domain = domains[0]

            if not target_domain:
                return {"error": "No se encontró configuración de dominio"}, 404

            scheduler = target_domain.get('scheduler', {})
            
            return {
                "morning": scheduler.get('morning', "No definido"),
                "afternoon": scheduler.get('afternoon', "No definido")
            }, 200

        except Exception as e:
            print(f"Error en Scheduler: {str(e)}")
            return {"error": str(e)}, 500