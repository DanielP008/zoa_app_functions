import requests

class ZoaEmail:
    def __init__(self, token=None, api_base=None):
        from config import API_BASE, TOKEN
        self.token = token or TOKEN
        self.api_base = api_base or API_BASE
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def send(self, request_json):
        """
        Sends an email via ZOA endpoint.
        """
        # 1. Fields that must NOT go in ZOA API body
        exclude = ['company_id', 'action', 'option', 'token']
        
        # 2. Clean request_json
        # Keep: to, subject, body, body_type, cc, bcc, reply_to, thread_id
        final_data = {k: v for k, v in request_json.items() if k not in exclude and v is not None}

        try:
            # Send POST to specific endpoint
            response = requests.post(self.api_base, headers=self.headers, json=final_data)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500