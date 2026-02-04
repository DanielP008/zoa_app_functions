import requests
from datetime import datetime
from models.contacts import ZoaContact
from models.cards import ZoaCard
from models.users import ZoaUser

class ZoaNote:
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
        # Contact manager instance for search
        self.contact_manager = ZoaContact(self.token, api_base)
        self.card_manager = ZoaCard(self.token, api_base)
        self.user_manager = ZoaUser(self.token, api_base)
        
    def _get_contact_id(self, request_json):
        """
        Uses contacts module to get the ID.
        Searches by phone, mobile, nif, email or name.
        """
        # If ID is already provided, use it
        if request_json.get("contact_id"):
            return request_json.get("contact_id")

        print("DEBUG (Notes): Resolviendo contact_id desde contacts.py...")
        # Call the search method from contacts.py
        c_res, c_status = self.contact_manager.search(request_json)
        
        if c_status == 200 and isinstance(c_res, dict):
            data = c_res.get("data", [])
            if isinstance(data, list) and len(data) > 0:
                # Extract first ID found
                return data[0].get("id")
            elif isinstance(data, dict):
                return data.get("id")
        
        return None

    def search(self, request_json):
        """
        GET /api/pipelines/notes/contact/{contact_id}
        """
        contact_id = self._get_contact_id(request_json)
        
        if not contact_id:
            return {"error": "No se localizó el contacto para obtener sus notas"}, 404

        url = f"{self.api_base}/pipelines/notes/contact/{contact_id}"
        
        try:
            print(f"DEBUG: Consultando notas para contacto {contact_id}")
            response = requests.get(url, headers=self.headers)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": f"Error en búsqueda de notas: {str(e)}"}, 500

    def create(self, request_json):
        """
        Creates a note assigning it to a contact, a card and optionally a manager.
        """
        # 1. Resolve contact ID
        contact_id = self._get_contact_id(request_json)
        if not contact_id:
            return {"error": "No se puede identificar al contacto"}, 404

        # 2. Resolve Card ID (if not sent, find the active one)
        card_id = request_json.get("card_id")
        if not card_id:
            card_res, card_status = self.card_manager.search({"contact_id": contact_id})
            if card_status == 200:
                cards = card_res.get("data", [])
                if cards: card_id = cards[0].get("id")

        # 3. Resolve Manager (User) ID
        # Priority:
        #   1) If user_id is already in the payload, use it.
        #   2) If manager_name or user_name is sent, resolve by name.
        user_id = request_json.get("user_id")
        if not user_id:
            manager_name = request_json.get("manager_name") or request_json.get("user_name")
            if manager_name:
                print(f"DEBUG: Buscando ID para el manager/user: {manager_name}")
                u_res, u_status = self.user_manager.search({"name": manager_name})
                if u_status == 200:
                    # API usually returns a list or object under 'data'
                    u_data = u_res.get("data", [])
                    if isinstance(u_data, list) and len(u_data) > 0:
                        user_id = u_data[0].get("id")
                    elif isinstance(u_data, dict):
                        user_id = u_data.get("id")

        # 4. Build payload for ZOA
        url = f"{self.api_base}/pipelines/notes"
        payload = {
            "contact_id": contact_id,
            "card_id": card_id,
            "user_id": user_id,  # Assigned manager ID
            "content": request_json.get("content"),
            "date": request_json.get("date", datetime.now().strftime("%Y-%m-%d")),
            "is_pinned": request_json.get("is_pinned", False)
        }

        try:
            print(f"DEBUG: Creando nota. Contact:{contact_id} | Card:{card_id} | User:{user_id}")
            response = requests.post(url, headers=self.headers, json=payload)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def update(self, request_json):
        # 1. Obtener notas
        search_res, status = self.search(request_json)
        if status != 200:
            return search_res, status

        # 2. Validate response structure
        # ZOA returns { "success": true, "data": [...] }
        notes_list = search_res.get("data")
        if not isinstance(notes_list, list):
            return {"error": "La API no devolvió una lista de notas válida", "res": search_res}, 500

        target_date = request_json.get("date")
        old_content = request_json.get("old_content")
        note_id = None

        print(f"DEBUG: Buscando nota para fecha {target_date} entre {len(notes_list)} notas")

        # 3. Match the note (avoid IndexError)
        for note in notes_list:
            note_date = note.get("date")
            note_content = note.get("content", "")
            
            # Compare date
            if note_date == target_date:
                # If old_content exists, refine; otherwise take first for that date.
                if old_content:
                    if old_content.lower() in note_content.lower():
                        note_id = note.get("id")
                        break
                else:
                    note_id = note.get("id")
                    break

        if not note_id:
            return {"error": f"No se encontró nota en fecha {target_date}"}, 404

        # 4. Resolver Manager (opcional)
        user_id = None
        if request_json.get("manager_name"):
            u_res, u_status = self.user_manager.search({"name": request_json.get("manager_name")})
            if u_status == 200:
                u_data = u_res.get("data", [])
                if isinstance(u_data, list) and u_data:
                    user_id = u_data[0].get("id")

        # 5. Execute PATCH
        url_patch = f"{self.api_base}/pipelines/notes/{note_id}"
        payload = {
            "content": request_json.get("new_content") or request_json.get("content"),
            "is_pinned": request_json.get("is_pinned"),
            "user_id": user_id
        }
        clean_payload = {k: v for k, v in payload.items() if v is not None}

        try:
            print(f"DEBUG: Enviando PATCH a {url_patch}")
            response = requests.patch(url_patch, headers=self.headers, json=clean_payload)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": f"Excepción en PATCH: {str(e)}"}, 500