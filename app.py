from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
import os, requests
import pandas as pd
import numpy as np

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
# FOUNDATION_MODEL = "mistralai/mistral-large"
FOUNDATION_MODEL = "meta-llama/llama-3-3-70b-instruct"


WATSONX_URL = f"https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2024-05-01"

ML_MODEL_URL = "https://us-south.ml.cloud.ibm.com/ml/v4/deployments/deteccionfraudet49c2w/predictions?version=2021-05-01"

# Crear cliente MongoDB
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["watsonxDemoDB"]
collection = db["diagnosticos"]


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
            "min_new_tokens": 2000
        },
        "project_id": WATSONX_PROJECT_ID
    }

    response = requests.post(WATSONX_URL, headers=headers, json=payload)
    result = response.json()

    if response.status_code != 200:
        return jsonify({"error": "Error al consultar Watsonx.ai", "details": result}), 500

    generated_text = result.get("results", [{}])[0].get("generated_text", "")
    return generated_text

def generate_dummy_data_from_csv():
    with open("./fraud_detection.csv", 'r') as file:
        # Read the entire content of the file as a single string
        dummy_data = file.read()
    
    prompt = (
            f"Instrucción: Genera un conjunto de datos dummy para un modelo de detección de fraudes, toma como ejemplo el siguiente conjunto de datos: {dummy_data}.\n"
            f"Contexto: Este ejercicio es para una demostración en un evento de aseguradoras.\n"
            "Objetivo: Proporciona un conjunto de datos para analizar con un modelo de machine learning, tomando como base el contexto que se te dió. "
            "Formato: Retorna tu respuesta en un formato JSON que contenga un campo, se llamará 'values' y contendrá una lista de listas con todos los ejemplos que generes. Genera 10 ejemplos."
        )
    generated_text = call_to_watsonx_api(prompt)
    return generated_text
        
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
        
        generated_text = call_to_watsonx_api(prompt)

        # Actualizar documento
        collection.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"diagnostico": generated_text}}
        )

        return jsonify({"diagnostico": generated_text}), 200

    except Exception as e:
        return jsonify({"error": "Error interno", "details": str(e)}), 500

@app.route("/model-predict", methods=["GET"])
def model_dummy_predict():
    try:
        mltoken = obtener_token_ibm(WATSONX_API_KEY)
        
        df = pd.read_csv("app/fraud_detection_complete.csv")
        summary = {}
        for column in df.columns:
            summary[column] = {
                "mean": round(df[column].mean(), 3),
                "std": round(df[column].std(), 3),
                "min": round(df[column].min(), 3),
                "max": round(df[column].max(), 3)
            }
        
        header = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + mltoken}

        # NOTE:  manually define and pass the array(s) of values to be scored in the next line
        payload_scoring = {"input_data": [
            {
                "fields": df.columns.to_numpy().tolist(),
                "values": df.values.tolist()
            }
        ]}

        response_scoring = requests.post(ML_MODEL_URL, json=payload_scoring,
        headers=header)

        print("Scoring response")
        response = response_scoring.json()["predictions"][0]["values"]
        # print(response)
        classes_per_prediction = {
            0: sum( list( map(lambda x: is_zero(x[0]), response) ) ),
            1: sum( list( map(lambda x: is_one(x[0]), response) ) ),
        }

        prompt = f"""
        Actúa como un analista experto de riesgos y fraudes en seguros.

        Se te proporciona un resumen estadístico de las variables de entrada de un modelo de detección de fraude.
        El número de casos analizados fue: {len(df)} y los resultados fueron: casos detectados como fraude: {classes_per_prediction[1]}, casos detectados como no fraude: {classes_per_prediction[0]}
        Tu tarea es:

        - Analizar los patrones observados.
        - Identificar posibles factores de riesgo asociados al fraude.
        - Generar hipótesis razonables de por qué ciertos valores o comportamientos están relacionados con fraude.
        - Proponer recomendaciones de negocio basadas en el análisis.
        - Considerar posibles sesgos o limitaciones que pudiera tener el modelo.

        IMPORTANTE: Devuelve tu análisis utilizando formato Markdown, para que pueda ser renderizado en un sitio web.

        A continuación el resumen estadístico:
        """

        for feature, stats in summary.items():
            prompt += f"\nFeature: {feature}\n"
            prompt += f"- Media: {stats['mean']}\n"
            prompt += f"- Desviación estándar: {stats['std']}\n"
            prompt += f"- Valor mínimo: {stats['min']}\n"
            prompt += f"- Valor máximo: {stats['max']}\n"

        generated_text = call_to_watsonx_api(prompt)

        return jsonify({
            "deteccion_results": classes_per_prediction,
            "analisis_modelo": generated_text
            }), 200

    except Exception as e:
        return jsonify({"error": "Error interno", "details": str(e)}), 500



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
