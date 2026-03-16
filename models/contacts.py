import os
import requests
import logging
from urllib.parse import quote
from models.users import ZoaUser

logger = logging.getLogger(__name__)


class ZoaContact:
    def __init__(self, token=None, api_base=None):
        self.token = token or os.getenv("TOKEN")
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": self.token
        }
        self.user_manager = ZoaUser(self.token, api_base)

    def search(self, request_json):
        phone = request_json.get("phone") or request_json.get("mobile")
        nif = request_json.get("nif")
        email = request_json.get("email")
        name = request_json.get("name")
        base = f"{self.api_base}/pipelines/contacts"

        if phone and str(phone).strip():
            return self._search_by_phone(base, phone)
        elif nif and str(nif).strip():
            url = f"{base}/nif/{nif.strip()}"
        elif email and str(email).strip():
            url = f"{base}/email/{email.strip()}"
        elif name and str(name).strip():
            url = f"{base}/name/{quote(name.strip())}"
        else:
            return {"error": "Falta criterio de búsqueda (phone, mobile, nif, email o name)"}, 400

        try:
            response = requests.get(url, headers=self.headers)
            data = response.json()
            if response.status_code == 200 and data.get("success"):
                self._enrich_with_manager_name(data)
            return data, response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def create(self, request_json):
        manager_name = request_json.get("manager_name")
        resolved_manager_id = None
        resolved_office_ids = []

        if manager_name:
            u_res, u_status = self.user_manager.search({"name": manager_name})
            if u_status == 200:
                user_obj = self._extract_first(u_res)
                if user_obj:
                    resolved_manager_id = user_obj.get("id")
                    office = user_obj.get("office_default")
                    resolved_office_ids = [office] if office else []

        payload = {
            "name": request_json.get("name", ""),
            "email": request_json.get("email", ""),
            "email2": request_json.get("email2", ""),
            "nif": request_json.get("nif", ""),
            "mobile": request_json.get("mobile") or request_json.get("phone", ""),
            "contact_type": request_json.get("contact_type", "particular"),
            "gender": request_json.get("gender", "Hombre"),
            "office_ids": request_json.get("office_ids") or resolved_office_ids,
            "manager_id": resolved_manager_id
        }
        try:
            response = requests.post(f"{self.api_base}/pipelines/contacts", headers=self.headers, json=payload)
            try:
                return response.json(), response.status_code
            except Exception:
                return {"status": "processed", "code": response.status_code}, response.status_code
        except Exception as e:
            return {"error": f"Fallo de conexión: {str(e)}"}, 500

    def update(self, request_json):
        contact_id = request_json.get("contact_id")
        if not contact_id:
            # Intentar búsqueda con los datos originales (pueden traer prefijo o no)
            c_res, _ = self.search(request_json)
            contact_id = self._extract_id(c_res)
            
            # Si no se encuentra y hay un nombre, intentar por nombre
            if not contact_id and request_json.get("name"):
                c_res, _ = self.search({"name": request_json["name"]})
                contact_id = self._extract_id(c_res)

        if not contact_id:
            return {"error": "No se localizó el contacto por ningún criterio"}, 404

        manager_id = None
        m_name = request_json.get("manager_name") or request_json.get("new_manager_name")
        if m_name:
            u_res, u_status = self.user_manager.search({"name": m_name})
            if u_status == 200:
                manager_id = self._extract_id(u_res)

        patch_data = {
            "name": request_json.get("new_name") or request_json.get("name"),
            "mobile": request_json.get("new_phone") or request_json.get("phone") or request_json.get("mobile"),
            "email": request_json.get("email"),
            "nif": request_json.get("nif"),
            "gender": request_json.get("gender"),
            "manager_id": manager_id
        }
        # Solo enviamos campos que tengan valor y no sean strings vacíos
        clean = {k: v for k, v in patch_data.items() if v is not None and str(v).strip() != ""}
        
        # Log para depuración en Cloud Run
        logger.info(f"[DEBUG] PATCH Contact {contact_id}: {clean}")
        
        try:
            response = requests.patch(f"{self.api_base}/pipelines/contacts/{contact_id}", headers=self.headers, json=clean)
            if response.status_code != 200:
                logger.error(f"[ERROR] ZOA API Response: {response.text}")
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_id(res):
        if not isinstance(res, dict):
            return None
        data = res.get("data", [])
        if isinstance(data, list) and data:
            return data[0].get("id")
        if isinstance(data, dict):
            return data.get("id")
        return None

    @staticmethod
    def _extract_first(res):
        if not isinstance(res, dict):
            return None
        data = res.get("data", res)
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict):
            return data
        return None

    def _search_by_phone(self, base, phone):
        raw = str(phone).strip().replace(" ", "")
        # Try 1: With '+' prefix
        clean_plus = raw if raw.startswith("+") else "+" + raw
        try:
            response = requests.get(f"{base}/mobile/{clean_plus}", headers=self.headers)
            data = response.json()
            if response.status_code == 200 and data.get("success"):
                self._enrich_with_manager_name(data)
                return data, 200

            # Try 2: Without '+' prefix
            raw_no_plus = raw.replace("+", "")
            resp2 = requests.get(f"{base}/mobile/{raw_no_plus}", headers=self.headers)
            data2 = resp2.json()
            if resp2.status_code == 200 and data2.get("success"):
                self._enrich_with_manager_name(data2)
                return data2, 200

            # Try 3: If it had a prefix (like +34), try without the prefix (last 9 digits)
            if len(raw_no_plus) > 9:
                last_9 = raw_no_plus[-9:]
                resp3 = requests.get(f"{base}/mobile/{last_9}", headers=self.headers)
                data3 = resp3.json()
                if resp3.status_code == 200 and data3.get("success"):
                    self._enrich_with_manager_name(data3)
                    return data3, 200

            return data, response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def _enrich_with_manager_name(self, data):
        contact_data = data.get("data")
        contacts = contact_data if isinstance(contact_data, list) else [contact_data] if isinstance(contact_data, dict) else []
        for contact in contacts:
            manager_id = contact.get("manager_id")
            if not manager_id:
                continue
            u_res, u_status = self.user_manager.search({"id": manager_id})
            if u_status == 200 and u_res.get("success"):
                user = self._extract_first(u_res)
                if user:
                    contact["manager_name"] = user.get("name")
