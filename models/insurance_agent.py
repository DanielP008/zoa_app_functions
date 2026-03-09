import os
import json
import copy
import logging

from models.ai_chat import ZoaAIChat

logger = logging.getLogger(__name__)


# ─── Data Templates ──────────────────────────────────────────────────────────

AUTO_TEMPLATE = {
    "complete": False,
    "ramo_activo": "AUTO",
    "vehiculo": {
        "matricula": ""
    },
    "tomador": {
        "nombre": "", "apellido1": "", "apellido2": "",
        "dni": "", "fecha_nacimiento": "", "fecha_carnet": "",
        "sexo": "", "estado_civil": "", "codigo_postal": ""
    },
    "poliza_actual": {
        "numero_poliza": "", "company": "", "fecha_efecto": ""
    }
}

HOGAR_TEMPLATE = {
    "complete": False,
    "ramo_activo": "HOGAR",
    "tomador": {
        "nombre": "", "apellido1": "", "apellido2": "",
        "dni": "", "fecha_nacimiento": "",
        "sexo": "", "estado_civil": "", "codigo_postal": ""
    },
    "vivienda": {
        "nombre_via": "", "numero_calle": "", "piso": "", "puerta": "",
        "tipo_vivienda": "", "uso_vivienda": "", "regimen_ocupacion": "",
        "numero_personas_vivienda": ""
    },
    "poliza_actual": {
        "fecha_efecto": ""
    }
}

AUTO_REQUIRED_FIELDS = [
    "vehiculo.matricula",
    "tomador.nombre", "tomador.apellido1", "tomador.dni",
    "tomador.fecha_nacimiento", "tomador.fecha_carnet",
    "tomador.sexo", "tomador.estado_civil", "tomador.codigo_postal",
    "poliza_actual.fecha_efecto"
]

HOGAR_REQUIRED_FIELDS = [
    "tomador.nombre", "tomador.apellido1", "tomador.dni",
    "tomador.fecha_nacimiento", "tomador.sexo", "tomador.estado_civil",
    "tomador.codigo_postal",
    "vivienda.nombre_via", "vivienda.numero_calle",
    "vivienda.tipo_vivienda", "vivienda.uso_vivienda",
    "vivienda.regimen_ocupacion",
    "poliza_actual.fecha_efecto"
]


# ─── LLM Prompts ─────────────────────────────────────────────────────────────

CLASSIFIER_SYSTEM = """\
Eres un filtro inteligente para un sistema de tarificación de seguros. \
Tu trabajo es detectar CUALQUIER dato que sirva para rellenar una solicitud de seguro de AUTO o HOGAR.

Tu respuesta debe ser ÚNICAMENTE:
1. La palabra: relevant (si contiene CUALQUIER dato útil para tarificación).
2. La palabra: irrelevant (si es solo ruido, saludos o temas ajenos).

## DATOS RELEVANTES (dejar pasar si contiene cualquiera)

### IDENTIFICACIÓN Y CONTACTO
DNI, NIE, CIF, Pasaporte, fecha de nacimiento, edad, fecha de carnet, email, teléfono, \
nombre, apellidos, profesión, estado civil.

### DATOS DE AUTO
Matrícula, marca, modelo, versión, cilindrada, CV, combustible, puertas, nuevo/segunda mano, \
fecha compra, valor, km anuales, uso particular/profesional, garaje, conductores ocasionales.

### DATOS DE HOGAR
Dirección completa, CP, población, provincia, tipo vivienda (piso/chalet/adosado/ático), \
propietario/inquilino, uso (habitual/segunda residencia), m², año construcción, reformas, \
valor continente/contenido, alarma, puerta blindada, joyas.

### HISTORIAL Y SEGURO ACTUAL
Compañía actual, antigüedad, siniestralidad pasada, vencimiento póliza, forma de pago.

### INTENCIÓN DE TARIFICAR
Cualquier mención a querer un seguro, tarificar, cotizar, presupuesto de auto o hogar.

## NO RELEVANTE (responder "irrelevant")
- Saludos vacíos: "Hola", "Buenos días", "¿Estás ahí?"
- Confirmaciones de espera: "Un momento", "Espera que lo miro"
- Siniestros ACTIVOS en curso: "La grúa no llega", "Quiero poner una reclamación"
- Ruido de transcripción: frases cortadas sin contexto

## REGLA DE ORO
Si el usuario responde con un dato suelto como "1990", "Gasolina", "Individual", \
"Sí, tiene alarma", "El 28001", SIEMPRE ES RELEVANTE (responde a pregunta previa del formulario).

## PROCESO DE DECISIÓN
Antes de responder, analiza internamente:
1. ¿Hay datos personales identificables?
2. ¿Hay intención de contratar/consultar un seguro?
3. ¿Se menciona póliza o historial?
4. ¿Hay datos sobre un bien asegurable (auto, inmueble)?
5. ¿Tiene relación con el mundo de los seguros?

Si al menos UNA es SÍ → "relevant"
Si TODAS son NO → "irrelevant"

Responde SOLO con "relevant" o "irrelevant"."""


EXTRACTOR_SYSTEM = """\
Eres un extractor de datos de seguros en tiempo real. \
Procesas fragmentos de transcripción de llamadas telefónicas y extraes datos estructurados.

### MEMORIA (Estado actual de la tarificación)
{{MEMORY}}

### INSTRUCCIONES
1. Si la MEMORIA tiene `ramo_activo`, extrae SOLO datos para ese ramo. No cambies el ramo.
2. Si la MEMORIA es "VACIO", detecta el ramo por contexto:
   - AUTO: mencionan coche, vehículo, auto, moto, matrícula, carnet de conducir, seguro de coche.
   - HOGAR: mencionan casa, piso, vivienda, hogar, alquiler, seguro de hogar/casa.
3. NUNCA inventes datos. Solo extrae lo mencionado explícitamente.
4. Campos sin dato van como cadena vacía "".

### NORMALIZACIÓN (OBLIGATORIO)
- Fechas → YYYY-MM-DD
- DNI → Mayúsculas sin espacios (ej: "12345678A")
- hombre/varón → "MASCULINO", mujer → "FEMENINO"
- casado/a → "CASADO", soltero/a → "SOLTERO", viudo/a → "VIUDO", divorciado/a → "DIVORCIADO"
- piso → "PISO_EN_ALTO", ático → "ATICO", chalet → "CHALET_O_VIVIENDA_UNIFAMILIAR", \
adosado → "CHALET_O_VIVIENDA_ADOSADA"
- vivienda habitual → "HABITUAL", segunda residencia → "SEGUNDA_RESIDENCIA"
- propia/propiedad → "PROPIEDAD", alquilada/alquiler → "ALQUILER"

### FORMATO DE RESPUESTA (JSON estricto)

Si ramo es AUTO:
{
  "ramo": "AUTO",
  "data": {
    "vehiculo": { "matricula": "" },
    "tomador": {
      "nombre": "", "apellido1": "", "apellido2": "", "dni": "",
      "fecha_nacimiento": "", "fecha_carnet": "", "sexo": "",
      "estado_civil": "", "codigo_postal": ""
    },
    "poliza_actual": { "numero_poliza": "", "company": "", "fecha_efecto": "" }
  },
  "datos_detectados": ["tomador.nombre", "tomador.dni"]
}

Si ramo es HOGAR:
{
  "ramo": "HOGAR",
  "data": {
    "tomador": {
      "nombre": "", "apellido1": "", "apellido2": "", "dni": "",
      "fecha_nacimiento": "", "sexo": "", "estado_civil": "", "codigo_postal": ""
    },
    "vivienda": {
      "nombre_via": "", "numero_calle": "", "piso": "", "puerta": "",
      "tipo_vivienda": "", "uso_vivienda": "", "regimen_ocupacion": "",
      "numero_personas_vivienda": ""
    },
    "poliza_actual": { "fecha_efecto": "" }
  },
  "datos_detectados": ["tomador.nombre", "vivienda.tipo_vivienda"]
}

Si no se detecta ramo:
{ "ramo": null, "data": {}, "datos_detectados": [] }

IMPORTANTE:
- `datos_detectados` debe listar SOLO los campos para los que has extraído un valor NO vacío \
del mensaje actual (formato "seccion.campo").
- Rellena los campos extraídos con sus valores normalizados. Los demás van como "".
- Responde ÚNICAMENTE con el JSON, sin texto adicional."""


class ZoaInsuranceAgent:
    """
    Agent that classifies and extracts insurance data from call transcriptions,
    then creates or updates tarification sheets via ZoaAIChat.

    Pipeline: classify (relevant/irrelevant) → extract data → create/update sheet.
    """

    def __init__(self, token=None, api_base=None):
        self.ai_chat = ZoaAIChat(token, api_base)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # ── Public API ────────────────────────────────────────────────────────────

    def process(self, request_json):
        """
        Main pipeline: classify → extract → create/update tarification sheet.

        Expected fields:
        - user_id  (str, required)
        - call_id  (str, required)
        - message  (str, required): Buffered/concatenated transcription text.
        - memory   (dict, optional): Current tarification state, or empty/null.
        """
        message = request_json.get("message", "").strip()
        user_id = request_json.get("user_id")
        call_id = request_json.get("call_id")
        memory = request_json.get("memory") or {}

        if not message:
            return {"error": "El campo 'message' es obligatorio."}, 400
        if not user_id:
            return {"error": "El campo 'user_id' es obligatorio."}, 400
        if not call_id:
            return {"error": "El campo 'call_id' es obligatorio."}, 400
        if not self.openai_api_key:
            return {"error": "OPENAI_API_KEY no configurada en el entorno."}, 500

        try:
            logger.info("[INSURANCE_AGENT] Classifying message for call_id=%s", call_id)
            is_relevant = self._classify(message)

            if not is_relevant:
                logger.info("[INSURANCE_AGENT] Message irrelevant, skipping")
                return self._response("irrelevant", memory), 200

            logger.info("[INSURANCE_AGENT] Message relevant, extracting data")
            extraction = self._extract(message, memory)

            ramo = extraction.get("ramo") or memory.get("ramo_activo")
            extracted_data = extraction.get("data", {})
            datos_detectados = extraction.get("datos_detectados", [])

            if not ramo:
                logger.info("[INSURANCE_AGENT] No ramo detected, waiting")
                return self._response(
                    "waiting", memory, datos_detectados=datos_detectados
                ), 200

            is_new = not memory or not memory.get("ramo_activo")

            if is_new:
                return self._handle_create(
                    ramo, extracted_data, datos_detectados, user_id, call_id
                )
            return self._handle_update(
                memory, extracted_data, datos_detectados, user_id, call_id
            )

        except Exception as e:
            logger.exception("[INSURANCE_AGENT] Error processing message")
            return {"error": f"Error en el agente de seguros: {str(e)}"}, 500

    # ── Internal Pipeline Steps ───────────────────────────────────────────────

    def _classify(self, message):
        result = self._call_llm(CLASSIFIER_SYSTEM, message)
        return result.strip().lower() != "irrelevant"

    def _extract(self, message, memory):
        memory_str = json.dumps(memory, ensure_ascii=False, indent=2) if memory else "VACIO"
        system = EXTRACTOR_SYSTEM.replace("{{MEMORY}}", memory_str)
        raw = self._call_llm(system, message, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("[INSURANCE_AGENT] Failed to parse extractor response: %s", raw)
            return {"ramo": None, "data": {}, "datos_detectados": []}

    def _handle_create(self, ramo, extracted_data, datos_detectados, user_id, call_id):
        logger.info("[INSURANCE_AGENT] Creating new %s sheet", ramo)
        template = copy.deepcopy(AUTO_TEMPLATE if ramo == "AUTO" else HOGAR_TEMPLATE)
        new_memory = self._consolidate(template, extracted_data)
        new_memory["ramo_activo"] = ramo
        new_memory["complete"] = self._is_complete(ramo, new_memory)

        sheet_data = self._build_sheet_data(ramo, new_memory)
        api_result, _ = self.ai_chat.create({
            "user_id": user_id,
            "body_type": "auto_sheet" if ramo == "AUTO" else "home_sheet",
            "call_id": call_id,
            "complete": str(new_memory["complete"]).lower(),
            "data": sheet_data
        })

        return self._response(
            "created", new_memory, ramo, datos_detectados, api_result
        ), 200

    def _handle_update(self, memory, extracted_data, datos_detectados, user_id, call_id):
        ramo = memory["ramo_activo"]

        if not datos_detectados:
            logger.info("[INSURANCE_AGENT] No new data, skipping update")
            return self._response("waiting", memory, ramo), 200

        logger.info("[INSURANCE_AGENT] Updating %s sheet: %s", ramo, datos_detectados)
        new_memory = self._consolidate(memory, extracted_data)
        new_memory["complete"] = self._is_complete(ramo, new_memory)

        sheet_data = self._build_sheet_data(ramo, new_memory)
        api_result, _ = self.ai_chat.update({
            "user_id": user_id,
            "body_type": "auto_sheet" if ramo == "AUTO" else "home_sheet",
            "call_id": call_id,
            "complete": str(new_memory["complete"]).lower(),
            "data": sheet_data
        })

        return self._response(
            "updated", new_memory, ramo, datos_detectados, api_result
        ), 200

    # ── LLM Communication ─────────────────────────────────────────────────────

    def _call_llm(self, system_prompt, user_message, json_mode=False):
        import openai

        client = openai.OpenAI(api_key=self.openai_api_key)
        kwargs = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    # ── Data Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _consolidate(base, new_data):
        """Merge new extracted data into base, only overwriting with non-empty values."""
        result = copy.deepcopy(base)
        for key, value in new_data.items():
            if key in ("complete", "ramo_activo"):
                continue
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                for fk, fv in value.items():
                    if fv and str(fv).strip():
                        result[key][fk] = fv
            elif value and str(value).strip():
                result[key] = value
        return result

    @staticmethod
    def _build_sheet_data(ramo, memory):
        """Extract the data payload (without metadata) for the API call."""
        if ramo == "AUTO":
            return {
                "vehiculo": memory.get("vehiculo", {"matricula": ""}),
                "tomador": memory.get("tomador", {}),
                "poliza_actual": memory.get("poliza_actual", {})
            }
        return {
            "tomador": memory.get("tomador", {}),
            "vivienda": memory.get("vivienda", {}),
            "poliza_actual": memory.get("poliza_actual", {})
        }

    @staticmethod
    def _is_complete(ramo, memory):
        required = AUTO_REQUIRED_FIELDS if ramo == "AUTO" else HOGAR_REQUIRED_FIELDS
        return all(ZoaInsuranceAgent._get_nested(memory, p) for p in required)

    @staticmethod
    def _get_pending(ramo, memory):
        if not ramo:
            return []
        required = AUTO_REQUIRED_FIELDS if ramo == "AUTO" else HOGAR_REQUIRED_FIELDS
        return [p for p in required if not ZoaInsuranceAgent._get_nested(memory, p)]

    @staticmethod
    def _get_nested(obj, dot_path):
        for key in dot_path.split("."):
            if isinstance(obj, dict):
                obj = obj.get(key, "")
            else:
                return ""
        return obj

    # ── Response Builder ──────────────────────────────────────────────────────

    def _response(self, status, memory, ramo=None, datos_detectados=None, api_response=None):
        ramo = ramo or memory.get("ramo_activo")
        resp = {
            "status": status,
            "ramo": ramo,
            "memory": memory,
            "datos_detectados": datos_detectados or [],
            "pendientes": self._get_pending(ramo, memory) if ramo else []
        }
        if api_response is not None:
            resp["api_response"] = api_response
        return resp
