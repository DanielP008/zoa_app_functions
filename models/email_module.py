import requests

class ZoaEmail:
    def __init__(self, token=None):
        from config import API_BASE, TOKEN
        self.token = token or TOKEN
        self.api_base = f"{API_BASE}/email/send"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def send(self, request_json):
        """
        Envía un email a través del endpoint de ZOA.
        """
        # 1. Lista de campos que NO deben ir en el body de la API de ZOA
        exclude = ['company_id', 'action', 'option', 'token']
        
        # 2. Limpieza del request_json
        # Mantenemos: to, subject, body, body_type, cc, bcc, reply_to, thread_id
        final_data = {k: v for k, v in request_json.items() if k not in exclude and v is not None}

        try:
            # Enviamos la petición POST al endpoint específico
            response = requests.post(self.api_base, headers=self.headers, json=final_data)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500