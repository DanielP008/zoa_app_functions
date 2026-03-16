import os
import requests
from models.contacts import ZoaContact


class ZoaDepartment:
    def __init__(self, token=None, api_base=None):
        self.token = token or os.getenv("TOKEN")
        self.api_base = api_base or os.getenv("API_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apiKey": self.token
        }
        self.contact_manager = ZoaContact(self.token, api_base)

    def search(self, request_json):
        mobile = request_json.get("phone") or request_json.get("mobile")
        if not mobile:
            return {"error": "Falta el parámetro 'phone' o 'mobile'"}, 400
        try:
            c_res, c_status = self.contact_manager.search({"mobile": mobile})
            if c_status != 200:
                return c_res, c_status

            data_c = c_res.get("data", [])
            contact = data_c[0] if isinstance(data_c, list) and data_c else data_c
            m_id = str(contact.get("manager_id") or "").strip().lower()
            if not m_id or m_id == "none":
                return {"error": "Contacto sin gestor asignado en ZOA"}, 404

            response = requests.get(
                f"{self.api_base}/pipelines/users/{m_id}/department-users",
                headers=self.headers, timeout=10
            )
            if response.status_code != 200:
                return {"error": "No se pudo obtener el equipo del departamento"}, response.status_code

            return self._build_team_response(response.json().get("data", {}), m_id), 200
        except Exception as e:
            return {"error": str(e)}, 500

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_team_response(payload, manager_id_ref):
        team_details = []
        extensions = []
        primary_ext = None

        for user in payload.get("users", []):
            ext = user.get("voip_extension")
            if not ext:
                continue
            u_id = str(user.get("id") or "").strip().lower()
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            member = {"name": name, "extension": ext}
            if u_id == manager_id_ref:
                member["is_primary"] = True
                primary_ext = ext
            team_details.append(member)
            extensions.append(str(ext))

        if primary_ext is None and team_details:
            primary_ext = team_details[0]["extension"]
            team_details[0]["is_primary"] = True

        team_details.sort(key=lambda x: x.get("is_primary", False), reverse=True)
        return {
            "department_id": payload.get("department_id"),
            "primary_manager_extension": primary_ext,
            "team": team_details,
            "all_extensions": ",".join(extensions),
            "voip_extensions": "&".join(f"Local/{e}@users" for e in extensions)
        }
