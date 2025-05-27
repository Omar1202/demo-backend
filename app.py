from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
import os, requests

from dotenv import load_dotenv

load_dotenv()

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
FOUNDATION_MODEL = "ibm/granite-13b-instruct-v2"

WATSONX_URL = f"https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2024-05-01"

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
        )
        token = obtener_token_ibm(WATSONX_API_KEY)
        # Headers Watsonx
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Payload Watsonx
        payload = {
            "model_id": "ibm/granite-3-8b-instruct",
            "input": prompt,
            "parameters": {
                "decoding_method": "sample",
                "temperature": 0.7,
                "repetition_penalty": 1.1,
                "max_new_tokens": 500
            },
            "project_id": WATSONX_PROJECT_ID
        }

        response = requests.post(WATSONX_URL, headers=headers, json=payload)
        result = response.json()

        if response.status_code != 200:
            return jsonify({"error": "Error al consultar Watsonx.ai", "details": result}), 500

        generated_text = result.get("results", [{}])[0].get("generated_text", "")
        print("Raw response:", result)

        # Actualizar documento
        collection.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"diagnostico": generated_text}}
        )

        return jsonify({"diagnostico": generated_text}), 200

    except Exception as e:
        return jsonify({"error": "Error interno", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
