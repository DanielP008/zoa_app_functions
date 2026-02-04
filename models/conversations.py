import requests
from models.users import ZoaUser

class ZoaConversation:
    def __init__(self, token=None, api_base=None):
        import os
        # Use env vars directly (Global configuration)
        self.token = str(token or os.getenv("TOKEN")).strip()
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": self.token
        }
        self.user_manager = ZoaUser(self.token, api_base)

    def _get_template_id_by_name(self, template_name, company_id):
        """Finds the template ID by iterating through all API pages."""
        if not company_id:
            return None
        
        base = self.api_base.rstrip('/')
        url = f"{base}/waba/templates"
        
        # Initial params; limit 100 to reduce pagination hops.
        params = {
            "phone_number_id": str(company_id),
            "limit": 100 
        }
        
        try:
            while url:
                print(f"DEBUG: Consultando página de templates en {url}")
                response = requests.get(url, headers=self.headers, params=params, timeout=15)
                
                if response.status_code != 200:
                    print(f"DEBUG: Error API ZOA ({response.status_code}): {response.text}")
                    break

                res_json = response.json()
                templates = res_json.get("data", [])
                
                # Search current page
                for t in templates:
                    if str(t.get("name")).strip().lower() == str(template_name).strip().lower():
                        t_id = t.get("id")
                        print(f"DEBUG: ¡Template encontrado en esta página! ID: {t_id}")
                        return t_id
                
                # --- LÓGICA DE PAGINACIÓN ---
                # Revisamos si hay una siguiente página según la estructura de Meta/ZOA
                paging = res_json.get("paging", {})
                next_page_url = paging.get("next")  # Sometimes full URL
                cursors = paging.get("cursors", {})
                after_token = cursors.get("after")

                if next_page_url:
                    url = next_page_url
                    params = {}  # Params are usually already in the 'next' URL
                elif after_token:
                    # If only 'after' token is given, add to params
                    params["after"] = after_token
                else:
                    # No more pages
                    url = None

            print(f"DEBUG: Se recorrieron todas las páginas y no se encontró '{template_name}'")
            return None

        except Exception as e:
            print(f"DEBUG: Error grave en búsqueda paginada: {str(e)}")
            return None
    def _get_conversation_id(self, request_json):
        """Genera el ID exacto: {company_id}_{phone_sin_mas}"""
        conv_id = request_json.get("conversation_id") or request_json.get("id")
        if conv_id:
            return conv_id
        
        company_id = str(request_json.get("company_id") or "").strip()
        # Strip phone of '+' and spaces
        phone = str(request_json.get("phone") or request_json.get("customer_phone") or "").strip().replace("+", "")
        
        if company_id and phone:
            return f"{company_id}_{phone}"
        return None

    def send(self, request_json):
        """Orchestrates message sending, transforming the request to ZOA's final format."""
        company_id = (
            request_json.get("company_id") or 
            request_json.get("phone_number_id") or 
            request_json.get("location_id")
        )
        
        if not company_id:
            return {"error": "Falta identificador de cuenta (company_id)"}, 400

        msg_type = request_json.get("type")
        empty_obj = {}

        # --- CASO TEXTO ---
        if msg_type == "text":
            endpoint = "/waba/messages/send/text"
            
            # 1. Try to get ID in every possible way
            conv_id = self._get_conversation_id(request_json)
            
            final_payload = {
                "phone_number_id": str(company_id),
                "conversation_id": conv_id, 
                "text": request_json.get("text"),
                "image": request_json.get("image") or empty_obj,
                "audio": request_json.get("audio") or empty_obj,
                "video": request_json.get("video") or empty_obj,
                "document": request_json.get("document") or empty_obj,
                "location": request_json.get("location") or empty_obj,
                "sticker": request_json.get("sticker") or empty_obj,
                "context": request_json.get("context") or empty_obj
            }

            # Si el conv_id sigue vacío, ZOA dará error, 
            # así que como último recurso lo armamos manual aquí
            if not final_payload["conversation_id"]:
                phone_raw = str(request_json.get("phone") or "").replace("+", "").strip()
                final_payload["conversation_id"] = f"{company_id}_{phone_raw}"

        # --- CASO BOTONES ---
        elif msg_type == "buttons_text":
            endpoint = "/waba/messages/send/text"
            
            conv_id = self._get_conversation_id(request_json)
            if not conv_id:
                phone_raw = str(request_json.get("phone") or "").replace("+", "").strip()
                conv_id = f"{company_id}_{phone_raw}"

            # 1. Filter buttons that have text
            btn_texts = [str(request_json.get(f"bt{i}") or "").strip() for i in range(1, 4)]
            btn_texts = [t for t in btn_texts if t]

            # 2. Si no hay botones, fallback a texto simple
            if not btn_texts:
                final_payload = {
                    "phone_number_id": str(company_id),
                    "conversation_id": conv_id,
                    "type": "text",
                    "text": request_json.get("text")
                }
            else:
                # 3. Build INTERACTIVE object per Meta standard
                formatted_buttons = []
                for i, text in enumerate(btn_texts):
                    formatted_buttons.append({
                        "type": "reply",
                        "reply": {
                            "id": f"btn_{i+1}",
                            "title": text[:20]  # WhatsApp limit
                        }
                    })

                final_payload = {
                    "phone_number_id": str(company_id),
                    "conversation_id": conv_id,
                    "type": "interactive",  # Use 'interactive', not 'buttons_text'
                    "content": {
                        "type": "button",
                        "body": {"text": request_json.get("text") or "Selecciona una opción:"},
                        "action": {"buttons": formatted_buttons}
                    }
                }

        # --- CASO TEMPLATE ---
        elif msg_type == "template":
            endpoint = "/waba/messages/send/template"
            
            # Priority 1: Use direct ID if in JSON
            template_id = request_json.get("template_id")
            
            # Priority 2: If no ID, search by name
            if not template_id:
                template_name = request_json.get("template_name")
                template_id = self._get_template_id_by_name(template_name, company_id)
            
            if not template_id:
                return {"error": f"No se pudo determinar el ID del template (nombre: {request_json.get('template_name')})"}, 404

            # Construir data simplificada para evitar errores 502/422 en producción
            msg_data = {
                "body": request_json.get("body") or request_json.get("data", {}).get("body") or [],
                "button": request_json.get("button") or [],
                "header": request_json.get("header") or [],
                "document_name": request_json.get("document_name"),
                "header_type": request_json.get("header_type", "")
            }

            # Base64 logic
            b64_data = request_json.get("base64")
            if b64_data:
                msg_data["header_type"] = "IMAGE"
                msg_data["header"] = [{
                    "type": "image",
                    "image": {"link": b64_data}
                }]

            final_payload = {
                "to": str(request_json.get("to") or request_json.get("phone")).strip(),
                "template_id": str(template_id),
                "data": msg_data,
                "phone_number_id": str(company_id)
            }

        else:
            return {"error": f"Tipo de mensaje '{msg_type}' no soportado"}, 400

        # --- EXECUTION ---
        try:
            # Avoid double slashes in URL
            base_url = self.api_base.rstrip('/')
            url_post = f"{base_url}{endpoint}"
            
            print(f"DEBUG: Enviando POST a {url_post}")
            response = requests.post(url_post, headers=self.headers, json=final_payload, timeout=15)
            
            if response.status_code == 422:
                print(f"ERROR 422 ZOA: {response.text}")

            return response.json() if response.text else {"status": "ok"}, response.status_code

        except Exception as e:
            return {"error": f"Error de red en Flow: {str(e)}"}, 500

    def assign(self, request_json):
        """Assigns a conversation to a user."""
        conv_id = request_json.get("conversation_id") or request_json.get("id")
        customer_phone = request_json.get("phone") or request_json.get("customer_phone")
        company_id = request_json.get("company_id")
        
        if not conv_id and customer_phone:
            url_list = f"{self.api_base}/waba/conversations?phone_number_id={company_id}"
            res = requests.get(url_list, headers=self.headers)
            if res.status_code == 200:
                items = res.json().get("items", [])
                found = next((c for c in items if c.get("customer_phone") == customer_phone), None)
                if found: conv_id = found.get("id")

        if not conv_id:
            return {"error": "No se localizó el ID de la conversación"}, 404

        manager_name = request_json.get("manager_name")
        u_res, u_status = self.user_manager.search({"name": manager_name})
        if u_status != 200: return {"error": f"No se encontró al usuario {manager_name}"}, 404
        
        u_data = u_res.get("data")
        resolved_user_id = u_data[0].get("id") if isinstance(u_data, list) and u_data else u_data.get("id")
        
        try:
            url_assign = f"{self.api_base}/waba/conversations/{conv_id}/assign"
            payload = {"user_id": str(resolved_user_id)}
            response = requests.post(url_assign, headers=self.headers, json=payload)
            return response.json() if response.text else {"status": "success"}, response.status_code
        except Exception as e: return {"error": str(e)}, 500

    def status(self, request_json):
        """
        Updates sales_status.
        Uses direct ID construction that works in the script.
        """
        # 1. Try to build ID directly
        conv_id = self._get_conversation_id(request_json)
        customer_phone = request_json.get("phone") or request_json.get("customer_phone")
        company_id = request_json.get("company_id")
        new_status = request_json.get("sales_status")

        # 2. Backup: Si no hay forma de armar el ID, buscarlo (tu lógica original)
        if not conv_id and customer_phone:
            url_list = f"{self.api_base}/waba/conversations?phone_number_id={company_id}"
            res = requests.get(url_list, headers=self.headers)
            if res.status_code == 200:
                items = res.json().get("items", [])
                found = next((c for c in items if c.get("customer_phone") == customer_phone), None)
                if found:
                    conv_id = found.get("id")

        if not conv_id:
            return {"error": "No se pudo determinar el conversation_id"}, 404

        # 3. Request to endpoint (PATCH preferred)
        try:
            url_status = f"{self.api_base}/waba/conversations/{conv_id}/sales-status"
            payload = {"sales_status": new_status}
            
            print(f"DEBUG: Enviando PATCH a {url_status}")
            
            # Usamos PATCH directamente ya que confirmaste que funciona
            response = requests.patch(url_status, headers=self.headers, json=payload)
            
            # If PATCH not available, fallback to POST
            if response.status_code == 405:
                response = requests.post(url_status, headers=self.headers, json=payload)

            if response.status_code in [200, 201, 204]:
                return {
                    "status": "success", 
                    "conversation_id": conv_id, 
                    "new_status": new_status
                }, 200
            
            return response.json() if response.text else {"status": "error"}, response.status_code

        except Exception as e:
            return {"error": str(e)}, 500
        
    def assign_status(self, request_json):
        """
        Dual flow: Assign user and change sales status.
        Uses direct ID to avoid lookup latency.
        """
        # 1. Resolve conversation ID once
        conv_id = self._get_conversation_id(request_json)
        if not conv_id:
            return {"error": "No se pudo determinar el ID de la conversación"}, 400
            
        # Inject ID into JSON so child logic doesn't look it up again
        request_json["conversation_id"] = conv_id
        
        print(f"DEBUG: Iniciando proceso dual para {conv_id}")

        # 2. Execute assignment
        # If manager_name is "", assign already handles user_id: null
        a_res, a_code = self.assign(request_json)
        
        # If assignment fails (and it's not "already assigned"), stop
        if a_code not in [200, 201, 204]:
            return {"error": "Falló la asignación", "details": a_res}, a_code

        # 3. Execute status change
        s_res, s_code = self.status(request_json)
        
        if s_code not in [200, 201, 204]:
            return {
                "status": "partial_success",
                "message": "Asignado correctamente pero falló el cambio de estado",
                "assign_result": a_res,
                "status_error": s_res
            }, s_code

        return {
            "status": "success",
            "conversation_id": conv_id,
            "results": {
                "assign": a_res,
                "status": s_res
            }
        }, 200