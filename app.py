from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
import os, requests
import pandas as pd

# from dotenv import load_dotenv

# load_dotenv()

app = Flask(__name__)
CORS(app)

# Obtener variables de entorno
username = os.environ.get("MONGODB_USERNAME")
password = os.environ.get("MONGODB_PASS")

if not username or not password:
    raise EnvironmentError("Faltan MONGODB_USERNAME o MONGODB_PASS")

# Construir URI
uri = f"mongodb+srv://{username}:{password}@watsonxtest.6u16lup.mongodb.net/?retryWrites=true&w=majority&appName=WatsonxTest"

WATSONX_API_KEY = os.environ.get("WATSONX_API_KEY")
WATSONX_PROJECT_ID = os.environ.get("WATSONX_PROJECT_ID")
FOUNDATION_MODEL = "mistralai/mistral-large"
# FOUNDATION_MODEL = "meta-llama/llama-3-3-70b-instruct"


WATSONX_URL = f"https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2024-05-01"

ML_MODEL_URL = "https://us-south.ml.cloud.ibm.com/ml/v4/deployments/deteccionfraudet49c2w/predictions?version=2021-05-01"

# Crear cliente MongoDB
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["watsonxDemoDB"]
collection = db["diagnosticos"]

descripcion_variables = """
    Month: Mes en que se presentó el siniestro.
    WeekOfMonth: Semana del mes en que ocurrió el siniestro.
    DayOfWeek: Día de la semana en que ocurrió el siniestro.
    Make: Fabricante del vehículo involucrado.
    AccidentArea: Zona donde ocurrió el accidente (urbana o rural).
    DayOfWeekClaimed: Día de la semana en que se procesó el reclamo.
    MonthClaimed: Mes en que se procesó el reclamo.
    WeekOfMonthClaimed: Semana del mes en que se procesó el reclamo.
    Sex: Género del asegurado.
    MaritalStatus: Estado civil del asegurado.
    Age: Edad del asegurado.
    Fault: Indica si el asegurado fue responsable del accidente.
    PolicyType: Tipo de póliza contratada.
    VehicleCategory: Categoría del vehículo (sedán, SUV, etc.).
    VehiclePrice: Precio del vehículo.
    PolicyNumber: Identificador único de la póliza.
    RepNumber: Identificador del representante de seguros.
    Deductible: Monto deducible que paga el asegurado antes del seguro.
    DriverRating: Calificación del conductor basada en su historial.
    Days_Policy_Accident: Días entre la emisión de la póliza y el accidente.
    Days_Policy_Claim: Días entre la emisión de la póliza y el reclamo.
    PastNumberOfClaims: Número de reclamos previos del asegurado.
    AgeOfVehicle: Edad del vehículo involucrado.
    AgeOfPolicyHolder: Edad del asegurado.
    PoliceReportFiled: Si se presentó reporte policial del accidente.
    WitnessPresent: Si hubo testigos en el accidente.
    AgentType: Tipo de agente de seguros (interno o externo).
    NumberOfSuppliments: Número de documentos o reclamos adicionales.
    AddressChange_Claim: Si hubo cambio de domicilio al momento del reclamo.
    NumberOfCars: Número de vehículos asegurados bajo la póliza.
    Year: Año en que se realizó o procesó el reclamo.
    BasePolicy: Tipo base de la póliza (Responsabilidad Civil, Colisión, Todo Riesgo).
"""


def obtener_token_ibm(api_key):
    url = "https://iam.cloud.ibm.com/identity/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key
    }

    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Error al obtener token: {response.text}")

def call_to_watsonx_api(prompt):
    # Construir prompt
    token = obtener_token_ibm(WATSONX_API_KEY)
    # Headers Watsonx
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Payload Watsonx
    payload = {
        "model_id": FOUNDATION_MODEL,
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "repetition_penalty": 1.1,
            "max_new_tokens": 2100,
            "min_new_tokens": 1000
        },
        "project_id": WATSONX_PROJECT_ID
    }

    response = requests.post(WATSONX_URL, headers=headers, json=payload)
    result = response.json()

    if response.status_code != 200:
        return {"result": False, "message": result}

    generated_text = result.get("results", [{}])[0].get("generated_text", "")
    return {"result": True, "message": generated_text}
        
def is_one(value):
    if value == 1:
        return 1
    return 0

def is_zero(value):
    if value == 0:
        return 1
    return 0

# Ruta para insertar un documento
@app.route("/diagnosticos", methods=["POST"])
def insertar_diagnostico():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se proporcionó ningún dato"}), 400
    try:
        result = collection.insert_one(data)
        return jsonify({
            "message": "Documento insertado",
            "id": str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ruta para obtener todos los documentos
@app.route("/diagnosticos", methods=["GET"])
def obtener_diagnosticos():
    try:
        documentos = list(collection.find())
        result = [{**doc, "_id": str(doc["_id"])} for doc in collection.find()]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/diagnosticos/<id>", methods=["GET"])
def get_diagnostico_by_id(id):
    try:
        doc = collection.find_one({"_id": ObjectId(id)})
        if not doc:
            return jsonify({"error": "Documento no encontrado"}), 404
        doc["_id"] = str(doc["_id"])
        return jsonify(doc)
    except Exception as e:
        return jsonify({"error": "ID inválido o error interno", "details": str(e)}), 400

@app.route("/diagnosticos/analizar", methods=["POST"])
def analizar_diagnostico():
    try:
        data = request.get_json()
        doc_id = data.get("id")

        if not doc_id:
            return jsonify({"error": "Falta el campo 'id'"}), 400

        doc = collection.find_one({"_id": ObjectId(doc_id)})

        if not doc:
            return jsonify({"error": "Documento no encontrado"}), 404

        # Construir prompt
        prompt = (
            f"Instrucción: Genera un diagnóstico consultivo de TI para una empresa del sector {doc.get('sector', 'desconocido')}.\n"
            f"Contexto: Su mayor dolor de cabeza es: {doc.get('painPoint', 'No especificado')}.\n"
            "Objetivo: Proporciona una recomendación concreta de consultoría especializada en Data & AI."
            "Formato: Retorna tu respuesta en un formato markdown."
        )
        
        watsonxai_answer = call_to_watsonx_api(prompt)

        if(watsonxai_answer["result"] == False):
            return jsonify({"error": watsonxai_answer["message"]}), 500

        # Actualizar documento
        collection.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"diagnostico": watsonxai_answer["message"]}}
        )

        return jsonify({"diagnostico": watsonxai_answer["message"]}), 200

    except Exception as e:
        return jsonify({"error": "Error interno", "details": str(e)}), 500

@app.route("/model-predict/<id>", methods=["GET"])
def model_predict(id):
    try:
        current_dir = os.getcwd()
        df = pd.read_csv(os.path.join(current_dir, "data_predicted.csv"), delimiter="|")
        actual_record = df.loc[df["id"] == int(id)]
        return jsonify({
            "prediction": int(actual_record.iloc[0]['isFraud']),
            "confidence": float(round(actual_record.iloc[0]['confidence_level']*100, 2)),
            }), 200
    
    except Exception as e:
        return jsonify({"error": "Error interno", "details": str(e)}), 500

@app.route("/model-analyze/<id>", methods=["GET"])
def model_analyze(id): 
    try:
        if(int(id) > 58): return jsonify({"error": "Error interno", "details": "No existe ese caso"}), 404
        current_dir = os.getcwd()
        df = pd.read_csv(os.path.join(current_dir, "data_predicted.csv"), delimiter="|")
        data = df.loc[df["id"] == int(id)]
        pred = data.iloc[0]["isFraud"]
        conf = float(round( data.iloc[0]["confidence_level"]*100, 2 ))
        data_usada = data.iloc[0][1:-3]
        if(pred == 1):
            prompt = f"""# INSTRUCCIONES DEL SISTEMA
                Eres un analista senior de riesgos y fraudes en seguros con 15+ años de experiencia. Tu especialidad es interpretar modelos de ML y generar insights accionables para equipos de negocio.

                ## CONTEXTO DEL ANÁLISIS
                **Variables del modelo:** {descripcion_variables}
                **Datos del caso:** {str(data_usada.to_dict())}
                **resultado del analisis:** "fraude"
                **porcentaje de probabilidad de fraude según el modelo:** {conf}
                **La probabilidad ya está calculada correctamente, no necesitas multiplicarla por 100.**

                ## ESTRUCTURA REQUERIDA DE RESPUESTA
                Proporciona tu análisis en exactamente estas secciones usando formato Markdown:

                ### 🔍 Resumen Ejecutivo
                - Nivel de riesgo: [ALTO/MEDIO/BAJO]
                - Probabilidad de fraude estimada (usa el valor proporcionado)
                - 2-3 puntos clave más críticos

                ### 📊 Análisis de Patrones Críticos  
                - Identifica los 3-4 factores más relevantes del caso
                - Explica cómo cada factor contribuye al riesgo
                - Usa comparativas: "Este valor es X% superior al promedio normal"

                ### ⚠️ Señales de Alerta Identificadas
                - Lista específica de red flags encontrados
                - Contexto de por qué cada señal es preocupante
                - Patrones típicos de fraude que coinciden

                ### 💡 Hipótesis de Fraude
                - 2-3 escenarios más probables de fraude
                - Lógica de negocio detrás de cada hipótesis
                - Indicadores que refuerzan cada teoría

                ### 🎯 Recomendaciones Inmediatas
                - Acciones específicas a tomar (investigación adicional, validaciones, etc.)
                - Priorización: qué revisar primero
                - Recursos necesarios para investigación

                ## CRITERIOS DE CALIDAD
                - Máximo 1000 palabras total
                - Usa datos específicos del caso, no generalidades
                - Incluye métricas numéricas cuando sea posible
                - Enfoque práctico y accionable
                - Tono profesional pero accesible

                Procede con el análisis:"""
        else:
            prompt = f"""# INSTRUCCIONES DEL SISTEMA
                Eres un analista senior de riesgos y fraudes en seguros con 15+ años de experiencia. Tu especialidad es interpretar modelos de ML y generar insights accionables para equipos de negocio.

                ## CONTEXTO DEL ANÁLISIS
                **Variables del modelo:** {descripcion_variables}
                **Datos del caso:** {str(data_usada.to_dict())}
                **Resultado del análisis:** "no fraude"
                **Porcentaje de probabilidad de fraude según el modelo:** {conf}
                **La probabilidad ya está calculada correctamente, no necesitas multiplicarla por 100.**

                ## ESTRUCTURA REQUERIDA DE RESPUESTA
                Proporciona tu análisis en exactamente estas secciones usando formato Markdown:

                ### 🔍 Resumen Ejecutivo
                - Nivel de riesgo: [MUY BAJO / BAJO / MODERADO]
                - Probabilidad de fraude estimada (usa el valor proporcionado)
                - 2-3 factores protectores principales

                ### 📊 Factores que Reducen el Riesgo  
                - Identifica los 3-4 factores clave que disminuyen la probabilidad de fraude
                - Explica cómo cada uno contribuye a la baja probabilidad
                - Compara los valores con promedios históricos o perfiles de alto riesgo

                ### ✅ Indicadores de Comportamiento Consistente
                - Describe patrones que sugieren consistencia, normalidad o baja sospecha
                - Contextualiza por qué estos factores generan confianza en el modelo
                - Incluye patrones que típicamente no se asocian con fraude

                ### 💡 Aprendizajes del Caso
                - Lecciones o patrones detectados que podrían reforzar futuras políticas antifraude
                - Comportamientos ejemplares del asegurado que reducen el riesgo
                - Oportunidades para ajustar reglas de negocio basadas en el caso

                ### 🎯 Recomendaciones Preventivas
                - Acciones preventivas sugeridas (educación, monitoreo continuo, incentivos)
                - Buenas prácticas de seguimiento para mantener el bajo riesgo
                - Recursos que podrían optimizar la gestión del cliente

                ## CRITERIOS DE CALIDAD
                - Máximo 1000 palabras total
                - Usa datos específicos del caso, no generalidades
                - Incluye métricas numéricas cuando sea posible
                - Enfoque práctico, preventivo y de aprendizaje
                - Tono profesional pero accesible

                Procede con el análisis:"""

        generated_text = call_to_watsonx_api(prompt)
        if(generated_text["result"] == False):
           return jsonify({
                "Error": generated_text["message"]
            }), 500

        return jsonify({
            "analisis_modelo": generated_text["message"]
            }), 200

        # return jsonify({"result": "result"})
    except Exception as e:
        return jsonify({"error": "Error interno", "details": str(e)}), 500

@app.route("/model-predict", methods=["GET"])
def model_dummy_predict():
    try:        
        current_dir = os.getcwd()
        df = pd.read_csv(os.path.join(current_dir, "data_predicted.csv"), delimiter='|')
       
        tasa_fraude = sum(map(lambda x: 0 if(x == 0) else 1, df["isFraud"].tolist())) / len(df)
        
        prompt = f"""Actúa como un consultor senior en detección de fraude de seguros. Analiza estos {len(df)} registros de reclamos (tasa de fraude: {(tasa_fraude * 100):.1f}%) para generar insights estratégicos destinados a líderes de agencias y empresas de seguros.

            **CONTEXTO DE VARIABLES:**
            {descripcion_variables}

            **DATOS PARA ANÁLISIS:**
            {str(df.to_dict())}

            ---

            ## 📊 ANÁLISIS EJECUTIVO REQUERIDO

            ### 1. **INDICADORES CLAVE DE RIESGO (KRIs)**
            - Identifica las TOP 5 variables más predictivas de fraude con su poder discriminatorio
            - Calcula umbrales críticos para alertas tempranas

            ### 2. **SEGMENTACIÓN ESTRATÉGICA DE RIESGO**
            - **Perfil Alto Riesgo**: Características y prevalencia (% de cartera)
            - **Perfil Medio Riesgo**: Factores de escalamiento
            - **Perfil Bajo Riesgo**: Benchmarks para comparación

            ### 3. **PATRONES OPERACIONALES CRÍTICOS**
            - **Timing Fraudulento**: Análisis de días entre póliza-accidente-reclamo
            - **Comportamientos Sospechosos**: Patrones en documentación, testigos, reportes policiales
            - **Correlaciones Geográficas y Temporales**: Zonas y períodos de mayor riesgo
            - **Perfiles de Agentes**: Identificación de comportamientos atípicos por tipo de agente

            ### 4. **PLAN DE ACCIÓN ESTRATÉGICO**
            - **Inmediato (0-30 días)**: 3 acciones de implementación rápida
            - **Corto plazo (1-6 meses)**: Mejoras en procesos y sistemas
            - **Largo plazo (6+ meses)**: Transformación digital y capacitación
            - Incluye métricas de éxito y responsible owners

            ---

            ## ESPECIFICACIONES DE ENTREGA

            **FORMATO:**
            - Respuesta en Markdown optimizado para dashboard web
            - Tablas para datos cuantitativos
            - Gráficos de texto (ASCII) cuando sea relevante
            - Secciones colapsables con detalles técnicos

            **ESTILO:**
            - Lenguaje ejecutivo directo y accionable
            - Cuantifica todo impacto en términos financieros
            - Prioriza recomendaciones por ROI potencial
            - Incluye timelines realistas de implementación

            **MÉTRICAS CLAVE A REPORTAR:**
            - Tasa de detección actual vs. potencial mejorada
            - Reducción estimada de pérdidas por fraude
            - Tiempo promedio de detección actual vs. objetivo
            - Precisión del modelo por segmento de riesgo

            Genera un reporte que permita a los líderes tomar decisiones informadas sobre inversiones en antifraude y optimización de procesos."""


        generated_text = call_to_watsonx_api(prompt)
        if(generated_text["result"] == False):
           return jsonify({
                "Error": generated_text["message"]
            }), 500
        
        response_dict = {
            "results": df["isFraud"].tolist(),
            "confidences": list( map( lambda x: float( round( x*100 , 2) ), df["confidence_level"].tolist() ) ),
            "analisis_modelo": generated_text["message"]
        }
        
        return jsonify(response_dict), 200

    except Exception as e:
        print(e)
        return jsonify({"error": "Error interno", "details": str(e)}), 500


## Function for special case
# def model_predict(id):
#     try:
#         mltoken = obtener_token_ibm(WATSONX_API_KEY)
#         current_dir = os.getcwd()
#         df = pd.read_csv(os.path.join(current_dir, "fraud_detection.csv"))
#         header = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + mltoken}

#         # NOTE:  manually define and pass the array(s) of values to be scored in the next line
#         payload_scoring = {"input_data": [
#             {
#                 "fields": df.columns.to_numpy().tolist(),
#                 "values": [df.iloc[int(id)].tolist()]
#             }
#         ]}
#         response_scoring = requests.post(ML_MODEL_URL, json=payload_scoring,
#         headers=header)

#         # print("Scoring response")
#         result = response_scoring.json()["predictions"][0]["values"][0][0]
#         confidence_level = response_scoring.json()["predictions"][0]["values"][0][1][0] if result == 0 else  response_scoring.json()["predictions"][0]["values"][0][1][1]
#         return jsonify({
#             "result": result,
#             "confidence": confidence_level*100,
#             }), 200
    
#     except Exception as e:
#         return jsonify({"error": "Error interno", "details": str(e)}), 500



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)


# vehicleprice_label = {'more than 69000': 1, '20000 to 29000': 0,  '30000 to 39000': 0, 'less than 20000': 1, '40000 to 59000': 1, '60000 to 69000': 0}
# ageofvehicle_label = {'new': 2, '2 years': 0, '3 years': 2, '4 years': 2, '5 years': 1, '6 years': 1, '7 years': 0, 'more than 7': 0}
# basepolicy_label = {'Liability': 0, 'Collision': 1, 'All Perils': 2}


# def categorize_age(age):
#     if age <= 20:
#         return 0
#     elif age <= 40:
#         return 1
#     elif age <= 65:
#         return 2
#     else:
#         return 3


# 'AccidentArea'
# 'AddressChange_Claim_no change'
# 'Age'
# 'AgeOfPolicyHolder_26 to 30'
# 'AgeOfPolicyHolder_31 to 35'
# 'AgeOfPolicyHolder_36 to 40'
# 'AgeOfPolicyHolder_41 to 50'
# 'AgeOfPolicyHolder_51 to 65'
# 'AgeOfVehicle'
# 'BasePolicy'
# 'Deductible_400'
# 'DriverRating'
# 'Fault'
# 'Make_Chevrolet'
# 'Make_Honda'
# 'Make_Mazda'
# 'Make_Pontiac'
# 'Make_Toyota'
# 'MaritalStatus_Married'
# 'MaritalStatus_Single'
# 'MonthClaimed_Apr'
# 'MonthClaimed_Aug'
# 'MonthClaimed_Dec'
# 'MonthClaimed_Feb'
# 'MonthClaimed_Jan'
# 'MonthClaimed_Jul'
# 'MonthClaimed_Jun'
# 'MonthClaimed_Mar'
# 'MonthClaimed_May'
# 'MonthClaimed_Nov'
# 'MonthClaimed_Oct'
# 'MonthClaimed_Sep'
# 'NumberOfSuppliments_3 to 5'
# 'NumberOfSuppliments_more than 5'
# 'NumberOfSuppliments_none'
# 'PastNumberOfClaims_1'
# 'PastNumberOfClaims_2 to 4'
# 'PastNumberOfClaims_more than 4'
# 'PastNumberOfClaims_none'
# 'PolicyType_Sedan - Collision'
# 'PolicyType_Sedan - Liability'
# 'RepNumber_1'
# 'RepNumber_2'
# 'RepNumber_3'
# 'RepNumber_4'
# 'RepNumber_5'
# 'RepNumber_6'
# 'RepNumber_7'
# 'RepNumber_8'
# 'RepNumber_9'
# 'RepNumber_10'
# 'RepNumber_11'
# 'RepNumber_12'
# 'RepNumber_13'
# 'RepNumber_14'
# 'RepNumber_15'
# 'RepNumber_16'
# 'VehicleCategory_Sedan'
# 'VehiclePrice'
# 'Year_1994'
# 'Year_1995'
# 'Year_1996'

# AccidentArea: The area where the accident occurred (e.g., urban, rural).
# AddressChange_Claim: Indicates whether the address of the policyholder was changed at the time of the claim, categorized into ranges.
# Age: The age of the policyholder.
# AgeOfPolicyHolder: The age of the policyholder.
# AgeOfVehicle: The age of the vehicle involved in the claim.
# BasePolicy: The base policy type (e.g., Liability, Collision, All Perils).
# Deductible: The amount that the policy holder must pay out of pocket before the insurance company pays the remaining costs.
# DriverRating: The rating of the driver, often based on driving history or other factors.
# Fault: Indicates whether the policyholder was at fault in the accident.
# Make: The manufacturer of the vehicle involved in the claim.
# MaritalStatus: The material status of the policyholder.
# MonthClaimed: The month in which the insurance claim was processed.
# NumberOfSuppliments: The number of supplementary documents or claims related to the main claim, categorized into ranges.
# PastNumberOfClaims: The number of claims previously made by the policyholder.
# PolicyType: The type of insurance policy (e.g., comprehensive, third-party).
# RepNumber: The unique identifier for the insurance representative handling the claim.
# VehicleCategory: The category of the vehicle (e.g., sedan, SUV).
# VehiclePrice: The price of vehicle.
# Year: The year in which the claim was made or processed.