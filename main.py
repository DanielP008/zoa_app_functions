import functions_framework
import json
import firebase_admin
from firebase_admin import firestore

firebase_admin.initialize_app()

@functions_framework.http
def main(request):
    # --- 0. Debug completo de entrada ---
    try:
        raw_body = request.get_data(as_text=True)
    except Exception:
        raw_body = "<unavailable>"
    print("[FLOW_ZOA_DEBUG] request.method:", request.method)
    print("[FLOW_ZOA_DEBUG] request.path:", getattr(request, "path", ""))
    print("[FLOW_ZOA_DEBUG] request.args:", request.args.to_dict(flat=True) if hasattr(request, "args") else {})
    print("[FLOW_ZOA_DEBUG] request.headers:", dict(request.headers) if hasattr(request, "headers") else {})
    print("[FLOW_ZOA_DEBUG] request.raw_body:", raw_body)
    print("[FLOW_ZOA_DEBUG] request.json:", request.get_json(silent=True))

    # --- 1. Gestión de CORS ---
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {'Access-Control-Allow-Origin': '*'}

    # --- 2. Validación Básica del Request ---
    request_json = request.get_json(silent=True)
    if not request_json:
        print("ERROR: No se recibió request_json JSON")
        return ({"error": "request_json missing"}, 400, headers)

    # Validamos que venga la acción y la opción
    if not request_json.get("action") or not request_json.get("option"):
        return ({"error": "Faltan campos obligatorios: 'action' u 'option'"}, 400, headers)

    # Validamos que venga AL MENOS un identificador de compañía
    company_id = request_json.get("company_id")
    
    if not company_id:
        print("ALERTA: Falta company_id")
        return ({"error": "Se requiere 'company_id'"}, 400, headers)

    # --- 3. Token ---
    from config import API_BASE, TOKEN
    token = TOKEN
    
    action = request_json.get("action")
    option = request_json.get("option")



    # 1. Asignación del Cliente según la acción
    client = None
    if action == "contacts":
        from models.contacts import ZoaContact
        client = ZoaContact(token)
    elif action == "users":
        from models.users import ZoaUser
        client = ZoaUser(token)
    elif action == "cards":
        from models.cards import ZoaCard
        client = ZoaCard(token)
    elif action == "cardact":
        from models.cardact import ZoaCardAct
        client = ZoaCardAct(token)
    elif action == "activities":
        from models.activities import ZoaActivity
        client = ZoaActivity(token)
    elif action == "readall":
        from models.readall import ZoaReadAll
        client = ZoaReadAll(token)
    elif action == "email_module":
        from models.email_module import ZoaEmail
        client = ZoaEmail(token)
    elif action == "conversations":
        from models.conversations import ZoaConversation
        client = ZoaConversation(token)
    elif action == "notes":
        from models.notes import ZoaNote
        client = ZoaNote(token)
    elif action == "tags":
        from models.tags import ZoaTags
        client = ZoaTags(token)  
    elif action  == "scheduler":
        from models.scheduler import ZoaScheduler
        client = ZoaScheduler(token) 
    elif action  == "departments":
        from models.departments import ZoaDepartment
        client = ZoaDepartment(token) 
    else:
        return {"error": f"Action '{action}' not recognized"}, 404



    # 2. Ejecución generalizada de la opción
    #APUNTES: Si intentaras ejecutar manager.create() sobre el módulo de usuarios, el programa se rompería (daría un error de tipo AttributeError).
    #Con hasattr, el código comprueba: "¿Este manager que acabo de cargar tiene permiso para crear?".
    #Si la respuesta es no, salta al else y devuelve un error amigable en lugar de colapsar la función.
    try:
        if option == "search":
            result, status = client.search(request_json)
        elif option == "create":  
            result, status = client.create(request_json)
        elif option == "update":
            result, status = client.update(request_json)
            
        elif option == "send":
            result, status = client.send(request_json)
        elif option == "assign":
            result, status = client.assign(request_json)
        elif option == "status":
            result, status = client.status(request_json)
        elif option == "assign_status":
            result, status = client.assign_status(request_json)
        else:
            return {"error": f"Option '{option}' is not valid for action '{action}'"}, 400

        return (result, status, headers)
    #Si no devuelves los headers en cada respuesta, cuando tu código falle (por ejemplo, un error 400), el navegador del cliente bloqueará la respuesta por seguridad (error de CORS).
    #Al ponerlo en el return, aseguras que el cliente siempre pueda leer el mensaje de error, sea cual sea el resultado.

    except Exception as e:

        print(f"ERROR CRÍTICO: {str(e)}")
        return ({
            "error": "Internal Server Error", 
            "details": str(e)
        }, 500, headers) # <--- Asegúrate de devolver los 3 elementos