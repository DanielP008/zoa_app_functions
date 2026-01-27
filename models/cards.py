import requests
from models.contacts import ZoaContact
from models.users import ZoaUser
from models.tags import ZoaTags

class ZoaCard:
    def __init__(self, token):
        self.token = token
        self.api_base = "https://api.zoasuite.com/api"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": f"{self.token}"
        }
        self.contact_manager = ZoaContact(token)
        self.user_manager = ZoaUser(token)
        self.tag_manager = ZoaTags(token)

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
        Versión ultra-diagnostic para identificar por qué se queda colgado.
        """
        # Cambiamos el orden: primero management porque es lo que vimos en tus imágenes
        c_type_lower = str(card_type).lower()
        p_type = "management" if c_type_lower == "task" else "sales"
        
        print(f"DEBUG: Intentando llamar a ZOA API. Tipo: {p_type}")
        
        try:
            url = f"{self.api_base}/pipelines/pipelines?type={p_type}"
            # Bajamos el timeout para que no se quede colgado el contenedor
            response = requests.get(url, headers=self.headers, timeout=5)
            
            print(f"DEBUG: Respuesta recibida. Status Code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"DEBUG: Error en API. Texto: {response.text[:100]}")
                return None, None
            
            res_json = response.json()
            data = res_json.get('data', [])
            print(f"DEBUG: Cantidad de pipelines encontrados: {len(data)}")

            if not data:
                # Si management falla, probamos con 'task' como último recurso
                print("DEBUG: Lista vacía. Reintentando con tipo 'task'...")
                url_alt = f"{self.api_base}/pipelines/pipelines?type=task"
                response = requests.get(url_alt, headers=self.headers, timeout=5)
                data = response.json().get('data', [])
            
            if not data:
                print("DEBUG: Sigue sin haber datos. Abortando.")
                return None, None

            # 1. Pipeline
            pipeline = None
            if p_name:
                pipeline = next((p for p in data if str(p.get('name','')).lower().strip() == str(p_name).lower().strip()), None)
            
            if not pipeline:
                pipeline = data[0]
                print(f"DEBUG: Seleccionado pipeline por defecto: {pipeline.get('name')}")

            # 2. Stage
            stages = pipeline.get('stages', [])
            stage_obj = None
            search_term = str(s_name).lower().strip() if s_name else ""
            
            # Buscamos de forma flexible
            for s in stages:
                title_s = str(s.get('title') or "").lower().strip()
                name_s = str(s.get('name') or "").lower().strip()
                if search_term in [title_s, name_s]:
                    stage_obj = s
                    break
            
            if not stage_obj and stages:
                stage_obj = stages[0]
                print(f"DEBUG: Usando primera columna como fallback")

            return pipeline.get('id'), stage_obj.get('id') if stage_obj else None
            
        except requests.exceptions.Timeout:
            print("ERROR: La API de ZOA tardó demasiado en responder (Timeout)")
            return None, None
        except Exception as e:
            print(f"ERROR inesperado en _get_context_ids: {str(e)}")
            return None, None

    def list_by_contact(self, contact_id):
        #Obtiene cards de un contacto
        url = f"{self.api_base}/pipelines/cards/contact/{contact_id}"
        try:
            response = requests.get(url, headers=self.headers)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

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
            c_type = request_json.get("card_type") or "opportunity"
            
            # 1. Obtener contexto automático (Management vs Sales)
            p_id, s_id = self._get_context_ids(
                request_json.get("pipeline_name"), 
                request_json.get("stage_name"),
                c_type
            )
            
            if not s_id:
                return {"error": f"No se pudo determinar la etapa para {c_type}"}, 404

            # 2. Búsqueda de Contacto
            c_res, c_status = self.contact_manager.search(request_json)
            contact_id = None
            if c_status == 200 and c_res.get("data"):
                data_c = c_res["data"]
                contact_id = data_c[0].get("id") if isinstance(data_c, list) and data_c else data_c.get("id")

            if not contact_id:
                return {"error": "Contacto no identificado"}, 404

            # 3. Tags
            tag_ids = self._resolve_tag_ids(request_json.get("tags_name"))

            # 4. POST inicial
            payload = {
                "stage_id": s_id,
                "pipeline_id": p_id,
                "title": request_json.get("title"),
                "contact_id": contact_id,
                "card_type": c_type,
                "amount": float(request_json.get("amount") or 0),
                "tag_id": tag_ids
            }
            
            response = requests.post(f"{self.api_base}/pipelines/cards", headers=self.headers, json=payload)
            res_json = response.json()
            card_id = res_json.get("data", {}).get("id")

            # 5. Sincronización PATCH (Doble paso para asegurar Tags)
            # Si envías los tag_id en el primer paquete (POST), la API podría ignorarlos porque aún está procesando la creación de la tarjeta "madre".
            # Al hacer el PATCH, nos aseguramos de que la tarjeta ya existe y le "pegamos" las etiquetas con total seguridad.
            if card_id and tag_ids:
                requests.patch(f"{self.api_base}/pipelines/cards/{card_id}", headers=self.headers, json={"tag_id": tag_ids})

            return res_json, response.status_code

        except Exception as e:
            return {"error": str(e)}, 500

    def update(self, request_json):
        card_id = request_json.get("card_id")
        target_title = request_json.get("title")
        
        # 1. Localizar Card
        if not card_id:
            c_res, c_status = self.search(request_json)
            if c_status == 200:
                data = c_res.get("data", [])
                found = next((c for c in data if c.get("title") == target_title), data[0]) if isinstance(data, list) and data else data
                card_id = found.get("id") if isinstance(found, dict) else None

        if not card_id:
            return {"error": "No se encontró la card para actualizar"}, 404

        # 2. Contexto Automático (Task/Opportunity)
        c_type = request_json.get("card_type") or "opportunity"
        s_name = request_json.get("new_stage_name") or request_json.get("stage_name")
        p_name = request_json.get("new_pipeline_name") or request_json.get("pipeline_name")
        
        p_id, s_id = None, None
        if s_name:
            p_id, s_id = self._get_context_ids(p_name, s_name, c_type)

        # 3. Tags
        tags_input = request_json.get("new_tags_name") or request_json.get("tags_name")
        tag_ids = self._resolve_tag_ids(tags_input) if tags_input else None

        # 4. Payload PATCH
        patch_payload = {
            "title": request_json.get("new_title"),
            "pipeline_id": p_id,
            "stage_id": s_id,
            "tag_id": tag_ids,
            "amount": float(request_json.get("amount")) if request_json.get("amount") else None,
            "description": request_json.get("description")
        }
        patch_payload = {k: v for k, v in patch_payload.items() if v is not None}

        try:
            url = f"{self.api_base}/pipelines/cards/{card_id}"
            response = requests.patch(url, headers=self.headers, json=patch_payload)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500