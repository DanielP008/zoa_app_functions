import requests
from models.contacts import ZoaContact

class ZoaDepartment:
    def __init__(self, token=None, api_base=None):
        import os
        # Use env vars directly (Global configuration)
        self.token = token or os.getenv("TOKEN")
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": f"{self.token}"
        }
        self.contact_manager = ZoaContact(self.token, api_base)

    def search(self, request_json):
        mobile = request_json.get("phone") or request_json.get("mobile")
        if not mobile:
            return {"error": "Falta el parámetro 'phone' o 'mobile'"}, 400

        try:
            # 1. Search contact
            c_res, c_status = self.contact_manager.search({"mobile": mobile})
            if c_status != 200:
                return c_res, c_status

            data_c = c_res.get("data", [])
            contact = data_c[0] if isinstance(data_c, list) and data_c else data_c
            
            # ID que viene del contacto
            m_id_ref = str(contact.get("manager_id") or "").strip().lower()
            print(f"DEBUG DEPARTMENTS: ID Manager buscado (desde contacto): '{m_id_ref}'")

            if not m_id_ref or m_id_ref == "none":
                return {"error": "Contacto sin gestor asignado en ZOA"}, 404

            # 2. Get department team
            url_dept = f"{self.api_base}/pipelines/users/{m_id_ref}/department-users"
            response = requests.get(url_dept, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                print(f"DEBUG DEPARTMENTS: Error API ZOA ({response.status_code}): {response.text}")
                return {"error": "No se pudo obtener el equipo del departamento"}, response.status_code

            dept_data = response.json()
            payload = dept_data.get("data", {})
            users_list = payload.get("users", [])
            print(f"DEBUG DEPARTMENTS: Usuarios encontrados en el departamento: {len(users_list)}")

            team_details = []
            extensions_only = []
            primary_manager_extension = None

            # 3. Mapear equipo
            for user in users_list:
                ext = user.get("voip_extension")
                u_id = str(user.get("id") or "").strip().lower()
                u_full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                
                # Comparison log
                print(f"DEBUG DEPARTMENTS: Comparando '{u_id}' == '{m_id_ref}' | Miembro: {u_full_name} | Ext: {ext}")
                
                if ext:
                    member_info = {"name": u_full_name, "extension": ext}
                    
                    # Verificación de ID
                    if u_id == m_id_ref:
                        print(f"DEBUG DEPARTMENTS: MATCH ENCONTRADO para {u_full_name}")
                        member_info["is_primary"] = True
                        primary_manager_extension = ext
                    
                    team_details.append(member_info)
                    extensions_only.append(str(ext))

            # 4. SAFETY HANDLING (if match failed)
            if primary_manager_extension is None and team_details:
                print("DEBUG DEPARTMENTS: No hubo match de ID. Aplicando failsafe (primer usuario = principal)")
                primary_manager_extension = team_details[0]["extension"]
                team_details[0]["is_primary"] = True

            # 5. Sort and build string
            team_details.sort(key=lambda x: x.get('is_primary', False), reverse=True)
            voip_dial_string = "&".join([f"Local/{ext}@users" for ext in extensions_only])

            return {
                "department_id": payload.get("department_id"),
                "primary_manager_extension": primary_manager_extension,
                "team": team_details,
                "all_extensions": ",".join(extensions_only),
                "voip_extensions": voip_dial_string
            }, 200

        except Exception as e:
            print(f"DEBUG DEPARTMENTS ERROR CRÍTICO: {str(e)}")
            return {"error": str(e)}, 500