import requests
from datetime import datetime
from models.contacts import ZoaContact
from models.users import ZoaUser
from models.tags import ZoaTags

class ZoaCardAct:
    def __init__(self, token):
        from config import API_BASE
        self.token = token
        self.api_base = API_BASE
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": f"{self.token}"
        }
        self.contact_manager = ZoaContact(token)
        self.user_manager = ZoaUser(token)
        self.tag_manager = ZoaTags(token)
    
    def _resolve_user_id_by_name(self, name):
        """Busca un usuario por nombre y devuelve su ID."""
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

    def _resolve_tag_ids(self, tags_name):
        """Convierte nombres de tags en una lista de IDs (UUIDs)."""
        #Entran nombres de etiquetas, limpia el texto, quita espacios y busca en la base de datos de etiquetas de ZOA y la salida es una lista de IDs.
        if not tags_name:
            return []
        
        names_to_find = []
        if isinstance(tags_name, str):
            names_to_find = [t.strip().lower() for t in tags_name.split(",") if t.strip()]
        elif isinstance(tags_name, list):
            names_to_find = [str(t).strip().lower() for t in tags_name]

        if not names_to_find:
            return []

        tags_res, status = self.tag_manager.search()
        if status != 200:
            return []

        all_tags = tags_res.get("data", [])
        resolved_ids = []

        for name in names_to_find:
            tag_obj = next((t for t in all_tags if t.get("name", "").lower().strip() == name), None)
            if tag_obj:
                resolved_ids.append(tag_obj.get("id"))
        
        return resolved_ids

    def _get_context_ids(self, p_name, s_name, card_type):
        """
        Obtiene pipeline_id y stage_id para crear/actualizar cards.
        Para card_type=task usa type=management; para opportunity usa type=sales.
        """
        c_type_lower = str(card_type).lower()
        p_type = "management" if c_type_lower == "task" else "sales"

        print(f"[CARDACT_DEBUG] _get_context_ids | card_type={card_type!r} -> p_type={p_type!r} | pipeline_name={p_name!r} | stage_name={s_name!r}")

        try:
            url = f"{self.api_base}/pipelines/pipelines?type={p_type}"
            print(f"[CARDACT_DEBUG] GET {url}")
            response = requests.get(url, headers=self.headers, timeout=10)

            print(f"[CARDACT_DEBUG] Response status={response.status_code}")

            if response.status_code != 200:
                print(f"[CARDACT_DEBUG] API error body (first 500 chars): {response.text[:500]}")
                return None, None

            res_json = response.json()
            data = res_json.get("data", [])
            print(f"[CARDACT_DEBUG] Pipelines returned for type={p_type!r}: count={len(data)}")

            if not data:
                print(f"[CARDACT_DEBUG] No pipelines for type={p_type!r}. Trying type=task...")
                url_alt = f"{self.api_base}/pipelines/pipelines?type=task"
                response = requests.get(url_alt, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    data = response.json().get("data", [])
                    print(f"[CARDACT_DEBUG] Pipelines for type=task: count={len(data)}")
                else:
                    data = []

            if not data:
                print("[CARDACT_DEBUG] No pipelines found for management nor task. Cannot determine stage.")
                return None, None

            # Log pipeline names and IDs for diagnosis
            for i, p in enumerate(data):
                name = p.get("name") or p.get("title") or "(sin nombre)"
                pid = p.get("id")
                stages = p.get("stages") or []
                stage_names = [str(s.get("title") or s.get("name") or "(sin nombre)") for s in stages]
                print(f"[CARDACT_DEBUG] Pipeline[{i}] id={pid} name={name!r} stages={stage_names!r}")

            # 1. Select pipeline by name or first
            pipeline = None
            if p_name:
                p_name_clean = str(p_name).lower().strip()
                for p in data:
                    n = str(p.get("name") or p.get("title") or "").lower().strip()
                    if n == p_name_clean:
                        pipeline = p
                        break
                if not pipeline:
                    print(f"[CARDACT_DEBUG] No pipeline named {p_name!r}. Available: {[p.get('name') or p.get('title') for p in data]}")

            if not pipeline:
                pipeline = data[0]
                print(f"[CARDACT_DEBUG] Using first pipeline: name={pipeline.get('name')!r} id={pipeline.get('id')}")

            # 2. Select stage by name or first
            stages = pipeline.get("stages") or []
            stage_obj = None
            search_term = str(s_name).lower().strip() if s_name else ""

            if search_term:
                for s in stages:
                    title_s = str(s.get("title") or "").lower().strip()
                    name_s = str(s.get("name") or "").lower().strip()
                    if search_term == title_s or search_term == name_s or search_term in (title_s, name_s):
                        stage_obj = s
                        print(f"[CARDACT_DEBUG] Stage matched: title={s.get('title')!r} name={s.get('name')!r} id={s.get('id')}")
                        break
                if not stage_obj:
                    available = [f"title={s.get('title')!r} name={s.get('name')!r}" for s in stages]
                    print(f"[CARDACT_DEBUG] No stage matched {s_name!r}. Available: {available}")

            if not stage_obj and stages:
                stage_obj = stages[0]
                print(f"[CARDACT_DEBUG] Using first stage: title={stage_obj.get('title')!r} id={stage_obj.get('id')}")

            p_id = pipeline.get("id")
            s_id = stage_obj.get("id") if stage_obj else None
            print(f"[CARDACT_DEBUG] Result: pipeline_id={p_id} stage_id={s_id}")
            return p_id, s_id

        except requests.exceptions.Timeout:
            print("[CARDACT_DEBUG] Timeout calling ZOA pipelines API")
            return None, None
        except Exception as e:
            print(f"[CARDACT_DEBUG] Exception in _get_context_ids: {type(e).__name__}: {e}")
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
        """Auxiliar para resolver nombres de invitados en IDs de usuario."""
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
                print(f"Error buscando por título: {e}")

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
            # --- PARTE 1: CREACIÓN DE LA CARD ---
            c_type = request_json.get("card_type") or "opportunity"
            p_id, s_id = self._get_context_ids(
                request_json.get("pipeline_name"), #Princpial, Revisiones
                request_json.get("stage_name"), #Nuevo
                c_type
            )
            
            if not s_id: return {"error": f"No se pudo determinar la etapa para {c_type}"}, 404

            # Resolver el ID del Manager
            resolved_manager_id = self._resolve_user_id_by_name(request_json.get("manager_name"))
            print(f"DEBUG: Manager resuelto: {resolved_manager_id} para el nombre: {request_json.get('manager_name')}")

            c_res, c_status = self.contact_manager.search(request_json)
            contact_id = None
            if c_status == 200 and c_res.get("data"):
                data_c = c_res["data"]
                contact_id = data_c[0].get("id") if isinstance(data_c, list) and data_c else data_c.get("id")

            if not contact_id: return {"error": "Contacto no identificado"}, 404

            tag_ids = self._resolve_tag_ids(request_json.get("tags_name"))

            # --- CORRECCIÓN AQUÍ: CAMBIADO manager_id_id a manager_id ---
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

            # --- PARTE 2: CREACIÓN DE ACTIVIDAD ---
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
                    "manager_id": resolved_manager_id # <--- También lo asignamos aquí
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
            
            # 1. LOCALIZAR ID DE LA CARD
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
            patch_card_payload = {
                "title": request_json.get("new_title"),
                "amount": float(request_json.get("amount")) if request_json.get("amount") else None,
                "description": request_json.get("description"),
                "manager_id": resolved_manager_id
            }
            patch_card_payload = {k: v for k, v in patch_card_payload.items() if v is not None}
            if patch_card_payload:
                requests.patch(f"{self.api_base}/pipelines/cards/{card_id}", headers=self.headers, json=patch_card_payload, timeout=10)

            # 4. GESTIÓN DE ACTIVIDADES: BORRAR Y RECREAR (Para evitar duplicados y nombres erróneos)
            res_final = {"card_id_processed": card_id, "success": True}
            
            # Buscamos actividades actuales de la card
            res_acts = requests.get(f"{self.api_base}/pipelines/activities?card_id={card_id}", headers=self.headers, timeout=10)
            
            if res_acts.status_code == 200:
                activities_data = res_acts.json().get("data", [])
                if isinstance(activities_data, dict): activities_data = [activities_data]
                
                # ELIMINAR TODAS LAS ANTERIORES
                for act in activities_data:
                    old_id = act.get("id")
                    if old_id:
                        requests.delete(f"{self.api_base}/pipelines/activities/{old_id}", headers=self.headers, timeout=5)
                        print(f"DEBUG: Eliminada actividad antigua {old_id}")

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
                    "manager_id": resolved_manager_id,
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