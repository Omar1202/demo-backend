# import pandas as pd
# from random import randint, sample
# import os, requests

# WATSONX_API_KEY = os.environ.get("WATSONX_API_KEY")

# ML_MODEL_URL = "https://us-south.ml.cloud.ibm.com/ml/v4/deployments/deteccionfraudet49c2w/predictions?version=2021-05-01"

# def obtener_token_ibm(api_key):
#     url = "https://iam.cloud.ibm.com/identity/token"
#     headers = {
#         "Content-Type": "application/x-www-form-urlencoded",
#     }
#     data = {
#         "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
#         "apikey": api_key
#     }

#     response = requests.post(url, headers=headers, data=data)

#     if response.status_code == 200:
#         return response.json()["access_token"]
#     else:
#         raise Exception(f"Error al obtener token: {response.text}")


# def model_predict():
#     try:
#         mltoken = obtener_token_ibm(WATSONX_API_KEY)
#         current_dir = os.getcwd()
#         df = pd.read_csv(os.path.join(current_dir, "fraud_detection_complete.csv"))
#         header = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + mltoken}

#         # NOTE:  manually define and pass the array(s) of values to be scored in the next line
#         payload_scoring = {"input_data": [
#             {
#                 "fields": df.columns.to_numpy().tolist(),
#                 "values": df.values.tolist()
#             }
#         ]}
#         response_scoring = requests.post(ML_MODEL_URL, json=payload_scoring,
#         headers=header)
#         results = response_scoring.json()["predictions"][0]["values"]
#         print( sum(map(lambda x: 1 if x[0] == 1 and x[1][1] > 0.7 else 0, results)) )

#         # print("Scoring response")
#         # results = [res[0] for res in response_scoring.json()["predictions"][0]["values"]]
#         # confidence_level = [confidence[1][1] for confidence in response_scoring.json()["predictions"][0]["values"]]
#         # df2 = pd.read_csv(os.path.join(current_dir, "data_test_for_page_detalle_nuevo.csv"), delimiter='|')
#         # df2["confidence_level"] = confidence_level
#         # df2.to_csv("data_test_for_page_detalle_nuevo.csv", sep="|")
        
    
#     except Exception as e:
#         print(e)

# model_predict()

# # # Cargar los datos
# # df_detalles = pd.read_csv("data_detalle_completo_predicted.csv", delimiter="|")
# # df_encoded = pd.read_csv("fraud_detection_complete.csv")

# # # Crear listas para almacenar los índices seleccionados
# # indices_seleccionados = []

# # # Generar 50 índices únicos aleatorios
# # filtered_positive = df_detalles.loc[df_detalles['isFraud'] == 1]
# # my_list = filtered_positive["id"].tolist()
# # num_to_select = randint(25,30)
# # positive_elements_indexes = sample(my_list, num_to_select)

# # num_to_select_2 = randint(25,30)
# # while len(indices_seleccionados) < num_to_select_2:
# #     random_number = randint(0, len(df_detalles) - 1)  # Usar len() en lugar de 3084 hardcodeado
# #     if random_number not in indices_seleccionados and random_number not in my_list:
# #         indices_seleccionados.append(random_number)

# # indices_seleccionados = indices_seleccionados + positive_elements_indexes

# # # Seleccionar las filas usando los índices
# # df_detalles_nuevo = df_detalles.iloc[indices_seleccionados].copy()
# # df_encoded_nuevo = df_encoded.iloc[indices_seleccionados].copy()

# # # Resetear los índices para que vayan de 0 a 49
# # df_detalles_nuevo.reset_index(drop=True, inplace=True)
# # df_encoded_nuevo.reset_index(drop=True, inplace=True)
# # df_detalles_nuevo["id"] = [i for i in range(1, len(df_detalles_nuevo)+1)]

# # # Guardar los nuevos archivos
# # df_detalles_nuevo.to_csv("data_test_for_page_detalle_nuevo.csv", index=False, sep='|')
# # df_encoded_nuevo.to_csv("fraud_detection_nuevo.csv", index=False)

# # print(f"Archivos creados exitosamente con {len(df_detalles_nuevo)} registros cada uno")
# # print(f"Índices seleccionados: {sorted(indices_seleccionados)}")

# # # Verificar que los DataFrames tienen datos
# # print(f"Forma df_detalles_nuevo: {df_detalles_nuevo.shape}")
# # print(f"Forma df_encoded_nuevo: {df_encoded_nuevo.shape}")