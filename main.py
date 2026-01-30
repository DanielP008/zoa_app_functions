import functions_framework
import json
import firebase_admin
from firebase_admin import firestore

# Inicialización de Firebase (opcional si no usas Firestore en este script, pero mantenida por compatibilidad)
if not firebase_admin._apps:
    firebase_admin.initialize_app()

@functions_framework.http
def main(request):
    # --- 1. Gestión de CORS (Crucial para evitar bloqueos) ---
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, apiKey',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Headers de respuesta estándar
    res_headers = {'Access-Control-Allow-Origin': '*'}

    # --- 2. Validación del JSON de entrada ---
    request_json = request.get_json(silent=True)
    if not request_json:
        print("ERROR: No se recibió JSON válido")
        return ({"error": "JSON body missing"}, 400, res_headers)

    # Validamos campos obligatorios
    action = request_json.get("action")
    option = request_json.get("option")
    company_id = request_json.get("company_id")

    if not action or not option:
        return ({"error": "Faltan campos obligatorios: 'action' u 'option'"}, 400, res_headers)

    if not company_id:
        print("ALERTA: Falta company_id")
        return ({"error": "Se requiere 'company_id'"}, 400, res_headers)

    # --- 3. Gestión del Token (Producción) ---
    from config import TOKEN
    token = TOKEN

    # --- 4. Enrutamiento de Acciones (Asignación del Cliente) ---
    client = None
    try:
        match action:
            case "contacts":
                from models.contacts import ZoaContact
                client = ZoaContact(token)
            case "users":
                from models.users import ZoaUser
                client = ZoaUser(token)
            case "cards":
                from models.cards import ZoaCard
                client = ZoaCard(token)
            case "cardact":
                from models.cardact import ZoaCardAct
                client = ZoaCardAct(token)
            case "activities":
                from models.activities import ZoaActivity
                client = ZoaActivity(token)
            case "departments":
                from models.departments import ZoaDepartment
                client = ZoaDepartment(token)
            case "tags":
                from models.tags import ZoaTags
                client = ZoaTags(token)
            case "readall":
                from models.readall import ZoaReadAll
                client = ZoaReadAll(token)
            case "email_module":
                from models.email_module import ZoaEmail
                client = ZoaEmail(token)
            case "conversations":
                from models.conversations import ZoaConversation
                client = ZoaConversation(token)
            case "notes":
                from models.notes import ZoaNote
                client = ZoaNote(token)
            case "scheduler":
                from models.scheduler import ZoaScheduler
                client = ZoaScheduler(token)
            case _:
                return ({"error": f"Acción '{action}' no reconocida"}, 404, res_headers)

        # --- 5. Ejecución de la Opción ---
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

        # Retorno exitoso
        return (result, status, res_headers)

    except Exception as e:
        print(f"ERROR CRÍTICO EN MAIN: {str(e)}")
        return ({
            "error": "Internal Server Error",
            "details": str(e)
        }, 500, res_headers)