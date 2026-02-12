import requests
from datetime import datetime
from models.contacts import ZoaContact
from models.users import ZoaUser
from models.tags import ZoaTags

class ZoaCardAct:
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
        self.user_manager = ZoaUser(self.token, api_base)
        self.tag_manager = ZoaTags(self.token, api_base)
    
    def _resolve_user_id_by_name(self, name):
        """Looks up a user by name and returns their ID."""
        if not name:
            return None
        u_res, u_status = self.user_manager.search({"name": name})
        if u_status == 200:
            u_data = u_res.get("data")
            if isinstance(u_data, list) and u_data:
                return u_data[0].get("id")
            elif isinstance(u_data, dict):
                return u_data.get("id")
        return None

    def _resolve_tag_ids(self, tags_name, create_missing=False):
        """
        Converts tag names into a list of IDs (UUIDs).

        If create_missing=True, tags that don't exist are created in ZOA
        (using ZoaTags model) and their IDs are returned as well.
        """
        if not tags_name:
            return []
        
        # Keep both original and normalized name for search
        names_to_find = []
        if isinstance(tags_name, str):
            raw_names = [t for t in tags_name.split(",") if t.strip()]
            names_to_find = [(n.strip(), n.strip().lower()) for n in raw_names]
        elif isinstance(tags_name, list):
            raw_names = [str(t) for t in tags_name if str(t).strip()]
            names_to_find = [(n.strip(), n.strip().lower()) for n in raw_names]

        if not names_to_find:
            return []

        tags_res, status = self.tag_manager.search()
        if status != 200:
            return []

        all_tags = tags_res.get("data", [])
        resolved_ids = []

        for original_name, normalized_name in names_to_find:
            # Find existing tag by name (case-insensitive)
            tag_obj = next(
                (
                    t
                    for t in all_tags
                    if str(t.get("name", "")).lower().strip() == normalized_name
                ),
                None,
            )

            if tag_obj:
                resolved_ids.append(tag_obj.get("id"))
            elif create_missing:
                # Create the tag if it doesn't exist
                try:
                    create_payload = {"name": original_name}
                    created_tag, c_status = self.tag_manager.create(create_payload)
                    if c_status in (200, 201):
                        # API may return object in "data" or flat
                        data_ct = created_tag.get("data", created_tag)
                        resolved_ids.append(data_ct.get("id"))
                except Exception as e:
                    pass
        
        return resolved_ids

    def _get_context_ids(self, p_name, s_name, card_type):
        """
        Diagnostic helper to identify why the request might hang.

        Pipelines allowed in production: "Ventas", "Renovaciones".
        Pipelines allowed in test: "Principal", "Revisiones".
        """
        # Use management first for task type
        c_type_lower = str(card_type).lower()
        p_type = "management" if c_type_lower == "task" else "sales"
        
        try:
            url = f"{self.api_base}/pipelines/pipelines?type={p_type}"
            # Lower timeout so the container doesn't hang
            response = requests.get(url, headers=self.headers, timeout=5)
            
            if response.status_code != 200:
                return None, None
            
            res_json = response.json()
            data = res_json.get('data', [])

            if not data:
                # If management fails, try 'task' as fallback
                url_alt = f"{self.api_base}/pipelines/pipelines?type=task"
                response = requests.get(url_alt, headers=self.headers, timeout=5)
                data = response.json().get('data', [])
            
            if not data:
                return None, None

            # 1. Pipeline
            pipeline = None
            if p_name:
                pipeline = next((p for p in data if str(p.get('name','')).lower().strip() == str(p_name).lower().strip()), None)
            
            if not pipeline:
                pipeline = data[0]

            # 2. Stage
            stages = pipeline.get('stages', [])
            stage_obj = None
            search_term = str(s_name).lower().strip() if s_name else ""
            
            # Search flexibly
            for s in stages:
                title_s = str(s.get('title') or "").lower().strip()
                name_s = str(s.get('name') or "").lower().strip()
                if search_term in [title_s, name_s]:
                    stage_obj = s
                    break
            
            if not stage_obj and stages:
                stage_obj = stages[0]

            return pipeline.get('id'), stage_obj.get('id') if stage_obj else None
            
        except requests.exceptions.Timeout:
            return None, None
        except Exception as e:
            return None, None


    #Read all: Get all cards by contact_id
    def list_by_contact(self, contact_id):
        #Obtiene cards de un contacto
        url = f"{self.api_base}/pipelines/cards/contact/{contact_id}"
        try:
            response = requests.get(url, headers=self.headers)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def _resolve_guests_ids(self, guests_names):
        """Helper to resolve guest names to user IDs."""
        if not guests_names: return []
        guests_ids = []
        names_list = [n.strip() for n in guests_names.split(",") if n.strip()]
        for name in names_list:
            u_res, u_status = self.user_manager.search({"name": name})
            if u_status == 200:
                u_data = u_res.get("data")
                uid = u_data[0].get("id") if isinstance(u_data, list) and u_data else u_data.get("id") if isinstance(u_data, dict) else None
                if uid: guests_ids.append(uid)
        return guests_ids
    
    def search(self, request_json):
        title = request_json.get("title")
        if title and str(title).strip():
            try:
                url = f"{self.api_base}/pipelines/cards/title/{title}"
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    return response.json(), 200
            except Exception as e:
                pass

        if any(request_json.get(k) for k in ["phone", "email", "nif", "mobile"]):
            c_res, c_status = self.contact_manager.search(request_json)
            if c_status == 200:
                contacts_list = c_res.get("data", [])
                contact_id = None
                if isinstance(contacts_list, list) and len(contacts_list) > 0:
                    contact_id = contacts_list[0].get('id')
                elif isinstance(contacts_list, dict):
                    contact_id = contacts_list.get('id')
                
                if contact_id:
                    try:
                        url = f"{self.api_base}/pipelines/cards/contact/{contact_id}"
                        response = requests.get(url, headers=self.headers)
                        return response.json(), response.status_code
                    except Exception as e:
                        return {"error": str(e)}, 500
        return {"error": "No se encontró la card"}, 404


    def create(self, request_json):
        try:
            # --- PART 1: CARD CREATION ---
            c_type = request_json.get("card_type") or "opportunity"
            # If no stage_name is provided we default to "Nuevo"
            pipeline_name = request_json.get("pipeline_name")
            stage_name = request_json.get("stage_name") or "Nuevo"

            p_id, s_id = self._get_context_ids(pipeline_name, stage_name, c_type)
            
            if not s_id: return {"error": f"No se pudo determinar la etapa para {c_type}"}, 404

            # Resolve Manager ID
            resolved_manager_id = self._resolve_user_id_by_name(request_json.get("manager_name"))

            c_res, c_status = self.contact_manager.search(request_json)
            contact_id = None
            if c_status == 200 and c_res.get("data"):
                data_c = c_res["data"]
                contact_id = data_c[0].get("id") if isinstance(data_c, list) and data_c else data_c.get("id")

            if not contact_id: return {"error": "Contacto no identificado"}, 404

            # Resolve tags: if they don't exist, create them automatically
            tag_ids = self._resolve_tag_ids(request_json.get("tags_name"), create_missing=True)

            card_payload = {
                "stage_id": s_id,
                "pipeline_id": p_id,
                "title": request_json.get("title"),
                "contact_id": contact_id,
                "card_type": c_type,
                "amount": float(request_json.get("amount") or 0),
                "tag_id": tag_ids,
                "description": request_json.get("description"),
                "manager_id": resolved_manager_id  # <--- Corregido
            }
            
            response_card = requests.post(f"{self.api_base}/pipelines/cards", headers=self.headers, json=card_payload)
            res_card_json = response_card.json()
            card_id = res_card_json.get("data", {}).get("id")

            if response_card.status_code not in [200, 201]:
                return res_card_json, response_card.status_code

            # --- PART 2: ACTIVITY CREATION ---
            if request_json.get("type_of_activity"):
                guests_ids = self._resolve_guests_ids(request_json.get("guests_names"))
                activity_title = request_json.get("activity_title") or f"Actividad: {request_json.get('title')}"
                
                # Default dates
                now = datetime.now()
                default_date = now.strftime("%Y-%m-%d")
                default_time = now.strftime("%H:%M")

                activity_payload = {
                    "title": activity_title,
                    "type_of_activity": request_json.get("type_of_activity", "llamada"),
                    "contact_id": contact_id,
                    "card_id": card_id,
                    "type": request_json.get("type", "sales"),
                    "date": request_json.get("date") or default_date,
                    "start_time": request_json.get("start_time") or default_time,
                    "duration": str(request_json.get("duration") or "30"),
                    "description": request_json.get("activity_description") or request_json.get("description"),
                    "guests": guests_ids,
                    # ZOA API expects activity manager as user_id
                    "user_id": resolved_manager_id
                }
                
                activity_payload = {k: v for k, v in activity_payload.items() if v is not None and v != ""}
                response_act = requests.post(f"{self.api_base}/pipelines/activities", headers=self.headers, json=activity_payload)
                res_card_json["activity_result"] = response_act.json()

            return res_card_json, 200

        except Exception as e:
            return {"error": str(e)}, 500
    
    def update(self, request_json):
        try:
            card_id = request_json.get("card_id")
            target_title = request_json.get("title")
            
            # 1. LOCATE CARD ID
            if not card_id:
                c_res, c_status = self.search(request_json)
                if c_status == 200:
                    data = c_res.get("data", [])
                    if isinstance(data, list) and data:
                        found = next((c for c in data if str(c.get("title")).lower() == str(target_title).lower()), data[0]) if target_title else data[0]
                        card_id = found.get("id")
                    elif isinstance(data, dict):
                        card_id = data.get("id")

            if not card_id:
                return {"error": "No se localizó la Card."}, 404

            # 2. RESOLVER GESTOR E INVITADOS
            resolved_manager_id = self._resolve_user_id_by_name(request_json.get("manager_name"))
            guests_ids = self._resolve_guests_ids(request_json.get("guests_names"))
            contact_id = request_json.get("contact_id") # Intentar pillar el ID si viene

            # 3. ACTUALIZAR CARD
            # 3. ACTUALIZAR CARD
            # If new tag names are sent, resolve/create tags
            tag_ids = None
            if request_json.get("tags_name"):
                tag_ids = self._resolve_tag_ids(request_json.get("tags_name"), create_missing=True)

            patch_card_payload = {
                "title": request_json.get("new_title"),
                "amount": float(request_json.get("amount")) if request_json.get("amount") else None,
                "description": request_json.get("description"),
                "manager_id": resolved_manager_id,
                "tag_id": tag_ids if tag_ids else None,
            }
            patch_card_payload = {k: v for k, v in patch_card_payload.items() if v is not None}
            if patch_card_payload:
                requests.patch(f"{self.api_base}/pipelines/cards/{card_id}", headers=self.headers, json=patch_card_payload, timeout=10)

            # 4. ACTIVITY HANDLING: DELETE AND RECREATE (to avoid duplicates and wrong names)
            res_final = {"card_id_processed": card_id, "success": True}
            
            # Fetch current activities for the card
            res_acts = requests.get(f"{self.api_base}/pipelines/activities?card_id={card_id}", headers=self.headers, timeout=10)
            
            if res_acts.status_code == 200:
                activities_data = res_acts.json().get("data", [])
                if isinstance(activities_data, dict): activities_data = [activities_data]
                
                # DELETE ALL PREVIOUS ONES
                for act in activities_data:
                    old_id = act.get("id")
                    if old_id:
                        requests.delete(f"{self.api_base}/pipelines/activities/{old_id}", headers=self.headers, timeout=5)

            # 5. CREAR LA NUEVA ACTIVIDAD (Limpia y con los datos correctos)
            if any(request_json.get(k) for k in ["date", "start_time", "activity_title", "type_of_activity"]):
                # Necesitamos el contact_id. Si no lo tenemos, lo buscamos de la card
                if not contact_id:
                    card_detail = requests.get(f"{self.api_base}/pipelines/cards/{card_id}", headers=self.headers).json()
                    contact_id = card_detail.get("data", {}).get("contact_id")

                # Default dates
                now = datetime.now()
                default_date = now.strftime("%Y-%m-%d")
                default_time = now.strftime("%H:%M")

                raw_time = request_json.get("start_time")
                clean_time = raw_time[:5] if raw_time and len(raw_time) > 5 else raw_time
                
                final_date = request_json.get("date") or default_date
                final_time = clean_time or default_time

                new_act_payload = {
                    "title": request_json.get("activity_title") or "Nueva Actividad",
                    "type_of_activity": request_json.get("type_of_activity") or "llamada",
                    "description": request_json.get("activity_description"),
                    "contact_id": contact_id,
                    "card_id": card_id,
                    "date": final_date,
                    "start_time": final_time,
                    "duration": str(request_json.get("duration") or "30"),
                    # On update we also use user_id as main manager
                    "user_id": resolved_manager_id,
                    "guests": guests_ids
                }
                new_act_payload = {k: v for k, v in new_act_payload.items() if v is not None}
                
                r_create = requests.post(f"{self.api_base}/pipelines/activities", headers=self.headers, json=new_act_payload, timeout=10)
                
                if r_create.status_code in [200, 201]:
                    res_final["activity_status"] = "Recreada correctamente"
                    res_final["activity_result"] = r_create.json()
                else:
                    res_final["activity_error"] = r_create.text

            return res_final, 200

        except Exception as e:
            return {"error": str(e)}, 500