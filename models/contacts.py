import requests
from models.users import ZoaUser

class ZoaContact:
    def __init__(self, token):
        from config import API_BASE
        self.token = token
        self.api_base = API_BASE
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": f"{self.token}"
        }
        self.user_manager = ZoaUser(token)
        

    def search(self, request_json):
        # Intentamos obtener el teléfono de ambas llaves posibles
        phone = request_json.get("phone") or request_json.get("mobile")
        nif = request_json.get("nif")
        email = request_json.get("email")
        name = request_json.get("name")

        search_path = f"{self.api_base}/pipelines/contacts"
        
        if phone and str(phone).strip():
            # Limpiamos el teléfono
            raw_phone = str(phone).strip().replace(" ", "")
            # Intentamos primero CON el '+'
            clean_phone_plus = raw_phone if raw_phone.startswith("+") else "+" + raw_phone
            url = f"{search_path}/mobile/{clean_phone_plus}"
            
            try:
                print(f"DEBUG: Buscando contacto (con +) en {url}")
                response = requests.get(url, headers=self.headers)
                data = response.json()
                
                # Si lo encuentra, devolvemos el resultado inmediatamente
                if response.status_code == 200 and data.get("success") is True:
                    return data, 200
                
                # Si no lo encuentra con +, probamos SIN el + (solo si no lo tenía originalmente)
                if not raw_phone.startswith("+"):
                    clean_phone_no_plus = raw_phone
                    url_no_plus = f"{search_path}/mobile/{clean_phone_no_plus}"
                    print(f"DEBUG: Falló con +. Probando sin + en {url_no_plus}")
                    response_no_plus = requests.get(url_no_plus, headers=self.headers)
                    data_no_plus = response_no_plus.json()
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
            return data, response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def create(self, request_json):
        """
        Crea un contacto resolviendo primero el ID del manager por su nombre.
        """
        # Dentro de ZoaContact.create:
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
                    # Ojo: ZOA a veces devuelve el objeto dentro de una llave 'data'
                    resolved_manager_id = u_res.get("id") or u_res.get("data", {}).get("id")
            else:
                print(f"DEBUG: No se pudo encontrar el manager. Error: {u_res}")

        # 2. Construcción del payload final para ZOA
        data = {
            "name": request_json.get("name", ""),
            "email": request_json.get("email", ""),
            "email2": request_json.get("email2", ""),
            "nif": request_json.get("nif", ""),
            "mobile": request_json.get("mobile") or request_json.get("phone", ""),
            "contact_type": request_json.get("contact_type", "particular"),
            "gender": request_json.get("gender", ""),
            "office_ids": request_json.get("office_ids", []),
            "manager_id": resolved_manager_id  # <--- Aquí insertamos el ID resuelto
        }
        print(data)

        # 3. Petición final a ZOA
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
        """Actualiza un contacto. Soporta buscar por Nombre para cambiar Teléfono y viceversa."""
        contact_id = request_json.get("contact_id")
        
        # 1. BÚSQUEDA FLEXIBLE
        if not contact_id:
            # Intentamos primero por los identificadores únicos (phone, email, nif)
            c_res, c_status = self.search(request_json)
            
            # Función auxiliar interna para extraer ID de la respuesta de ZOA
            # Utiliza una función interna llamada extract_id para navegar en la respuesta de la API de ZOA (que suele venir envuelta en una llave llamada data) y sacar el UUID del contacto
            def extract_id(res):
                if not isinstance(res, dict): return None
                data = res.get("data", [])
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("id")
                if isinstance(data, dict):
                    return data.get("id")
                return None

            contact_id = extract_id(c_res)

            # FALLBACK: Si no se encontró por teléfono, buscamos por NOMBRE
            if not contact_id and request_json.get("name"):
                name_to_search = request_json.get("name")
                print(f"DEBUG: No encontrado por teléfono. Buscando fallback por nombre: {name_to_search}")
                
                # Llamamos a search pasando solo el nombre
                c_res_name, c_status_name = self.search({"name": name_to_search})
                contact_id = extract_id(c_res_name)
                
                if contact_id:
                    print(f"DEBUG: Encontrado por nombre! ID: {contact_id}")

        if not contact_id:
            return {"error": "No se localizó el contacto por ningún criterio (teléfono/nombre)"}, 404

        # 2. RESOLVER MANAGER (Opcional)
        manager_id = None
        m_name = request_json.get("manager_name") or request_json.get("new_manager_name")
        if m_name:
            u_res, u_status = self.user_manager.search({"name": m_name})
            if u_status == 200:
                u_data = u_res.get("data")
                manager_id = u_data[0].get("id") if isinstance(u_data, list) and u_data else u_data.get("id") if isinstance(u_data, dict) else None

        # 3. PAYLOAD DE ACTUALIZACIÓN
        # Si filtramos por nombre, el 'phone' del request es el NUEVO.
        # Si filtramos por phone, el 'name' del request es el NUEVO.
        patch_data = {
            "name": request_json.get("new_name") or request_json.get("name"),
            "mobile": request_json.get("new_phone") or request_json.get("phone") or request_json.get("mobile"),
            "email": request_json.get("email"),
            "nif": request_json.get("nif"),
            "gender": request_json.get("gender"),
            "manager_id": manager_id
        }

        clean_patch = {k: v for k, v in patch_data.items() if v is not None and v != ""}

        # 4. PETICIÓN PATCH
        try:
            url_zoa = f"{self.api_base}/pipelines/contacts/{contact_id}"
            print(f"DEBUG: Realizando PATCH a {url_zoa} con data: {clean_patch}")
            response = requests.patch(url_zoa, headers=self.headers, json=clean_patch)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500