import requests
from users import ZoaUser

class ZoaConversation:
    def __init__(self, token):
        self.token = str(token).strip()
        self.api_base = "https://dev.api.zoasuite.com/api"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": self.token
        }
        self.user_manager = ZoaUser(token)

    def _get_template_id_by_name(self, template_name, company_id):
        """Busca el ID del template."""
        if not company_id:
            return None
        url = f"{self.api_base}/waba/templates?phone_number_id={company_id}"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                res_json = response.json()
                templates = res_json.get("data", [])
                for t in templates:
                    if t.get("name") == template_name:
                        return t.get("id")
            return None
        except Exception:
            return None
        
    def _get_conversation_id(self, request_json):
        """Genera el ID exacto: {company_id}_{phone_sin_mas}"""
        conv_id = request_json.get("conversation_id") or request_json.get("id")
        if conv_id:
            return conv_id
        
        company_id = str(request_json.get("company_id") or "").strip()
        # Limpiamos el teléfono de '+' y espacios
        phone = str(request_json.get("phone") or request_json.get("customer_phone") or "").strip().replace("+", "")
        
        if company_id and phone:
            return f"{company_id}_{phone}"
        return None

    def send(self, request_json):
        """Orquesta el envío de mensajes transformando el request al formato final de ZOA."""
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
            final_payload = {
                "phone_number_id": str(company_id),
                "conversation_id": request_json.get("conversation_id") or request_json.get("conv_id"),
                "text": request_json.get("text"),
                "image": request_json.get("image") or empty_obj,
                "audio": request_json.get("audio") or empty_obj,
                "video": request_json.get("video") or empty_obj,
                "document": request_json.get("document") or empty_obj,
                "location": request_json.get("location") or empty_obj,
                "sticker": request_json.get("sticker") or empty_obj,
                "context": request_json.get("context") or empty_obj
            }
            if not final_payload["conversation_id"]:
                final_payload["to"] = request_json.get("to") or request_json.get("phone")
                del final_payload["conversation_id"]

        # --- CASO BOTONES ---
        elif msg_type == "buttons_text":
            endpoint = "/waba/messages/send/text"
            
            # Recogemos los botones individuales que envía n8n
            # Usamos .get() y .strip() para evitar errores si vienen vacíos
            b1 = str(request_json.get("bt1") or "").strip()
            b2 = str(request_json.get("bt2") or "").strip()
            b3 = str(request_json.get("bt3") or "").strip()
            
            # Creamos la lista solo con los que no estén vacíos
            btn_list = [b for b in [b1, b2, b3] if b]

            # Mapeamos al formato interactivo de Meta
            formatted_buttons = []
            for i, btn_text in enumerate(btn_list):
                formatted_buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"btn_{i+1}", 
                        "title": btn_text[:20] # WhatsApp corta a los 20 caracteres
                    }
                })

            final_payload = {
                "phone_number_id": str(company_id),
                "conversation_id": request_json.get("conversation_id") or request_json.get("conv_id"),
                "message_type": "interactive",
                "content": {
                    "type": "button",
                    "header": {"type": "text", "text": "Opciones"},
                    # n8n envía el texto en el parámetro 'message' según tu URL
                    "body": {"text": request_json.get("message") or request_json.get("text") or "Selecciona:"},
                    "action": {"buttons": formatted_buttons}
                }
            }

            if not final_payload["conversation_id"]:
                final_payload["to"] = request_json.get("phone")
                del final_payload["conversation_id"]

        # --- CASO TEMPLATE ---
        elif msg_type == "template":
            endpoint = "/waba/messages/send/template"
            template_name = request_json.get("template_name")
            template_id = self._get_template_id_by_name(template_name, company_id)
            
            if not template_id:
                return {"error": f"Template '{template_name}' no encontrado"}, 404

            # Preparamos la data base
            msg_data = request_json.get("data") or {
                "body": request_json.get("body") or [],
                "button": request_json.get("button") or [],
                "header": request_json.get("header") or [],
                "document_name": request_json.get("document_name"),
                "header_type": request_json.get("header_type", "")
            }

            # LÓGICA PARA BASE64: Si n8n envía "base64", lo metemos en el header
            b64_data = request_json.get("base64")
            if b64_data:
                # Aseguramos que el header_type sea IMAGE
                msg_data["header_type"] = "IMAGE"
                # El formato de ZOA para base64 en templates suele requerir el objeto dentro de header
                msg_data["header"] = [{
                    "type": "image",
                    "image": {
                        "link": b64_data  # ZOA acepta el string base64 aquí
                    }
                }]

            final_payload = {
                "to": request_json.get("to") or request_json.get("phone"),
                "template_id": str(template_id),
                "data": msg_data,
                "phone_number_id": str(company_id)
            }

        # --- EJECUCIÓN DE LA PETICIÓN ---
        try:
            url_post = f"{self.api_base}{endpoint}"
            response = requests.post(url_post, headers=self.headers, json=final_payload)
            
            if response.status_code == 422:
                print(f"ERROR 422 DETALLE ZOA: {response.text}")

            try:
                return response.json(), response.status_code
            except Exception:
                return {"status": "processed", "code": response.status_code}, response.status_code

        except Exception as e:
            return {"error": f"Error de red: {str(e)}"}, 500

    def assign(self, request_json):
        """TU FUNCIÓN ORIGINAL (Sin cambios)"""
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
        Actualiza el sales_status. 
        Ahora utiliza la construcción directa de ID que te funcionó en el script.
        """
        # 1. Intentamos construir el ID directamente como en tu Direct Call
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

        # 3. Petición al endpoint (Priorizando PATCH que es el que te funcionó)
        try:
            url_status = f"{self.api_base}/waba/conversations/{conv_id}/sales-status"
            payload = {"sales_status": new_status}
            
            print(f"DEBUG: Enviando PATCH a {url_status}")
            
            # Usamos PATCH directamente ya que confirmaste que funciona
            response = requests.patch(url_status, headers=self.headers, json=payload)
            
            # Si PATCH no existe en algún caso, fallback a POST
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
        Orquestación dual: Asigna un usuario y cambia el estado de venta.
        Utiliza el ID directo para evitar latencias de búsqueda.
        """
        # 1. Aseguramos el ID de la conversación una sola vez
        conv_id = self._get_conversation_id(request_json)
        if not conv_id:
            return {"error": "No se pudo determinar el ID de la conversación"}, 400
            
        # Inyectamos el ID en el JSON para que las funciones hijas no lo busquen
        request_json["conversation_id"] = conv_id
        
        print(f"DEBUG: Iniciando proceso dual para {conv_id}")

        # 2. Ejecutar Asignación
        # Si manager_name es "", la función assign ya gestiona el user_id: null
        a_res, a_code = self.assign(request_json)
        
        # Si falla la asignación (y no es un error de "ya asignado"), paramos
        if a_code not in [200, 201, 204]:
            return {"error": "Falló la asignación", "details": a_res}, a_code

        # 3. Ejecutar Cambio de Estado
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