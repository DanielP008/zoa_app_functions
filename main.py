import os
import sys
from dotenv import load_dotenv
import functions_framework
import json
import firebase_admin
from firebase_admin import firestore

from firebase_config import get_company_token_and_env

load_dotenv()

# --- Configuration Defaults (from .env matches config.py names) ---
# Default/Dev
ENV_API_BASE = os.getenv("API_BASE", "https://dev.api.zoasuite.com/api")
ENV_TOKEN = os.getenv("TOKEN", "sk_test_9f8a7b6c5d4e3f2a")

# Prod/VIMA
ENV_API_BASE_PROD = os.getenv("API_BASE_PROD", "https://api.zoasuite.com/api")
ENV_TOKEN_VIMA = os.getenv("TOKEN_VIMA")

# Fallback default token
DEFAULT_TOKEN = ENV_TOKEN

# Firebase initialization (optional if you don't use Firestore in this script, kept for compatibility)
if not firebase_admin._apps:
    firebase_admin.initialize_app()

@functions_framework.http
def main(request):
    # --- 1. CORS handling (crucial to avoid blocking) ---
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, apiKey',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Standard response headers
    res_headers = {'Access-Control-Allow-Origin': '*'}

    # --- 2. Input JSON validation ---
    request_json = request.get_json(silent=True)
    if not request_json:
        print("ERROR: No se recibió JSON válido")
        return ({"error": "JSON body missing"}, 400, res_headers)

    # Validate required fields
    action = request_json.get("action")
    option = request_json.get("option")
    company_id = request_json.get("company_id")

    if not action or not option:
        return ({"error": "Faltan campos obligatorios: 'action' u 'option'"}, 400, res_headers)

    if not company_id:
        print("ALERTA: Falta company_id")
        return ({"error": "Se requiere 'company_id'"}, 400, res_headers)

    # --- 3. Token handling via Firestore company configuration ---
    #
    # We resolve the API token and environment (test/prod) from Firestore
    # based on the provided company_id.
    token_info = get_company_token_and_env(str(company_id))

    if token_info:
        token, is_test = token_info

        # Choose base URL and Token depending on environment.
        # If is_test is True, we use the dev API base (API_BASE), otherwise production (API_BASE_PROD).
        if is_test:
            api_base = ENV_API_BASE
            print(f"[FLOW-ZOA] company_id={company_id} -> TEST env, api_base={api_base}", flush=True)
        else:
            api_base = ENV_API_BASE_PROD
            print(f"[FLOW-ZOA] company_id={company_id} -> PROD env, api_base={api_base}", flush=True)
    else:
        # Fallback to static config for backwards compatibility.
        print(
            f"[FLOW-ZOA] company_id={company_id} -> NO Firestore doc, using FALLBACK (ENV_TOKEN/ENV_API_BASE)",
            flush=True,
        )
        token = ENV_TOKEN
        api_base = ENV_API_BASE
        print(f"[FLOW-ZOA] fallback api_base={api_base}", flush=True)

    # --- 4. Action routing (client assignment) ---
    client = None
    try:
        match action:
            case "contacts":
                from models.contacts import ZoaContact
                client = ZoaContact(token, api_base)
            case "users":
                from models.users import ZoaUser
                client = ZoaUser(token, api_base)
            case "cards":
                from models.cards import ZoaCard
                client = ZoaCard(token, api_base)
            case "cardact":
                from models.cardact import ZoaCardAct
                client = ZoaCardAct(token, api_base)
            case "activities":
                from models.activities import ZoaActivity
                client = ZoaActivity(token, api_base)
            case "departments":
                from models.departments import ZoaDepartment
                client = ZoaDepartment(token, api_base)
            case "tags":
                from models.tags import ZoaTags
                client = ZoaTags(token, api_base)
            case "readall":
                from models.readall import ZoaReadAll
                client = ZoaReadAll(token, api_base)
            case "email_module":
                from models.email_module import ZoaEmail
                client = ZoaEmail(token, api_base)
            case "conversations":
                from models.conversations import ZoaConversation
                client = ZoaConversation(token, api_base)
            case "notes":
                from models.notes import ZoaNote
                client = ZoaNote(token, api_base)
            case "scheduler":
                from models.scheduler import ZoaScheduler
                client = ZoaScheduler(token, api_base)
            case _:
                return ({"error": f"Acción '{action}' no reconocida"}, 404, res_headers)

        # --- 5. Option execution ---
        match option:
            case "search":
                result, status = client.search(request_json)
            case "create":
                result, status = client.create(request_json)
            case "update":
                result, status = client.update(request_json)
            case "send":
                result, status = client.send(request_json)
            case "assign":
                result, status = client.assign(request_json)
            case "status":
                result, status = client.status(request_json)
            case "assign_status":
                result, status = client.assign_status(request_json)
            case _:
                return ({"error": f"Opción '{option}' no válida para '{action}'"}, 400, res_headers)

        # Success response
        return (result, status, res_headers)

    except Exception as e:
        print(f"ERROR CRÍTICO EN MAIN: {str(e)}")
        return ({
            "error": "Internal Server Error",
            "details": str(e)
        }, 500, res_headers)