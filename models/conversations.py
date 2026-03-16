import os
import requests
import logging
import base64
import concurrent.futures
from models.users import ZoaUser

logger = logging.getLogger(__name__)


class ZoaConversation:
    def __init__(self, token=None, api_base=None):
        self.token = str(token or os.getenv("TOKEN")).strip()
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": self.token
        }
        self.user_manager = ZoaUser(self.token, api_base)

    def search(self, request_json):
        wamid = request_json.get("wamid")
        company_id = request_json.get("company_id")
        if not wamid:
            return {"error": "Se requiere 'wamid'"}, 400
        if not company_id:
            return {"error": "Se requiere 'company_id'"}, 400

        req_headers = {**self.headers, "company_id": str(company_id)}
        try:
            response = requests.get(f"{self.api_base.rstrip('/')}/waba/messages/{wamid}", headers=req_headers, timeout=15)
            if not response.text:
                return {"status": "empty_response"}, response.status_code

            res_data = response.json()
            media_url = res_data.get("media_url")
            if media_url:
                try:
                    media_res = requests.get(media_url, timeout=30)
                    media_res.raise_for_status()
                    res_data["base64"] = base64.b64encode(media_res.content).decode("utf-8")
                except Exception as e:
                    logger.error("[WABA_MSG] Error downloading media: %s", e)
            return res_data, response.status_code
        except requests.exceptions.Timeout:
            return {"error": "Timeout al consultar mensaje WABA"}, 504
        except Exception as e:
            return {"error": str(e)}, 500

    def send(self, request_json):
        company_id = request_json.get("company_id") or request_json.get("phone_number_id") or request_json.get("location_id")
        if not company_id:
            return {"error": "Falta identificador de cuenta (company_id)"}, 400

        msg_type = request_json.get("type")
        if msg_type == "text":
            endpoint, payload = self._build_text_payload(request_json, company_id)
        elif msg_type == "buttons_text":
            endpoint, payload = self._build_buttons_payload(request_json, company_id)
        elif msg_type == "template":
            result = self._build_template_payload(request_json, company_id)
            if isinstance(result, tuple) and isinstance(result[0], dict) and "error" in result[0]:
                return result
            endpoint, payload = result
        else:
            return {"error": f"Tipo de mensaje '{msg_type}' no soportado"}, 400

        try:
            url = f"{self.api_base.rstrip('/')}{endpoint}"
            response = requests.post(url, headers=self.headers, json=payload, timeout=15)
            return response.json() if response.text else {"status": "ok"}, response.status_code
        except Exception as e:
            return {"error": f"Error de red: {str(e)}"}, 500

    def assign(self, request_json):
        conv_id = self._resolve_conv_id(request_json)
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
            response = requests.post(
                f"{self.api_base}/waba/conversations/{conv_id}/assign",
                headers=self.headers, json={"user_id": str(user_id)}
            )
            return response.json() if response.text else {"status": "success"}, response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def status(self, request_json):
        conv_id = self._get_conversation_id(request_json)
        new_status = request_json.get("sales_status")
        company_id = request_json.get("company_id")

        if not conv_id:
            phone = request_json.get("phone") or request_json.get("customer_phone")
            conv_id = self._find_conv_id_by_phone(phone, company_id)
        if not conv_id:
            return {"error": "No se pudo determinar el conversation_id"}, 404

        try:
            url = f"{self.api_base}/waba/conversations/{conv_id}/sales-status"
            response = requests.patch(url, headers=self.headers, json={"sales_status": new_status})
            if response.status_code == 405:
                response = requests.post(url, headers=self.headers, json={"sales_status": new_status})
            if response.status_code in (200, 201, 204):
                return {"status": "success", "conversation_id": conv_id, "new_status": new_status}, 200
            return response.json() if response.text else {"status": "error"}, response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def assign_status(self, request_json):
        conv_id = self._get_conversation_id(request_json)
        if not conv_id:
            return {"error": "No se pudo determinar el ID de la conversación"}, 400
        request_json["conversation_id"] = conv_id

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f_assign = executor.submit(self.assign, request_json)
            f_status = executor.submit(self.status, request_json)
            a_res, a_code = f_assign.result()
            s_res, s_code = f_status.result()

        if a_code not in (200, 201, 204) and s_code not in (200, 201, 204):
            return {"error": "Fallaron ambos procesos", "assign": a_res, "status": s_res}, a_code
        if a_code not in (200, 201, 204):
            return {"status": "partial_success", "message": "Estado cambiado pero falló la asignación", "assign_error": a_res, "status_result": s_res}, a_code
        if s_code not in (200, 201, 204):
            return {"status": "partial_success", "message": "Asignado pero falló el cambio de estado", "assign_result": a_res, "status_error": s_res}, s_code
        return {"status": "success", "conversation_id": conv_id, "results": {"assign": a_res, "status": s_res}}, 200

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_conversation_id(self, request_json):
        conv_id = request_json.get("conversation_id") or request_json.get("id")
        if conv_id:
            return conv_id
        company_id = str(request_json.get("company_id") or "").strip()
        phone = str(request_json.get("phone") or request_json.get("customer_phone") or "").strip().replace("+", "")
        return f"{company_id}_{phone}" if company_id and phone else None

    def _resolve_conv_id(self, request_json):
        conv_id = request_json.get("conversation_id") or request_json.get("id")
        if conv_id:
            return conv_id
        phone = request_json.get("phone") or request_json.get("customer_phone")
        company_id = request_json.get("company_id")
        if phone:
            return self._find_conv_id_by_phone(phone, company_id)
        return None

    def _find_conv_id_by_phone(self, phone, company_id):
        if not phone or not company_id:
            return None
        try:
            res = requests.get(f"{self.api_base}/waba/conversations?phone_number_id={company_id}", headers=self.headers)
            if res.status_code == 200:
                found = next((c for c in res.json().get("items", []) if c.get("customer_phone") == phone), None)
                if found:
                    return found.get("id")
        except Exception:
            pass
        return None

    def _build_text_payload(self, req, company_id):
        conv_id = self._get_conversation_id(req)
        if not conv_id:
            phone_raw = str(req.get("phone") or "").replace("+", "").strip()
            conv_id = f"{company_id}_{phone_raw}"
        empty = {}
        payload = {
            "phone_number_id": str(company_id),
            "conversation_id": conv_id,
            "text": req.get("text"),
            "image": req.get("image") or empty,
            "audio": req.get("audio") or empty,
            "video": req.get("video") or empty,
            "document": req.get("document") or empty,
            "location": req.get("location") or empty,
            "sticker": req.get("sticker") or empty,
            "context": req.get("context") or empty
        }
        return "/waba/messages/send/text", payload

    def _build_buttons_payload(self, req, company_id):
        conv_id = self._get_conversation_id(req)
        if not conv_id:
            phone_raw = str(req.get("phone") or "").replace("+", "").strip()
            conv_id = f"{company_id}_{phone_raw}"
        btn_texts = [t for t in (str(req.get(f"bt{i}") or "").strip() for i in range(1, 4)) if t]
        if not btn_texts:
            return "/waba/messages/send/text", {
                "phone_number_id": str(company_id),
                "conversation_id": conv_id,
                "type": "text",
                "text": req.get("text")
            }
        buttons = [{"type": "reply", "reply": {"id": f"btn_{i+1}", "title": t[:20]}} for i, t in enumerate(btn_texts)]
        return "/waba/messages/send/text", {
            "phone_number_id": str(company_id),
            "conversation_id": conv_id,
            "type": "interactive",
            "content": {
                "type": "button",
                "body": {"text": req.get("text") or "Selecciona una opción:"},
                "action": {"buttons": buttons}
            }
        }

    def _build_template_payload(self, req, company_id):
        template_id = req.get("template_id")
        if not template_id:
            name = req.get("template_name")
            if name:
                template_id = self._get_template_id_by_name(name, company_id)
        if not template_id:
            return {"error": "No se pudo determinar el ID del template (se requiere 'template_id' o 'template_name')"}, 404

        msg_data = {
            "body": req.get("body") or req.get("data", {}).get("body") or [],
            "button": req.get("button") or [],
            "header": req.get("header") or [],
            "document_name": req.get("document_name"),
            "header_type": req.get("header_type", "")
        }
        b64 = req.get("base64")
        if b64:
            msg_data["header_type"] = "IMAGE"
            msg_data["header"] = [{"type": "image", "image": {"link": b64}}]

        return "/waba/messages/send/template", {
            "to": str(req.get("to") or req.get("phone")).strip(),
            "template_id": str(template_id),
            "data": msg_data,
            "phone_number_id": str(company_id)
        }

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
