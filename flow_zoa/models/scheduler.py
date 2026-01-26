import firebase_admin
from firebase_admin import firestore

class ZoaScheduler:
    def __init__(self, token):
        self.token = token
        self.api_base = "https://api.zoasuite.com/api"
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
            
            # Buscamos el documento en waba_accounts donde el ID del documento es el company_id
            doc_ref = db.collection(u'waba_accounts').document(company_id).get()

            if not doc_ref.exists:
                return {"error": f"Cuenta {company_id} no encontrada en Firebase"}, 404

            data = doc_ref.to_dict()
            domains = data.get('domains', [])

            # Navegamos según tu estructura: domains (array) -> 0 -> scheduler (map)
            # Buscamos el dominio que coincida con el phone_id solicitado
            target_domain = next((d for d in domains if d.get('phone_id') == company_id), None)
            
            # Si no hay coincidencia exacta por ID, intentamos con el primero por defecto
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