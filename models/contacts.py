import requests
from models.users import ZoaUser

class ZoaContact:
    def __init__(self, token=None, api_base=None):
        from config import API_BASE, TOKEN
        self.token = token or TOKEN
        self.api_base = api_base or API_BASE
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": f"{self.token}"
        }
        self.user_manager = ZoaUser(self.token)
        

    def _enrich_with_manager_name(self, data):
        """
        Helper to add manager_name to the contact response.
        Compatible with paginated structure: {success, data: [...], total, page, page_size, total_pages}
        """
        if not isinstance(data, dict):
            return data
            
        # Extract contact object or list of contacts
        # Paginated structure keeps 'data' as list or object
        contact_data = data.get("data")
        
        # If it's a list, iterate over all contacts (may be paginated)
        if isinstance(contact_data, list):
            for contact in contact_data:
                self._add_manager_name_to_contact(contact)
        elif isinstance(contact_data, dict):
            # Single contact as object
            self._add_manager_name_to_contact(contact_data)
            
        return data

    def _add_manager_name_to_contact(self, contact):
        """Adds manager_name to a single contact object if it has manager_id."""
        manager_id = contact.get("manager_id")
        if manager_id:
            # Look up user by ID
            u_res, u_status = self.user_manager.search({"id": manager_id})
            if u_status == 200 and u_res.get("success"):
                user_data = u_res.get("data")
                # user_data should be the user object already filtered by id in models/users.py
                if isinstance(user_data, dict):
                    contact["manager_name"] = user_data.get("name")
                elif isinstance(user_data, list) and len(user_data) > 0:
                     contact["manager_name"] = user_data[0].get("name")

    def search(self, request_json):
        # Try to get phone from both possible keys
        phone = request_json.get("phone") or request_json.get("mobile")
        nif = request_json.get("nif")
        email = request_json.get("email")
        name = request_json.get("name")

        search_path = f"{self.api_base}/pipelines/contacts"
        
        if phone and str(phone).strip():
            # Normalize phone number
            raw_phone = str(phone).strip().replace(" ", "")
            # Try first WITH '+'
            clean_phone_plus = raw_phone if raw_phone.startswith("+") else "+" + raw_phone
            url = f"{search_path}/mobile/{clean_phone_plus}"
            
            try:
                print(f"DEBUG: Buscando contacto (con +) en {url}")
                response = requests.get(url, headers=self.headers)
                data = response.json()
                
                # If found, return result immediately
                if response.status_code == 200 and data.get("success") is True:
                    self._enrich_with_manager_name(data)
                    return data, 200
                
                # If not found with +, try WITHOUT + (only if it didn't have it originally)
                if not raw_phone.startswith("+"):
                    clean_phone_no_plus = raw_phone
                    url_no_plus = f"{search_path}/mobile/{clean_phone_no_plus}"
                    print(f"DEBUG: Falló con +. Probando sin + en {url_no_plus}")
                    response_no_plus = requests.get(url_no_plus, headers=self.headers)
                    data_no_plus = response_no_plus.json()
                    
                    if response_no_plus.status_code == 200 and data_no_plus.get("success") is True:
                         self._enrich_with_manager_name(data_no_plus)

                    return data_no_plus, response_no_plus.status_code
                
                return data, response.status_code
            except Exception as e:
                return {"error": str(e)}, 500

        elif nif and str(nif).strip():
            url = f"{search_path}/nif/{nif.strip()}"
        elif email and str(email).strip():
            url = f"{search_path}/email/{email.strip()}"
        elif name and str(name).strip():
            from urllib.parse import quote
            url = f"{search_path}/name/{quote(name.strip())}"
        else:
            return {"error": "Falta criterio de búsqueda (phone, mobile, nif, email o name)"}, 400

        try:
            print(f"DEBUG: Buscando contacto en {url}")
            response = requests.get(url, headers=self.headers)
            data = response.json()
            if response.status_code == 200 and data.get("success") is True:
                self._enrich_with_manager_name(data)
            return data, response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def create(self, request_json):
        """
        Creates a contact, first resolving the manager ID by name.
        """
        manager_name = request_json.get("manager_name")
        resolved_manager_id = None
        print("entro aqui")

        if manager_name:
            print(f"DEBUG: Intentando buscar manager: {manager_name}")
            u_res, u_status = self.user_manager.search({"name": manager_name})
            print(f"DEBUG: Status búsqueda: {u_status} | Respuesta: {u_res}")
            
            if u_status == 200:
                if isinstance(u_res, list) and len(u_res) > 0:
                    resolved_manager_id = u_res[0].get("id")
                elif isinstance(u_res, dict):
                    # ZOA sometimes returns the object under a 'data' key
                    resolved_manager_id = u_res.get("id") or u_res.get("data", {}).get("id")
            else:
                print(f"DEBUG: No se pudo encontrar el manager. Error: {u_res}")

        # 2. Build final payload for ZOA
        data = {
            "name": request_json.get("name", ""),
            "email": request_json.get("email", ""),
            "email2": request_json.get("email2", ""),
            "nif": request_json.get("nif", ""),
            "mobile": request_json.get("mobile") or request_json.get("phone", ""),
            "contact_type": request_json.get("contact_type", "particular"),
            "gender": request_json.get("gender", ""),
            "office_ids": request_json.get("office_ids", []),
            "manager_id": resolved_manager_id  # Resolved manager ID
        }
        print(data)

        # 3. Final request to ZOA
        try:
            url_zoa = f"{self.api_base}/pipelines/contacts" 
            response = requests.post(url_zoa, headers=self.headers, json=data)
            
            try:
                return response.json(), response.status_code
            except:
                return {"status": "processed", "code": response.status_code}, response.status_code

        except Exception as e:
            return {"error": f"Fallo de conexión: {str(e)}"}, 500
            
    def update(self, request_json):
        """Updates a contact. Supports lookup by name to change phone and vice versa."""
        contact_id = request_json.get("contact_id")
        
        # 1. FLEXIBLE LOOKUP
        if not contact_id:
            # Try first by unique identifiers (phone, email, nif)
            c_res, c_status = self.search(request_json)
            
            # Internal helper to extract ID from ZOA response
            # Compatible with paginated structure: {success, data: [...], total, page, ...}
            def extract_id(res):
                if not isinstance(res, dict): return None
                data_content = res.get("data", [])
                # If data is a list (may be paginated), take first element
                if isinstance(data_content, list) and len(data_content) > 0:
                    return data_content[0].get("id")
                # If data is a direct object (single contact)
                if isinstance(data_content, dict):
                    return data_content.get("id")
                return None

            contact_id = extract_id(c_res)

            # FALLBACK: If not found by phone, search by NAME
            if not contact_id and request_json.get("name"):
                name_to_search = request_json.get("name")
                print(f"DEBUG: Not found by phone. Fallback search by name: {name_to_search}")
                
                # Call search with name only
                c_res_name, c_status_name = self.search({"name": name_to_search})
                contact_id = extract_id(c_res_name)
                
                if contact_id:
                    print(f"DEBUG: Encontrado por nombre! ID: {contact_id}")

        if not contact_id:
            return {"error": "No se localizó el contacto por ningún criterio (teléfono/nombre)"}, 404

        # 2. RESOLVE MANAGER (optional)
        manager_id = None
        m_name = request_json.get("manager_name") or request_json.get("new_manager_name")
        if m_name:
            u_res, u_status = self.user_manager.search({"name": m_name})
            if u_status == 200 and isinstance(u_res, dict):
                u_data = u_res.get("data", [])
                # Compatible with paginated structure: may be list or object
                if isinstance(u_data, list) and len(u_data) > 0:
                    manager_id = u_data[0].get("id")
                elif isinstance(u_data, dict):
                    manager_id = u_data.get("id")

        # 3. UPDATE PAYLOAD
        # If we filtered by name, request 'phone' is the NEW value.
        # If we filtered by phone, request 'name' is the NEW value.
        patch_data = {
            "name": request_json.get("new_name") or request_json.get("name"),
            "mobile": request_json.get("new_phone") or request_json.get("phone") or request_json.get("mobile"),
            "email": request_json.get("email"),
            "nif": request_json.get("nif"),
            "gender": request_json.get("gender"),
            "manager_id": manager_id
        }

        clean_patch = {k: v for k, v in patch_data.items() if v is not None and v != ""}

        # 4. PATCH request
        try:
            url_zoa = f"{self.api_base}/pipelines/contacts/{contact_id}"
            print(f"DEBUG: Realizando PATCH a {url_zoa} con data: {clean_patch}")
            response = requests.patch(url_zoa, headers=self.headers, json=clean_patch)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500