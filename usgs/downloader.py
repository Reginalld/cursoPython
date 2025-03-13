import json
import requests
import sys
import time
import argparse
import datetime
import threading
import re
import os

# Definições iniciais
MAX_THREADS = 5  # Número máximo de downloads simultâneos
SEMA = threading.Semaphore(value=MAX_THREADS)
LABEL = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # Label baseado no timestamp atual
THREADS = []
LOG_FILE = "download_log.txt"

# Função para log
def log_message(message):
    print(message)
    with open(LOG_FILE, "a") as log:
        log.write(f"{datetime.datetime.now()} - {message}\n")

# Função para enviar requisições à API
def send_request(url, data, api_key=None):  
    try:
        headers = {"X-Auth-Token": api_key} if api_key else {}
        response = requests.post(url, json.dumps(data), headers=headers)
        response.raise_for_status()
        output = response.json()
        
        if output.get("errorCode"):
            log_message(f"Erro na requisição {url}: {output['errorCode']} - {output['errorMessage']}")
            sys.exit()
        
        log_message(f"Requisição {url} concluída com sucesso.")
        return output["data"]
    except requests.RequestException as e:
        log_message(f"Erro de conexão com {url}: {e}")
        sys.exit()
    except json.JSONDecodeError:
        log_message(f"Erro ao interpretar resposta JSON de {url}")
        sys.exit()

# Função para download
def download_file(url, path):
    SEMA.acquire()
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        disposition = response.headers.get("content-disposition", "")
        filename = re.findall("filename=(.+)", disposition)
        filename = filename[0].strip("\"") if filename else f"file_{datetime.datetime.now().timestamp()}.dat"
        
        file_path = os.path.join(path, filename)
        
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        
        log_message(f"Download concluído: {file_path}")
    except Exception as e:
        log_message(f"Erro ao baixar {url}: {e}")
    finally:
        SEMA.release()

# Função para gerenciar threads de download
def run_download(url, path):
    thread = threading.Thread(target=download_file, args=(url, path))
    THREADS.append(thread)
    thread.start()

if __name__ == "__main__": 
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', required=True, help='ERS Username')
    parser.add_argument('-t', '--token', required=True, help='ERS application token')
    parser.add_argument('-p', '--path', required=True, help='Diretório para salvar arquivos')
    args = parser.parse_args()

    username = args.username
    token = args.token
    path = args.path
    os.makedirs(path, exist_ok=True)

    log_message("Iniciando script...")
    service_url = "https://m2m.cr.usgs.gov/api/api/json/stable/"

    # Autenticação
    api_key = send_request(service_url + "login-token", {"username": username, "token": token})
    log_message(f"API Key obtida: {api_key}")

    dataset_name = "gls_all"
    spatial_filter = {"filterType": "mbr", "lowerLeft": {"latitude": 30, "longitude": -120}, "upperRight": {"latitude": 40, "longitude": -140}}
    temporal_filter = {"start": "2000-12-10", "end": "2005-12-10"}
    payload = {"datasetName": dataset_name, "spatialFilter": spatial_filter, "temporalFilter": temporal_filter}
    
    log_message("Buscando datasets...")
    datasets = send_request(service_url + "dataset-search", payload, api_key)
    log_message(f"{len(datasets)} datasets encontrados.")

    for dataset in datasets:
        if dataset['datasetAlias'] != dataset_name:
            log_message(f"Dataset {dataset['collectionName']} encontrado, mas ignorado.")
            continue

        acquisition_filter = {"end": "2005-12-10", "start": "2000-12-10"}
        payload = {"datasetName": dataset['datasetAlias'], "maxResults": 2, "startingNumber": 1, "sceneFilter": {"spatialFilter": spatial_filter, "acquisitionFilter": acquisition_filter}}
        
        log_message("Buscando cenas...")
        scenes = send_request(service_url + "scene-search", payload, api_key)

        if scenes['recordsReturned'] > 0:
            scene_ids = [result['entityId'] for result in scenes['results']]
            payload = {"datasetName": dataset['datasetAlias'], "entityIds": scene_ids}
            download_options = send_request(service_url + "download-options", payload, api_key)

            downloads = [{"entityId": product['entityId'], "productId": product['id']} for product in download_options if product['available']]
            
            if downloads:
                payload = {"downloads": downloads, "label": LABEL}
                request_results = send_request(service_url + "download-request", payload, api_key)

                available_downloads = request_results.get("availableDownloads", [])
                for download in available_downloads:
                    run_download(download['url'], path)
        else:
            log_message("Nenhuma cena encontrada.")
    
    log_message("Aguardando downloads...")
    for thread in THREADS:
        thread.join()
    
    log_message("Downloads concluídos.")
    send_request(service_url + "logout", None, api_key)
    log_message("Logout realizado.")
