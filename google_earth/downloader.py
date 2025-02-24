import os
import ee
import geemap
import logging
import typer

logging.basicConfig(
    level=logging.INFO,  # Pode ser DEBUG, INFO, WARNING, ERROR
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("sentinel_log.txt"),  # Salva em arquivo
        logging.StreamHandler()  # Exibe no console
    ]
)

#Inicialização do Google Earth Engine
class GEEManager:
    def __init__(self, service_account: str, key_path: str, project: str):
        self.service_account = service_account
        self.key_path = key_path
        self.project = project
        self.initialize_gee()

    def initialize_gee(self):
        #Inicializado o GEE com a conta de serviço fornecida
        try:
            logging.info("Inicializando o Google Earth Engine (GEE)...")
            if not os.path.exists(self.key_path):
                logging.error(f"Arquivo de chave de serviço não encontrado: {self.key_path}")
                raise FileNotFoundError(f"Arquivo de chave de serviço não encontrado: {self.key_path}")
            credentials = ee.ServiceAccountCredentials(self.service_account,self.key_path)
            ee.Initialize(credentials,project=self.project)
            logging.info(f"GEE inicializado com sucesso para o projeto {self.project}")
        except Exception as e:
            logging.critical(f"Erro ao inicializar o GEE: {e}", exc_info=True)
            raise RuntimeError(f"Erro ao inicializar o GEE: {e}")

class SentinelImageSearch:
    def __init__(self,satelite: str, lat: float, lon: float, radius_km: float, start_date: str, end_date: str):
        self.satelite = satelite
        self.lat = lat
        self.lon = lon
        self.radius_km = radius_km
        self.start_date = start_date
        self.end_date = end_date

    def mask_s2_clouds(self,image):
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

    def mask_s1_edges(self,image):
        edge = image.lt(-30.0)
        masked_image = image.mask().And(edge.Not())
        return image.updateMask(masked_image)
    
    def apply_scale_factors(self,image):
        optical_bands = image.select('SR_B.*').multiply(0.0000275).add(-0.2)
        thermal_bands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
        return image.addBands(optical_bands, None, True).addBands(
            thermal_bands, None, True
        )
    
    def mask_l8_clouds(self,image):
        """Masks clouds in a Landsat 8 image using the QA_PIXEL band.
        
        Args:
            image (ee.Image): A Landsat 8 image.
        
        Returns:
            ee.Image: A cloud-masked Landsat 8 image.
        """
        qa = image.select('QA_PIXEL')
        
        # Bits de interesse na QA_PIXEL
        cloud_bit = 1 << 3  # Indica a presença de nuvens
        cloud_shadow_bit = 1 << 4  # Indica a presença de sombras de nuvem

        # Criação da máscara (onde os bits de nuvem e sombra são 0, ou seja, sem nuvens)
        mask = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(cloud_shadow_bit).eq(0))

        # Aplica a máscara e mantém apenas os pixels válidos
        return image.updateMask(mask)
        
    def get_sentinel_image(self):
        # Obtém imagens para uma área específica com um raio definido
        try:
            logging.info(f"Buscando imagens do {self.satelite} para ({self.lat}, {self.lon}) com raio de {self.radius_km} km...")
            point = ee.Geometry.Point([self.lon,self.lat])
            region = point.buffer(self.radius_km * 1000).bounds()

            if self.satelite == 'Landsat8_T1_L2':
                collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')\
                    .filterBounds(region)\
                    .filterDate(ee.Date(self.start_date), ee.Date(self.end_date))

                # Aplicando a máscara de nuvens
                collection = collection.map(self.mask_l8_clouds)

                # Aplicando a mediana e os fatores de escala
                image = collection.median()
                image = self.apply_scale_factors(image)

                # Selecionando as bandas desejadas
                image = image.select(['SR_B4', 'SR_B3', 'SR_B2', 'SR_B5'])

                # Reprojetando
                image = image.reproject('EPSG:4326', None, 30)

            elif self.satelite == 'Landsat8_T1_TOA':
                collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_TOA')\
                        .filterBounds(region)\
                        .filterDate(ee.Date(self.start_date),ee.Date(self.end_date))\

                image = collection.median()
                image = image.select(['B2','B3','B4','B5'])
                image = image.reproject('EPSG:4326', None, 30)

            elif self.satelite == 'Landsat8_T1':
                collection = ee.ImageCollection('LANDSAT/LC08/C02/T1')\
                        .filterBounds(region)\
                        .filterDate(ee.Date(self.start_date),ee.Date(self.end_date))\
                        
                image = collection.median()
                image = image.select(['B2','B3','B4','B5'])
                image = image.reproject('EPSG:4326', None, 30)
            
            elif self.satelite == 'Landsat9_T1':
                collection = ee.ImageCollection('LANDSAT/LC09/C02/T1')\
                        .filterBounds(region)\
                        .filterDate(ee.Date(self.start_date),ee.Date(self.end_date))\
                
                image = collection.median()
                image = image.select(['B2','B3','B4','B5'])
                image = image.reproject('EPSG:4326', None, 30)

            elif self.satelite == 'Sentinel-2_SR':
                collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')\
                        .filterBounds(region) \
                        .filterDate(ee.Date(self.start_date),ee.Date(self.end_date))\
                        .sort('CLOUDY_PIXEL_PERCENTAGE') \
                        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',20)) \
                        .map(self.mask_s2_clouds)
                
                image = collection.median()
                image = image.select(['B4', 'B3', 'B2', 'B8'])
                image = image.reproject('EPSG:4326', None, 10)  # Adiciona projeção fixa
            
            elif self.satelite == 'Sentinel-2':
                collection = ee.ImageCollection('COPERNICUS/S2_HARMONIZED')\
                        .filterBounds(region)\
                        .filterDate(ee.Date(self.start_date),ee.Date(self.end_date))\
                        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',20))\
                        .map(self.mask_s2_clouds)
                
                image = collection.median()
                image = image.select(['B4', 'B3', 'B2', 'B8'])
                image = image.reproject('EPSG:4326', None, 10)  # Adiciona projeção fixa


            elif self.satelite == 'Sentinel-1':
                collection = ee.ImageCollection('COPERNICUS/S1_GRD')\
                    .filterBounds(region)\
                    .filterDate(ee.Date(self.start_date), ee.Date(self.end_date))\
                    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))\
                    .filter(ee.Filter.eq('instrumentMode', 'IW'))\
                    .map(self.mask_s1_edges)
                
                image = collection.qualityMosaic('VV')
                image = image.reproject('EPSG:4326', None, 10) 

            else:
                logging.warning(f"Satélite {self.satelite} não suportado!")
                raise ValueError('Satélite não suportado. Escolha entre os satélites informados')
            
            count = collection.size().getInfo()
            logging.info(f"{count} imagens encontradas para {self.satelite}.")

            if count == 0:
                logging.warning("Nenhuma imagem encontrada para os parâmetros fornecidos.")
                raise ValueError("Nenhuma imagem encontrada para os parâmetros fornecidos.")
            
            return image, region
        
        except Exception as e:
            logging.error(f"Erro ao obter imagem {self.satelite}: {e}", exc_info=True)
            return None,None

class ImageDownloader:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.create_output()

    def create_output(self):
        # Função para criar o diretório de saída, caso não exista
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)


    def download_image(self, image, region,filename):
        try:
            if image is None:
                logging.error("Tentativa de download com imagem inválida.")
                raise ValueError("Imagem inválida. Verifique os parâmetros.")
            filepath = os.path.join(self.output_dir, filename)
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
    
app = typer.Typer()

@app.command()
def main(
    satelite: str = typer.Argument(..., help="Escolha um satélite (Sentinel-1, Sentinel-2_SR, Sentinel-2)"),
    lat: float = typer.Argument(..., help="Latitude da área de interesse",show_default=True),
    lon: float = typer.Argument(..., help="Longitude da área de interesse",show_default=True),
    radius_km: float = typer.Argument(5.0, help="Raio da área de interesse em km",show_default=True),
    start_date: str = typer.Argument(..., help="Data de início da área de interesse",show_default=True),
    end_date: str = typer.Argument(..., help="Data final da área de interesse",show_default=True),
    service_account: str = typer.Option("teste-api-key@sunlit-flag-449511-f7.iam.gserviceaccount.com", help="Conta de serviço do GEE"),
    key_path: str = typer.Option("google_earth\\key\\api_key_test.json", help="Caminho para a chave JSON da conta de serviço"),
    project: str = typer.Option("ee-reginaldosg", help="Nome do projeto GEE"),
    output_dir: str = typer.Option("D:\\codigos\\imagens", help="Diretório de saída para salvar as imagens"),
):
    
    #Inicializando o GEE
    gee_manager = GEEManager(service_account, key_path,project)

    downloader = SentinelImageSearch(satelite, lat, lon, radius_km, start_date, end_date)
    image, region = downloader.get_sentinel_image()
        
    if image:
        image_downloader = ImageDownloader(output_dir)
        filename = f'{satelite}_{lat}_{lon}_{radius_km}km_{start_date}_{end_date}.tif'
        image_downloader.download_image(image, region, filename)
    else:
        logging.warning("Nenhuma imagem encontrada")
            

if __name__ == "__main__":
    app()