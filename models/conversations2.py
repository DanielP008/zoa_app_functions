import requests
import concurrent.futures
from models.users import ZoaUser

class ZoaConversation2:
    def __init__(self, token=None, api_base=None):
        import os
        self.token = str(token or os.getenv("TOKEN")).strip()
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": self.token
        }
        self.user_manager = ZoaUser(self.token, api_base)

    def _get_conversation_id(self, request_json):
        conv_id = request_json.get("conversation_id") or request_json.get("id")
        if conv_id:
            return conv_id
        company_id = str(request_json.get("company_id") or "").strip()
        phone = str(request_json.get("phone") or request_json.get("customer_phone") or "").strip().replace("+", "")
        return f"{company_id}_{phone}" 

    def _get_template_id_by_name(self, template_name, company_id):
        if not company_id:
            return None
        url = f"{self.api_base.rstrip('/')}/waba/templates"
        params = {"phone_number_id": str(company_id), "limit": 100}
        try:
            while url:
                response = requests.get(url, headers=self.headers, params=params, timeout=15)
                if response.status_code != 200:
                    break
                res_json = response.json()
                for t in res_json.get("data", []):
                    if str(t.get("name")).strip().lower() == str(template_name).strip().lower():
                        return t.get("id")
                paging = res_json.get("paging", {})
                next_url = paging.get("next")
                after = paging.get("cursors", {}).get("after")
                if next_url:
                    url, params = next_url, {}
                elif after:
                    params["after"] = after
                else:
                    url = None
        except Exception:
            pass
        return None

    def send(self, request_json):
        company_id = request_json.get("company_id") or request_json.get("phone_number_id")
        if not company_id:
            return {"error": "Falta company_id"}, 400

        msg_type = request_json.get("type")
        empty = {}

        if msg_type == "text":
            endpoint = "/waba/messages/send/text"
            conv_id = self._get_conversation_id(request_json)
            if not conv_id:
                phone_raw = str(request_json.get("phone") or "").replace("+", "").strip()
                conv_id = f"{company_id}_{phone_raw}"
            final_payload = {
                "phone_number_id": str(company_id),
                "conversation_id": conv_id,
                "text": request_json.get("text"),
                "image": request_json.get("image") or empty,
                "audio": request_json.get("audio") or empty,
                "video": request_json.get("video") or empty,
                "document": request_json.get("document") or empty,
                "location": request_json.get("location") or empty,
                "sticker": request_json.get("sticker") or empty,
                "context": request_json.get("context") or empty
            }

        elif msg_type == "buttons_text":
            endpoint = "/waba/messages/send/text"
            conv_id = self._get_conversation_id(request_json)
            if not conv_id:
                phone_raw = str(request_json.get("phone") or "").replace("+", "").strip()
                conv_id = f"{company_id}_{phone_raw}"
            btn_texts = [t for t in (str(request_json.get(f"bt{i}") or "").strip() for i in range(1, 4)) if t]
            if not btn_texts:
                final_payload = {"phone_number_id": str(company_id), "conversation_id": conv_id, "type": "text", "text": request_json.get("text")}
            else:
                buttons = [{"type": "reply", "reply": {"id": f"btn_{i+1}", "title": t[:20]}} for i, t in enumerate(btn_texts)]
                final_payload = {
                    "phone_number_id": str(company_id),
                    "conversation_id": conv_id,
                    "type": "interactive",
                    "content": {"type": "button", "body": {"text": request_json.get("text") or "Selecciona una opción:"}, "action": {"buttons": buttons}}
                }

        elif msg_type == "template":
            endpoint = "/waba/messages/send/template"
            template_id = request_json.get("template_id")
            if not template_id:
                template_name = request_json.get("template_name")
                if template_name:
                    template_id = self._get_template_id_by_name(template_name, company_id)
            final_payload = {
                "to": str(request_json.get("to") or request_json.get("phone")).strip(),
                "template_id": str(template_id),
                "data": {
                    "body": request_json.get("body") or request_json.get("data", {}).get("body") or [],
                    "button": request_json.get("button") or [],
                    "header": request_json.get("header") or [],
                    "document_name": request_json.get("document_name"),
                    "header_type": request_json.get("header_type", "")
                },
                "phone_number_id": str(company_id)
            }
        else:
            return {"error": f"Tipo '{msg_type}' no soportado"}, 400

        try:
            url = f"{self.api_base.rstrip('/')}{endpoint}"
            response = requests.post(url, headers=self.headers, json=final_payload, timeout=15)
            return response.json() if response.text else {"status": "ok"}, response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def assign(self, request_json):
        conv_id = request_json.get("conversation_id") or request_json.get("id")
        company_id = request_json.get("company_id")
        if not conv_id:
            return {"error": "No se localizó el ID de la conversación"}, 404

        user_id = request_json.get("manager_id")
        
        if not user_id:
            manager_name = request_json.get("manager_name")
            if not manager_name:
                return {"error": "Se requiere 'manager_id' o 'manager_name'"}, 400
                
            u_res, u_status = self.user_manager.search({"name": manager_name})
            if u_status != 200:
                return {"error": f"No se encontró al usuario {manager_name}"}, 404
            u_data = u_res.get("data")
            user_id = u_data[0].get("id") if isinstance(u_data, list) and u_data else u_data.get("id")

        try:
            response = requests.post(f"{self.api_base}/waba/conversations/{conv_id}/assign", headers=self.headers, json={"user_id": str(user_id)})
            return response.json() if response.text else {"status": "success"}, response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def status(self, request_json):
        conv_id = self._get_conversation_id(request_json)
        company_id = request_json.get("company_id")
        new_status = request_json.get("sales_status")
        if not conv_id:
            return {"error": "No se pudo determinar el conversation_id"}, 404
        try:
            url = f"{self.api_base}/waba/conversations/{conv_id}/sales-status"
            response = requests.patch(url, headers=self.headers, json={"sales_status": new_status})
            if response.status_code in [200, 201, 204]:
                return {"status": "success", "conversation_id": conv_id, "new_status": new_status}, 200
            return response.json() if response.text else {"status": "error"}, response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def assign_status(self, request_json):
        """
        Dual flow: Assign user and change sales status in parallel.
        Uses direct ID to avoid lookup latency.
        """
        # 1. Resolve conversation ID once
        conv_id = self._get_conversation_id(request_json)
        if not conv_id:
            return {"error": "No se pudo determinar el ID de la conversación"}, 400
            
        # Inject ID into JSON so child logic doesn't look it up again
        request_json["conversation_id"] = conv_id
        
        # 2. Execute assignment and status change in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_assign = executor.submit(self.assign, request_json)
            future_status = executor.submit(self.status, request_json)
            
            a_res, a_code = future_assign.result()
            s_res, s_code = future_status.result()

        return {
            "status": "success",
            "conversation_id": conv_id,
            "results": {
                "assign": a_res,
                "status": s_res
            }
        }, 200