import os
import requests
import logging
from datetime import datetime
from models.contacts import ZoaContact
from models.users import ZoaUser
from models.tags import ZoaTags

logger = logging.getLogger(__name__)


class ZoaCardAct:
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

            manager_id = self._resolve_user_id(request_json.get("manager_name"))
            contact_id = self._resolve_or_create_contact(request_json)
            if not contact_id:
                return {"error": "Contacto no identificado y sin datos para crearlo"}, 404

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
                "manager_id": manager_id
            }

            response = requests.post(f"{self.api_base}/pipelines/cards", headers=self.headers, json=card_payload)
            res_json = response.json()
            if response.status_code not in (200, 201):
                return res_json, response.status_code

            card_id = res_json.get("data", {}).get("id")
            
            # PATCH sync (two-step to ensure tags)
            if card_id and tag_ids:
                requests.patch(f"{self.api_base}/pipelines/cards/{card_id}", headers=self.headers, json={"tag_id": tag_ids})

            if request_json.get("type_of_activity"):
                res_json["activity_result"] = self._create_activity(request_json, contact_id, card_id, manager_id)

            return res_json, 200
        except Exception as e:
            return {"error": str(e)}, 500

    def update(self, request_json):
        try:
            card_id = request_json.get("card_id")
            target_title = request_json.get("title")
            if not card_id:
                c_res, c_status = self.search(request_json)
                if c_status == 200:
                    data = c_res.get("data", [])
                    if isinstance(data, list) and data:
                        found = next(
                            (c for c in data if str(c.get("title")).lower() == str(target_title).lower()),
                            data[0]
                        ) if target_title else data[0]
                        card_id = found.get("id")
                    elif isinstance(data, dict):
                        card_id = data.get("id")

            if not card_id:
                return {"error": "No se localizó la Card."}, 404

            manager_id = self._resolve_user_id(request_json.get("manager_name"))
            tag_ids = self._resolve_tag_ids(request_json.get("tags_name"), create_missing=True) if request_json.get("tags_name") else None

            patch = {
                "title": request_json.get("new_title"),
                "amount": float(request_json.get("amount")) if request_json.get("amount") else None,
                "description": request_json.get("description"),
                "manager_id": manager_id,
                "tag_id": tag_ids,
            }
            patch = {k: v for k, v in patch.items() if v is not None}
            if patch:
                requests.patch(f"{self.api_base}/pipelines/cards/{card_id}", headers=self.headers, json=patch, timeout=10)

            res_final = {"card_id_processed": card_id, "success": True}

            self._delete_card_activities(card_id)

            if any(request_json.get(k) for k in ["date", "start_time", "activity_title", "type_of_activity"]):
                contact_id = request_json.get("contact_id") or self._get_card_contact_id(card_id)
                guests_ids = self._resolve_guests(request_json.get("guests_names"))
                now = datetime.now()
                raw_time = request_json.get("start_time")
                clean_time = raw_time[:5] if raw_time and len(raw_time) > 5 else raw_time

                act_payload = {
                    "title": request_json.get("activity_title") or "Nueva Actividad",
                    "type_of_activity": request_json.get("type_of_activity") or "llamada",
                    "description": request_json.get("activity_description"),
                    "contact_id": contact_id,
                    "card_id": card_id,
                    "type": request_json.get("type", "task" if str(request_json.get("card_type", "")).lower() == "task" else "sales"),
                    "date": request_json.get("date") or now.strftime("%Y-%m-%d"),
                    "start_time": clean_time or now.strftime("%H:%M"),
                    "duration": str(request_json.get("duration") or "30"),
                    "user_id": manager_id,
                    "guests": guests_ids
                }
                act_payload = {k: v for k, v in act_payload.items() if v is not None}
                r = requests.post(f"{self.api_base}/pipelines/activities", headers=self.headers, json=act_payload, timeout=10)
                if r.status_code in (200, 201):
                    res_final["activity_status"] = "Recreada correctamente"
                    res_final["activity_result"] = r.json()
                else:
                    res_final["activity_error"] = r.text

            return res_final, 200
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

    def _resolve_guests(self, guests_names):
        if not guests_names:
            return []
        ids = []
        for name in (n.strip() for n in guests_names.split(",") if n.strip()):
            uid = self._resolve_user_id(name)
            if uid:
                ids.append(uid)
        return ids

    def _resolve_or_create_contact(self, request_json):
        c_res, c_status = self.contact_manager.search(request_json)
        if c_status == 200 and c_res.get("data"):
            return self._extract_id(c_res)

        phone = request_json.get("phone") or request_json.get("mobile")
        email = request_json.get("email")
        name = request_json.get("contact_name") or request_json.get("name") or phone or email
        if not name:
            return None

        cc_res, cc_status = self.contact_manager.create({
            "name": name,
            "mobile": phone or "",
            "email": email or "",
            "manager_name": request_json.get("manager_name"),
        })
        if cc_status in (200, 201):
            return self._extract_id(cc_res)
        return None

    def _resolve_tag_ids(self, tags_name, create_missing=False):
        if not tags_name:
            return []
        if isinstance(tags_name, str):
            raw = [n.strip() for n in tags_name.split(",") if n.strip()]
        elif isinstance(tags_name, list):
            raw = [str(t).strip() for t in tags_name if str(t).strip()]
        else:
            return []

        tags_res, status = self.tag_manager.search()
        if status != 200:
            return []
        tag_map = {t.get("name", "").lower().strip(): t.get("id") for t in tags_res.get("data", [])}

        ids = []
        for name in raw:
            key = name.lower()
            if key in tag_map:
                ids.append(tag_map[key])
            elif create_missing:
                created, c_status = self.tag_manager.create({"name": name})
                if c_status in (200, 201):
                    new_id = created.get("data", created).get("id")
                    if new_id:
                        ids.append(new_id)
        return ids

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

    def _create_activity(self, request_json, contact_id, card_id, manager_id):
        now = datetime.now()
        guests_ids = self._resolve_guests(request_json.get("guests_names"))
        payload = {
            "title": request_json.get("activity_title") or f"Actividad: {request_json.get('title')}",
            "type_of_activity": request_json.get("type_of_activity", "llamada"),
            "contact_id": contact_id,
            "card_id": card_id,
            "type": request_json.get("type", "task" if str(request_json.get("card_type", "")).lower() == "task" else "sales"),
            "date": request_json.get("date") or now.strftime("%Y-%m-%d"),
            "start_time": request_json.get("start_time") or now.strftime("%H:%M"),
            "duration": str(request_json.get("duration") or "30"),
            "description": request_json.get("activity_description") or request_json.get("description"),
            "guests": guests_ids,
            "user_id": manager_id
        }
        payload = {k: v for k, v in payload.items() if v is not None and v != ""}
        response = requests.post(f"{self.api_base}/pipelines/activities", headers=self.headers, json=payload)
        return response.json()

    def _delete_card_activities(self, card_id):
        try:
            res = requests.get(f"{self.api_base}/pipelines/activities?card_id={card_id}", headers=self.headers, timeout=10)
            if res.status_code == 200:
                activities = res.json().get("data", [])
                if isinstance(activities, dict):
                    activities = [activities]
                for act in activities:
                    act_id = act.get("id")
                    if act_id:
                        requests.delete(f"{self.api_base}/pipelines/activities/{act_id}", headers=self.headers, timeout=5)
        except Exception:
            pass

    def _get_card_contact_id(self, card_id):
        try:
            res = requests.get(f"{self.api_base}/pipelines/cards/{card_id}", headers=self.headers)
            return res.json().get("data", {}).get("contact_id")
        except Exception:
            return None
