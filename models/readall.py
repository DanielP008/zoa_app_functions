from models.contacts import ZoaContact
from models.cards import ZoaCard
from models.users import ZoaUser
import requests
import traceback

class ZoaReadAll:
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

    def _get_stage_map(self):
        """Obtiene todos los pipelines y crea un diccionario de {id_etapa: nombre_etapa}."""
        stage_map = {}
        try:
            # Traemos tanto sales como management para tener el mapa completo
            for p_type in ["sales", "management"]:
                res = requests.get(f"{self.api_base}/pipelines/pipelines?type={p_type}", headers=self.headers)
                if res.status_code == 200:
                    pipelines = res.json().get('data', [])
                    for pipe in pipelines:
                        for stage in pipe.get('stages', []):
                            stage_map[stage.get('id')] = stage.get('title') or stage.get('name')
        except Exception as e:
            pass
        return stage_map

    def search(self, request_json):
        try:
            # 1. SEARCH CONTACT
            c_res, c_status = self.contact_manager.search(request_json)
            if c_status != 200 or not c_res.get("data"):
                return {
                    "contact": {"name": "Desconocido"},
                    "manager": {"name": "No asignado", "phone": None},
                    "open_activities_count": 0,
                    "activities_details": []
                }, 200

            contact = c_res.get("data")[0] if isinstance(c_res.get("data"), list) else c_res.get("data")
            contact_id = contact.get("id")
            
            # 2. RESOLVE MANAGER AND PHONE
            m_id = contact.get("user_id") or contact.get("manager_id")
            manager_name = "No asignado"
            manager_phone = None
            
            if m_id:
                u_res, u_status = self.user_manager.search({"id": m_id})
                if u_status == 200:
                    u_data = u_res.get("data")
                    u_obj = u_data[0] if isinstance(u_data, list) and u_data else u_data
                    if isinstance(u_obj, dict):
                        # Extraer Nombre
                        manager_name = f"{u_obj.get('first_name', '')} {u_obj.get('last_name', '')}".strip() or u_obj.get("name")
                        # Extract phone (ZOA usually uses 'mobile' or 'phone')
                        manager_phone = u_obj.get("mobile") or u_obj.get("phone")

            # 3. LIST CARDS AND MAP STAGE_ID TO NAME
            cards_open = []
            cards_res, cards_status = self.card_manager.list_by_contact(contact_id)
            
            if cards_status == 200 and cards_res.get("data"):
                stages_info = self._get_stage_map()
                raw_cards = cards_res.get("data")
                card_list = raw_cards if isinstance(raw_cards, list) else [raw_cards]
                
                for card in card_list:
                    if card.get("status") not in ["won", "lost"]:
                        s_id = card.get("stage_id")
                        st_name = stages_info.get(s_id, "N/A")

                        cards_open.append({
                            "title": card.get("title"),
                            "type": card.get("card_type", "opportunity"),
                            "stage": st_name
                        })

            # Final response with manager phone
            return {
                "contact": {
                    "id": contact_id,
                    "name": contact.get("name"),
                    "nif": contact.get("nif")
                },
                "manager": {
                    "id": m_id,
                    "name": manager_name,
                    "phone": manager_phone
                },
                "open_activities_count": len(cards_open),
                "activities_details": cards_open
            }, 200

        except Exception as e:
            return {"error": str(e)}, 500