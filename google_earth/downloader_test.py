import os
import ee
import geemap
import rasterio
from rasterio.plot import show
from matplotlib import pyplot as plt
import requests

#Identificação da conta de serviço do google que está conectada e tem as autoricações necessárias com o projeto do GEE
service_account = 'teste-api-key@sunlit-flag-449511-f7.iam.gserviceaccount.com'
#Variável de acesso ao google por meio de dois parâmetros, a indentificação da conta de serviço e a chave json gerada nessa conta de serviço
credentials = ee.ServiceAccountCredentials(service_account,'D:\\codigos\\Python_curso\\google_earth\\api_key_test.json')
ee.Initialize(credentials,project='ee-reginaldosg')

# Diretório de saída
output_dir = 'D:\\codigos\\imagens'

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

def get_sentinel2_image(lat, lon, radius_km=5, start_date='2024-01-01', end_date='2024-02-01'):
    
    # Obtém imagens do Sentinel-2A para uma área específica com um raio definido
    point = ee.Geometry.Point([lon,lat])
    region = point.buffer(radius_km * 1000)

    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')\
        .filterBounds(region) \
        .filterDate(ee.Date(start_date),ee.Date(end_date))\
        .sort('CLOUDY_PIXEL_PERCENTAGE') \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',20)) \
        .map(mask_s2_clouds)
    
    image = collection.first()
    image = image.select(['B4', 'B3', 'B2','B8'])  # Bandas Vermelho, Verde, Azul e NIR para cálculo de NDVI
    return image, region

def download_image(image, region, file):


    #  url = image.getDownloadURL({
    #     'scale': 30,
    #     'region': region,
    #     'format': 'GeoTIFF'
    # })

    # filepath = os.path.join(output_dir, file)
    
    # response = requests.get(url, stream=True)
    # if response.status_code == 200:
    #     with open(filepath, 'wb') as file:
    #         for chunk in response.iter_content(1024):
    #             file.write(chunk)
    #     print(f"Imagem salva em: {filepath}")
    # else:
    #     print(f"Erro ao baixar imagem: {response.status_code}, {response.text}")
    
    # return filepath
    
    url = image.getDownloadURL({
        'scale': 10, 
        'region': region,
        'format': 'GeoTIFF'
    })

    filepath = os.path.join(output_dir, file)
    geemap.download_file(url, filepath)
    print(f'Imagem salve em: {filepath}')
    return filepath

def plot_image(filepath):
    

    with rasterio.open(filepath) as src:
        fig, ax= plt.subplots(figsize=(10,10))
        show(src.read([3,2,1]), ax=ax) 
        plt.title('Sentinel-2A Imagem RGB')
        plt.show()

latitude = -23.5505
longitude = -46.6333

image, region = get_sentinel2_image(latitude,longitude)
image_path = download_image(image,region,'imagem_teste_NDVI.tif')

