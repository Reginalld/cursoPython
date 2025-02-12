import os
import ee
import geemap
import rasterio
from rasterio.plot import show
from matplotlib import pyplot as plt
import requests
import logging

logging.basicConfig(
    level=logging.INFO,  # Pode ser DEBUG, INFO, WARNING, ERROR
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("sentinel_log.txt"),  # Salva em arquivo
        logging.StreamHandler()  # Exibe no console
    ]
)

def initialize_gee(service_account, key_path,project):
    #Inicializado o GEE com a conta de serviço fornecida
    try:
        logging.info("Inicializando o Google Earth Engine (GEE)...")
        if not os.path.exists(key_path):
            logging.error(f"Arquivo de chave de serviço não encontrado: {key_path}")
            raise FileNotFoundError(f"Arquivo de chave de serviço não encontrado: {key_path}")
        credentials = ee.ServiceAccountCredentials(service_account,key_path)
        ee.Initialize(credentials,project=project)
        logging.info(f"GEE inicializado com sucesso para o projeto {project}")
    except Exception as e:
        logging.critical(f"Erro ao inicializar o GEE: {e}", exc_info=True)
        raise RuntimeError(f"Erro ao inicializar o GEE: {e}")

def create_output(output_dir):
    # Função para criar o diretório de saída, caso não exista
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

def mask_s2_clouds(image):
  """Masks clouds in a Sentinel-2 image using the QA band.
  Args:
      image (ee.Image): A Sentinel-2 image.
  Returns:
      ee.Image: A cloud-masked Sentinel-2 image.
  """
  qa = image.select('QA60')
  # Bits 10 and 11 are clouds and cirrus, respectively.
  cloud_bit_mask = 1 << 10
  cirrus_bit_mask = 1 << 11
  # Both flags should be set to zero, indicating clear conditions.
  mask = (
      qa.bitwiseAnd(cloud_bit_mask)
      .eq(0)
      .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
  )
  return image.updateMask(mask).divide(10000)

def mask_s1_edges(image):
    edge = image.lt(-30.0)
    masked_image = image.mask().And(edge.Not())
    return image.updateMask(masked_image)

def get_sentinel_image(satelite,lat, lon, radius_km=5, start_date='2024-12-01', end_date='2025-02-01'):
    # Obtém imagens do Sentinel-2A para uma área específica com um raio definido
    try:
        logging.info(f"Buscando imagens do {satelite} para ({lat}, {lon}) com raio de {radius_km} km...")
        point = ee.Geometry.Point([lon,lat])
        region = point.buffer(radius_km * 500).bounds()

        if satelite == 'Sentinel-2_SR':
            collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')\
                    .filterBounds(region) \
                    .filterDate(ee.Date(start_date),ee.Date(end_date))\
                    .sort('CLOUDY_PIXEL_PERCENTAGE') \
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',20)) \
                    .map(mask_s2_clouds)
            
            image = collection.median()
            image = image.select(['B4', 'B3', 'B2', 'B8'])
            image = image.reproject('EPSG:4326', None, 10)  # Adiciona projeção fixa
        
        elif satelite == 'Sentinel-2':
            collection = ee.ImageCollection('COPERNICUS/S2_HARMONIZED')\
                    .filterBounds(region)\
                    .filterDate(ee.Date(start_date),ee.Date(end_date))\
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',20))\
                    .map(mask_s2_clouds)
            
            image = collection.median()
            image = image.select(['B4', 'B3', 'B2', 'B8'])
            image = image.reproject('EPSG:4326', None, 10)  # Adiciona projeção fixa


        elif satelite == 'Sentinel-1':
            collection = ee.ImageCollection('COPERNICUS/S1_GRD')\
                .filterBounds(region)\
                .filterDate(ee.Date(start_date), ee.Date(end_date))\
                .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))\
                .filter(ee.Filter.eq('instrumentMode', 'IW'))\
                .map(mask_s1_edges)
            
            image = collection.qualityMosaic('VV')
            image = image.reproject('EPSG:4326', None, 10)  # Força uma projeção fixa

        else:
            logging.warning(f"Satélite {satelite} não suportado!")
            raise ValueError('Satélite não suportado. Escolha entre os satélites informados')
        
        count = collection.size().getInfo()
        logging.info(f"{count} imagens encontradas para {satelite}.")

        if count == 0:
            logging.warning("Nenhuma imagem encontrada para os parâmetros fornecidos.")
            raise ValueError("Nenhuma imagem encontrada para os parâmetros fornecidos.")
        
        return image, region
    
    except Exception as e:
        logging.error(f"Erro ao obter imagem {satelite}: {e}", exc_info=True)
        return None,None

def download_image(image, region, output_dir,filename):
    try:
        if image is None:
            logging.error("Tentativa de download com imagem inválida.")
            raise ValueError("Imagem inválida. Verifique os parâmetros.")
        filepath = os.path.join(output_dir, filename)
        logging.info(f"Iniciando download da imagem para {filepath}...")

        geemap.download_ee_image(image,filepath,scale=10,region=region)
        logging.info(f"Download concluído: {filepath}")
        # url = image.getDownloadURL({'scale': 10, 'region': region, 'format': 'GeoTIFF'})
        # geemap.download_file(url, filepath, overwrite=True)
        # print(f"Imagem salva em: {filepath}")
        return filepath
    except Exception as e:
        logging.critical(f"Erro ao fazer download da imagem: {e}", exc_info=True)
        raise RuntimeError('Erro ao fazer download da imagem',e)

def plot_image(filepath,satelite):
    
    try:
        if satelite == "Sentinel-1":
            with rasterio.open(filepath) as src:
                fig, ax = plt.subplots(figsize=(10, 10))
                show(src.read(1), ax=ax, cmap='gray')  # Sentinel-1 é SAR, então exibe em tons de cinza
                plt.title('Imagem de Satélite')
                plt.show()
        elif satelite == 'Sentinel-2_SR':
            with rasterio.open(filepath) as src:
                img = src.read([3, 2, 1]).astype(float)
                img = img / img.max()  # Normalização para melhorar o contraste
                fig, ax = plt.subplots(figsize=(10, 10))
                show(img, ax=ax)
                plt.title('Sentinel-2 RGB (B4, B3, B2)')
                plt.axis('off')
                plt.show()
    except Exception as e:
        print(f'Erro ao exibir a imagem: {e}')

def main():
    #Função main responsável pelo núcleo central da aplicação
  
    #Identificação da conta de serviço do google que está conectada e tem as autoricações necessárias com o projeto do GEE
    #Variável de acesso ao google por meio de dois parâmetros, a indentificação da conta de serviço e a chave json gerada nessa conta de serviço
    service_account = 'teste-api-key@sunlit-flag-449511-f7.iam.gserviceaccount.com'
    key_path = 'D:\\codigos\\Python_curso\\google_earth\\layer\\api_key_test.json'
    project = 'ee-reginaldosg'
    output_dir = 'D:\\codigos\\imagens'
    initialize_gee(service_account,key_path,project)
    create_output(output_dir)

    while True:
        #Entrada do usuário
        try:
            satelite = input('Escolha um satélite (Sentinel-1 / Sentinel-2_SR / Sentinel-2): '.strip())
            lat = float(input('Digite a latitude: '))
            lon = float(input('Digite a longitude: '))
            radius_km = float(input('Digite o raio em km: '))
        except ValueError:
            logging.error("Erro: Entrada inválida do usuário.")
            continue
        
        #Processamento da imagem
        image, region = get_sentinel_image(satelite,lat,lon,radius_km)
        if image is None:
            logging.warning("Nenhuma imagem encontrada.")
            continue
        
        #Baixando a imagem e exibindo para alguma inspeção básica de funcionamento
        filename = f'{satelite}_{lat}_{lon}_{radius_km}km.tif'
        download_image(image,region,output_dir,filename)
            
        repeat = input("Deseja processar outra imagem? (s/n): ").strip().lower()
        if repeat != 's':
            logging.info("Encerrando o programa.")
            break

main()