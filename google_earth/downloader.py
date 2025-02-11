import os
import ee
import geemap
from rasterio.plot import show
from matplotlib import pyplot as plt
import typer

def initialize_gee(service_account, key_path,project):
    #Inicializado o GEE com a conta de serviço fornecida
    try:
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"Arquivo de chave de serviço não encontrado: {key_path}")
        credentials = ee.ServiceAccountCredentials(service_account,key_path)
        ee.Initialize(credentials,project=project)
        print('GEE inicializado com sucesso')
    except Exception as e:
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

def get_sentinel_image(satelite,lat, lon, radius_km=5, start_date='2025-01-01', end_date='2025-02-01'):
    # Obtém imagens do Sentinel-2A para uma área específica com um raio definido
    try:
        point = ee.Geometry.Point([lon,lat])
        region = point.buffer(radius_km * 1000)

        if satelite == 'Sentinel-2_SR':
            collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')\
                    .filterBounds(region) \
                    .filterDate(ee.Date(start_date),ee.Date(end_date))\
                    .sort('CLOUDY_PIXEL_PERCENTAGE') \
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',20)) \
                    .map(mask_s2_clouds)
            
            image = collection.first()
            image = image.select(['B4', 'B3', 'B2','B8'])  # Bandas Vermelho, Verde, Azul e NIR para cálculo de NDVI
        
        elif satelite == 'Sentinel-2':
            collection = ee.ImageCollection('COPERNICUS/S2_HARMONIZED')\
                    .filterBounds(region)\
                    .filterDate(ee.Date(start_date),ee.Date(end_date))\
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',20))\
                    .map(mask_s2_clouds)
            
            image = collection.first()
            image = image.select(['B4','B3','B2','B8'])


        elif satelite == 'Sentinel-1':
            collection = ee.ImageCollection('COPERNICUS/S1_GRD')\
                .filterBounds(region)\
                .filterDate(ee.Date(start_date), ee.Date(end_date))\
                .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))\
                .filter(ee.Filter.eq('instrumentMode', 'IW'))\
                .map(mask_s1_edges)
            
            image = collection.median().select('VV')    
        else:
            raise ValueError('Satélite não suportado. Escolha entre os satélites informados')
        
        count = collection.size().getInfo()
        print(f"{count} imagens encontradas para a região.") 

        if count == 0:
            raise ValueError("Nenhuma imagem encontrada para os parâmetros fornecidos.")
        
        return image, region
    
    except Exception as e:
        print(f'Erro ao obter imagem {satelite}: {e}')
        return None,None

def download_image(image, region, output_dir,filename):
    try:
        if image is None:
            raise ValueError("Imagem inválida. Verifique os parâmetros.")
        url = image.getDownloadURL({'scale': 10, 'region': region, 'format': 'GeoTIFF'})
        filepath = os.path.join(output_dir, filename)
        geemap.download_file(url, filepath, overwrite=True)
        print(f"Imagem salva em: {filepath}")
        return filepath
    except Exception as e:
        raise RuntimeError('Erro ao fazer download da imagem',e)

app = typer.Typer()

@app.command()
def main(
    satelite: str = typer.Argument(..., help="Escolha um satélite (Sentinel-1, Sentinel-2_SR, Sentinel-2)"),
    lat: float = typer.Argument(..., help="Latitude da área de interesse",show_default=True),
    lon: float = typer.Argument(..., help="Longitude da área de interesse",show_default=True),
    radius_km: float = typer.Argument(5.0, help="Raio da área de interesse em km",show_default=True),
    service_account: str = typer.Option("teste-api-key@sunlit-flag-449511-f7.iam.gserviceaccount.com", help="Conta de serviço do GEE"),
    key_path: str = typer.Option("D:\\codigos\\Python_curso\\google_earth\\api_key_test.json", help="Caminho para a chave JSON da conta de serviço"),
    project: str = typer.Option("ee-reginaldosg", help="Nome do projeto GEE"),
    output_dir: str = typer.Option("D:\\codigos\\imagens", help="Diretório de saída para salvar as imagens"),
):
 
    """Baixa imagens de satélite do Google Earth Engine."""
    initialize_gee(service_account, key_path, project)
    create_output(output_dir)
    
    image, region = get_sentinel_image(satelite, lat, lon, radius_km)
    if image is None:
        typer.echo("Erro: Nenhuma imagem encontrada para os parâmetros fornecidos.")
        raise typer.Exit(code=1)
    
    filename = f"{satelite}_{lat}_{lon}_{radius_km}km.tif"
    download_image(image, region, output_dir, filename)
            

if __name__ == "__main__":
    app()