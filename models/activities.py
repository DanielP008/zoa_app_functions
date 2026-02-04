import requests
from models.contacts import ZoaContact
from models.cards import ZoaCard 
from models.users import ZoaUser

class ZoaActivity:
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
        self.card_manager = ZoaCard(self.token, api_base) 
        self.user_manager = ZoaUser(self.token, api_base)
    
    def search(self, request_json):
        """
        Searches for a contact's activities.
        """
        # 1. Resolve contact ID using flexible logic (object or list)
        print("--- INICIANDO LÓGICA DE ACTIVIDADES ---")
        contact_id = None
        print(f"DEBUG: Buscando contacto con payload: {request_json}")
        
        if any(request_json.get(k) for k in ["phone", "email", "nif", "mobile"]):
            c_res, c_status = self.contact_manager.search(request_json)
            
            if c_status == 200 and isinstance(c_res, dict):
                data_content = c_res.get("data")
                
                # Case A: It's a list
                if isinstance(data_content, list) and len(data_content) > 0:
                    contact_id = data_content[0].get("id")
                # Case B: It's a direct object
                elif isinstance(data_content, dict):
                    contact_id = data_content.get("id")
                
                print(f"DEBUG: ID de contacto obtenido: {contact_id}")

        if not contact_id:
            return {"error": "No se encontró el contacto para recuperar sus actividades"}, 404

        # 2. GET call to ZOA: /pipelines/activities/contact/{contact_id}
        try:
            url = f"{self.api_base}/pipelines/activities/contact/{contact_id}"
            print(f"DEBUG: Realizando GET a ZOA Activities: {url}")
            
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                # ZOA API returns {"success": true, "data": [...activities...]}
                return response.json(), 200
            else:
                return {
                    "error": "Error al obtener actividades de ZOA",
                    "details": response.text
                }, response.status_code

        except Exception as e:
            return {"error": str(e)}, 500

    def create(self, request_json):
        """Creates an activity resolving Contact, Card and Guests."""
        
        # 1. Resolve Contact (flexible logic)
        contact_id = None
        if any(request_json.get(k) for k in ["phone", "email", "nif"]):
            c_res, c_status = self.contact_manager.search(request_json)
            if c_status == 200 and isinstance(c_res, dict):
                data = c_res.get("data")
                contact_id = data.get("id") if isinstance(data, dict) else (data[0].get("id") if data else None)

        # 2. Resolve Card (flexible logic)
        card_id = None
        card_name = request_json.get("card_name")
        if card_name:
            card_res, card_status = self.card_manager.search({"title": card_name})
            if card_status == 200 and isinstance(card_res, dict):
                data = card_res.get("data")
                # Card search may return list or object
                if isinstance(data, list) and len(data) > 0:
                    card_id = data[0].get("id")
                elif isinstance(data, dict):
                    card_id = data.get("id")

        # 3. Resolve Guests
        guests_ids = []
        guests_raw = request_json.get("guests_names")
        if guests_raw:
            names_list = [n.strip() for n in guests_raw.split(",") if n.strip()]
            for name in names_list:
                u_res, u_status = self.user_manager.search({"name": name})
                if u_status == 200 and isinstance(u_res, dict):
                    u_data = u_res.get("data")
                    uid = u_data[0].get("id") if isinstance(u_data, list) and u_data else u_data.get("id") if isinstance(u_data, dict) else None
                    if uid: guests_ids.append(uid)

        # 4. Resolve main manager (user_id) from name
        user_id = None
        manager_name = request_json.get("manager_name") or request_json.get("user_name")
        if manager_name:
            u_res, u_status = self.user_manager.search({"name": manager_name})
            if u_status == 200 and isinstance(u_res, dict):
                u_data = u_res.get("data", [])
                if isinstance(u_data, list) and len(u_data) > 0:
                    user_id = u_data[0].get("id")
                elif isinstance(u_data, dict):
                    user_id = u_data.get("id")

        # 5. Build final payload
        final_payload = {
            "title": request_json.get("title"),
            "type_of_activity": request_json.get("type_of_activity", "llamada"),
            "contact_id": contact_id,
            "card_id": card_id,
            "type": request_json.get("type", "sales"),
            "date": request_json.get("date"),
            "start_time": request_json.get("start_time"),
            "duration": str(request_json.get("duration")) if request_json.get("duration") else "30",
            "completed": request_json.get("completed", "not_completed"),
            "description": request_json.get("description"),
            "comment": request_json.get("comment"),
            "location": request_json.get("location"),
            "videocall_link": request_json.get("videocall_link"),
            "all_day": str(request_json.get("all_day", "")).lower() == "true",
            "guests": guests_ids,
            "repeat": str(request_json.get("repeat", "")).lower() == "true",
            "repetition_type": request_json.get("repetition_type"),
            "repetitions_number": int(request_json.get("repetitions_number")) if request_json.get("repetitions_number") else None,
            "days": request_json.get("days", []),
            "end_type": request_json.get("end_type", "never"),
            "end_date": request_json.get("end_date"),
            "end_after_occurrences": request_json.get("end_after_occurrences"),
            # En la API de ZOA el gestor de la actividad se espera en user_id
            "user_id": user_id
        }

        # Remove nulls to avoid sending junk to the API
        final_payload = {k: v for k, v in final_payload.items() if v is not None and v != ""}

        try:
            url = f"{self.api_base}/pipelines/activities"
            print(f"DEBUG: Enviando creación de actividad a ZOA para Contacto {contact_id}")
            response = requests.post(url, headers=self.headers, json=final_payload)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def update(self, request_json):
        """Updates an existing activity using PATCH with flexible search."""
        activity_id = request_json.get("activity_id")
        target_title = request_json.get("title")
        
        # 1. Locate activity if ID was not sent directly
        if not activity_id and target_title:
            print(f"DEBUG: Buscando actividad con título: {target_title}")
            
            # ATTEMPT A: By contact if phone/email present
            if any(request_json.get(k) for k in ["phone", "email", "nif"]):
                act_res, act_status = self.search(request_json)
                if act_status == 200:
                    activities = act_res.get("data", [])
                    found = next((a for a in activities if a.get("title") == target_title), None)
                    if found:
                        activity_id = found.get("id")

            # ATTEMPT B: General search by title (if Attempt A failed or no phone)
            if not activity_id:
                print("DEBUG: Buscando por título de forma general en el tenant...")
                try:
                    # Consultamos el endpoint general de actividades
                    response = requests.get(f"{self.api_base}/pipelines/activities", headers=self.headers)
                    if response.status_code == 200:
                        all_activities = response.json().get("data", [])
                        # Find activity matching exact title
                        found = next((a for a in all_activities if a.get("title") == target_title), None)
                        if found:
                            activity_id = found.get("id")
                            print(f"DEBUG: Actividad encontrada por título general: {activity_id}")
                except Exception as e:
                    print(f"Error en búsqueda general: {str(e)}")
        
        if not activity_id:
            return {"error": f"No se pudo localizar ninguna actividad con el título '{target_title}'"}, 404

        # 2. Resolve guest IDs
        guests_ids = []
        guests_raw = request_json.get("guests_names")
        if guests_raw:
            names_list = [n.strip() for n in guests_raw.split(",") if n.strip()]
            for name in names_list:
                u_res, u_status = self.user_manager.search({"name": name})
                if u_status == 200:
                    u_data = u_res.get("data")
                    uid = u_data[0].get("id") if isinstance(u_data, list) and u_data else u_data.get("id") if isinstance(u_data, dict) else None
                    if uid: guests_ids.append(uid)

        # 3. Preparar Payload para PATCH
        patch_payload = {}
        # Map updatable fields
        fields = ["title", "description", "completed", "date", "start_time", "duration"]
        for field in fields:
            val = request_json.get(f"new_{field}") or request_json.get(field)
            if val is not None and val != "":
                patch_payload[field] = val
        
        if guests_ids:
            patch_payload["guests"] = guests_ids

        # 4. Execute PATCH
        try:
            url = f"{self.api_base}/pipelines/activities/{activity_id}"
            print(f"DEBUG: Realizando PATCH a ZOA en: {url}")
            response = requests.patch(url, headers=self.headers, json=patch_payload)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500