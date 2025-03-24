import json
import requests
import sys
import argparse
import datetime
import threading
import os
import tarfile
import rasterio
import numpy as np

# Definições iniciais
MAX_THREADS = 3
SEMA = threading.Semaphore(value=MAX_THREADS)
THREADS = []
LOG_FILE = "download_log.txt"
LABEL = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Função para log
def log_message(message):
    print(message)
    with open(LOG_FILE, "a") as log:
        log.write(f"{datetime.datetime.now()} - {message}\n")

# Função para requisição à API
def send_request(url, data, api_key=None):
    try:
        headers = {"X-Auth-Token": api_key} if api_key else {}
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})
    except Exception as e:
        log_message(f"Erro na requisição {url}: {e}")
        sys.exit()

# Função para download
def download_file(url, path):
    SEMA.acquire()
    try:
        filename = os.path.join(path, "downloaded_scene.tar")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filename, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        log_message(f"Download concluído: {filename}")
    except Exception as e:
        log_message(f"Erro ao baixar {url}: {e}")
    finally:
        SEMA.release()

# Função para extrair e combinar bandas RGB
def process_landsat_tar(tar_path, output_path):
    bands = {}
    with tarfile.open(tar_path, "r") as tar:
        for member in tar.getnames():
            if any(b in member for b in ["B4.TIF", "B3.TIF", "B2.TIF"]):
                tar.extract(member, output_path)
                band_name = member.split("_")[-1].replace(".TIF", "")
                bands[band_name] = os.path.join(output_path, member)
    
    if len(bands) != 3:
        log_message("Erro: Nem todas as bandas RGB foram encontradas.")
        return
    
    # Abrir as bandas e combinar em um único TIFF
    with rasterio.open(bands["B4"]) as r, rasterio.open(bands["B3"]) as g, rasterio.open(bands["B2"]) as b:
        profile = r.profile
        profile.update(count=3, dtype=rasterio.uint16)
        rgb_output = os.path.join(output_path, "landsat_rgb.tif")
        with rasterio.open(rgb_output, "w", **profile) as dst:
            dst.write(r.read(1), 1)
            dst.write(g.read(1), 2)
            dst.write(b.read(1), 3)
    
    log_message(f"Imagem RGB salva em {rgb_output}")
    os.remove(tar_path)
    for f in bands.values():
        os.remove(f)

# Função principal
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', required=True, help='ERS Username')
    parser.add_argument('-t', '--token', required=True, help='ERS application token')
    parser.add_argument('-p', '--path', required=True, help='Diretório para salvar arquivos')
    args = parser.parse_args()
    os.makedirs(args.path, exist_ok=True)
    
    log_message("Iniciando script...")
    service_url = "https://m2m.cr.usgs.gov/api/api/json/stable/"
    api_key = send_request(service_url + "login-token", {"username": args.username, "token": args.token})
    
    dataset_name = "landsat_ot_c2_l2"
    spatial_filter = {"filterType": "mbr", "lowerLeft": {"latitude": -25.4808, "longitude": -54.6457}, "upperRight": {"latitude": -25.3908, "longitude": -54.5457}}
    temporal_filter = {"start": "2024-01-01", "end": "2024-05-15"}
    cloud_filter = {'min': 0, 'max': 20}
    acquisition_filter = {"start": "2024-01-01", "end": "2024-05-15"}
    
    payload = {
        "datasetName": dataset_name,
        "spatialFilter": spatial_filter,
        "temporalFilter": temporal_filter,
        "sceneFilter": {"spatialFilter": spatial_filter, "acquisitionFilter": acquisition_filter, "cloudCoverFilter": cloud_filter}
    }
    
    log_message("Buscando cenas...")
    scenes = send_request(service_url + "scene-search", payload, api_key)
    if scenes.get("recordsReturned", 0) > 0:
        scene_id = scenes["results"][0]["entityId"]
        payload = {"datasetName": dataset_name, "entityIds": [scene_id]}
        download_options = send_request(service_url + "download-options", payload, api_key)
        download_url = next((opt["url"] for opt in download_options if opt["available"]), None)
        
        if download_url:
            log_message("Iniciando download...")
            download_file(download_url, args.path)
            process_landsat_tar(os.path.join(args.path, "downloaded_scene.tar"), args.path)
        else:
            log_message("Nenhum download disponível.")
    else:
        log_message("Nenhuma cena encontrada.")
    
    send_request(service_url + "logout", None, api_key)
    log_message("Logout realizado.")