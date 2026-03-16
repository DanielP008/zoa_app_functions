import os
import requests
from models.contacts import ZoaContact
from models.users import ZoaUser
from models.tags import ZoaTags


class ZoaCard:
    def __init__(self, token=None, api_base=None):
        self.token = token or os.getenv("TOKEN")
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": self.token
        }
        self.contact_manager = ZoaContact(self.token, api_base)
        self.user_manager = ZoaUser(self.token, api_base)
        self.tag_manager = ZoaTags(self.token, api_base)

    def search(self, request_json):
        title = request_json.get("title")
        if title and str(title).strip():
            try:
                response = requests.get(f"{self.api_base}/pipelines/cards/title/{title}", headers=self.headers)
                if response.status_code == 200:
                    return response.json(), 200
            except Exception:
                pass

        if any(request_json.get(k) for k in ["phone", "email", "nif", "mobile"]):
            c_res, c_status = self.contact_manager.search(request_json)
            if c_status == 200:
                contact_id = self._extract_id(c_res)
                if contact_id:
                    return self.list_by_contact(contact_id)
        return {"error": "No se encontró la card"}, 404

    def list_by_contact(self, contact_id):
        try:
            response = requests.get(f"{self.api_base}/pipelines/cards/contact/{contact_id}", headers=self.headers)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def create(self, request_json):
        try:
            c_type = request_json.get("card_type") or "opportunity"
            p_id, s_id = self._get_context_ids(
                request_json.get("pipeline_name"),
                request_json.get("stage_name") or "Nuevo",
                c_type
            )
            if not s_id:
                return {"error": f"No se pudo determinar la etapa para {c_type}"}, 404

            c_res, c_status = self.contact_manager.search(request_json)
            contact_id = self._extract_id(c_res) if c_status == 200 else None
            if not contact_id:
                return {"error": "Contacto no identificado"}, 404

            tag_ids = self._resolve_tag_ids(request_json.get("tags_name"))
            manager_id = self._resolve_user_id(request_json.get("manager_name"))
            
            payload = {
                "stage_id": s_id,
                "pipeline_id": p_id,
                "title": request_json.get("title"),
                "contact_id": contact_id,
                "card_type": c_type,
                "amount": float(request_json.get("amount") or 0),
                "tag_id": tag_ids,
                "description": request_json.get("description"),
                "manager_id": manager_id
            }
            response = requests.post(f"{self.api_base}/pipelines/cards", headers=self.headers, json=payload)
            res_json = response.json()
            card_id = res_json.get("data", {}).get("id")

            # PATCH to ensure tags are attached reliably
            if card_id and tag_ids:
                requests.patch(f"{self.api_base}/pipelines/cards/{card_id}", headers=self.headers, json={"tag_id": tag_ids})

            return res_json, response.status_code
        except Exception as e:
            return {"error": str(e)}, 500

    def update(self, request_json):
        card_id = request_json.get("card_id")
        target_title = request_json.get("title")
        if not card_id:
            c_res, c_status = self.search(request_json)
            if c_status == 200:
                data = c_res.get("data", [])
                found = next((c for c in data if c.get("title") == target_title), data[0]) if isinstance(data, list) and data else data
                card_id = found.get("id") if isinstance(found, dict) else None

        if not card_id:
            return {"error": "No se encontró la card para actualizar"}, 404

        c_type = request_json.get("card_type") or "opportunity"
        s_name = request_json.get("new_stage_name") or request_json.get("stage_name")
        p_name = request_json.get("new_pipeline_name") or request_json.get("pipeline_name")
        p_id, s_id = self._get_context_ids(p_name, s_name, c_type) if s_name else (None, None)

        tags_input = request_json.get("new_tags_name") or request_json.get("tags_name")
        tag_ids = self._resolve_tag_ids(tags_input) if tags_input else None
        manager_id = self._resolve_user_id(request_json.get("manager_name"))

        patch = {
            "title": request_json.get("new_title"),
            "pipeline_id": p_id,
            "stage_id": s_id,
            "tag_id": tag_ids,
            "amount": float(request_json.get("amount")) if request_json.get("amount") else None,
            "description": request_json.get("description"),
            "manager_id": manager_id
        }
        patch = {k: v for k, v in patch.items() if v is not None}
        try:
            response = requests.patch(f"{self.api_base}/pipelines/cards/{card_id}", headers=self.headers, json=patch)
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

    def _resolve_user_id(self, name):
        if not name:
            return None
        u_res, u_status = self.user_manager.search({"name": name})
        if u_status != 200:
            return None
        u_data = u_res.get("data")
        if isinstance(u_data, list) and u_data:
            return u_data[0].get("id")
        if isinstance(u_data, dict):
            return u_data.get("id")
        return None

    def _resolve_tag_ids(self, tags_name):
        if not tags_name:
            return []
        if isinstance(tags_name, str):
            names = [t.strip().lower() for t in tags_name.split(",") if t.strip()]
        elif isinstance(tags_name, list):
            names = [str(t).strip().lower() for t in tags_name if str(t).strip()]
        else:
            return []

        tags_res, status = self.tag_manager.search()
        if status != 200:
            return []
        tag_map = {t.get("name", "").lower().strip(): t.get("id") for t in tags_res.get("data", [])}
        return [tag_map[n] for n in names if n in tag_map]

    def _get_context_ids(self, p_name, s_name, card_type):
        p_type = "management" if str(card_type).lower() == "task" else "sales"
        try:
            response = requests.get(f"{self.api_base}/pipelines/pipelines?type={p_type}", headers=self.headers, timeout=5)
            if response.status_code != 200:
                return None, None
            data = response.json().get("data", [])
            if not data:
                alt = requests.get(f"{self.api_base}/pipelines/pipelines?type=task", headers=self.headers, timeout=5)
                data = alt.json().get("data", [])
            if not data:
                return None, None

            pipeline = None
            if p_name:
                pipeline = next((p for p in data if str(p.get("name", "")).lower().strip() == str(p_name).lower().strip()), None)
            pipeline = pipeline or data[0]

            stages = pipeline.get("stages", [])
            term = str(s_name).lower().strip() if s_name else ""
            stage = next(
                (s for s in stages if term in [str(s.get("title") or "").lower().strip(), str(s.get("name") or "").lower().strip()]),
                stages[0] if stages else None
            )
            return pipeline.get("id"), stage.get("id") if stage else None
        except Exception:
            return None, None
