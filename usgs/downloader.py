import json
import requests
import sys
import time
import argparse
import datetime
import threading
import re
import os
import tarfile
import rasterio
import numpy as np
from rasterio.merge import merge
from rasterio.plot import show

# Definições iniciais
MAX_THREADS = 5  # Número máximo de downloads simultâneos
SEMA = threading.Semaphore(value=MAX_THREADS)
LABEL = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # Label baseado no timestamp atual
THREADS = []
LOG_FILE = "download_log.txt"
RGB_BANDS = {"4": "B4.TIF", "3": "B3.TIF", "2": "B2.TIF"}  # Bandas RGB para Landsat 8/9

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

# Função para extrair bandas RGB e combinar
def process_landsat_tar(file_path, base_path):
    tiles_path = os.path.join(base_path, "tiles")
    images_path = base_path
    os.makedirs(tiles_path, exist_ok=True)
    
    try:
        with tarfile.open(file_path, "r") as tar:
            members = {band: None for band in RGB_BANDS.values()}
            for member in tar.getmembers():
                for band_key, band_name in RGB_BANDS.items():
                    if band_name in member.name:
                        members[band_name] = member
                        break
            
            if all(members.values()):
                extracted_files = []
                for band_name, member in members.items():
                    tar.extract(member, path=tiles_path)
                    extracted_files.append(os.path.join(tiles_path, member.name))
                
                rgb_files = [rasterio.open(f) for f in extracted_files]
                profile = rgb_files[0].profile
                profile.update(count=3, dtype=np.uint16)
                
                rgb_output_path = os.path.join(images_path, os.path.basename(file_path).replace(".tar", "_RGB.tif"))
                with rasterio.open(rgb_output_path, "w", **profile) as dst:
                    for i, src in enumerate(rgb_files):
                        dst.write(src.read(1), i + 1)
                
                log_message(f"Imagem RGB combinada salva em: {rgb_output_path}")
    except Exception as e:
        log_message(f"Erro ao processar TAR {file_path}: {e}")

# Função para download
def download_file(url, base_path):
    SEMA.acquire()
    tiles_path = os.path.join(base_path, "tiles")
    os.makedirs(tiles_path, exist_ok=True)
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        disposition = response.headers.get("content-disposition", "")
        filename = re.findall("filename=(.+)", disposition)
        filename = filename[0].strip("\"") if filename else f"file_{datetime.datetime.now().timestamp()}.tar"
        
        file_path = os.path.join(tiles_path, filename)
        
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        
        log_message(f"Download concluído: {file_path}")
        process_landsat_tar(file_path, base_path)  # Processar TAR após download
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

    api_key = send_request(service_url + "login-token", {"username": username, "token": token})
    log_message(f"API Key obtida: {api_key}")

    dataset_name = "landsat_ot_c2_l2"
    spatial_filter = {"filterType": "mbr", "lowerLeft": {"latitude": -25.4808, "longitude": -54.6457}, "upperRight": {"latitude": -25.3908, "longitude": -54.5457}}
    temporal_filter = {"start": "2024-01-01", "end": "2024-05-15"}
    cloud_filter = {'min': 0, 'max':20}
    
    payload = {"datasetName": dataset_name, "sceneFilter": {"spatialFilter": spatial_filter, "acquisitionFilter": temporal_filter, "cloudCoverFilter": cloud_filter}}
    log_message("Buscando datasets...")
    datasets = send_request(service_url + "dataset-search", payload, api_key)
    log_message(f"{len(datasets)} datasets encontrados.")

    for dataset in datasets:
        if dataset['datasetAlias'] != dataset_name:
            log_message(f"Dataset {dataset['collectionName']} ignorado.")
            continue
        
        payload = {"datasetName": dataset['datasetAlias'], "maxResults": 2, "startingNumber": 1, "sceneFilter": {"spatialFilter": spatial_filter, "acquisitionFilter": temporal_filter, "cloudCoverFilter": cloud_filter}}
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
                
                for download in request_results.get("availableDownloads", []):
                    run_download(download['url'], path)
    
    log_message("Aguardando downloads...")
    for thread in THREADS:
        thread.join()
    
    log_message("Downloads concluídos.")
    send_request(service_url + "logout", None, api_key)
    log_message("Logout realizado.")