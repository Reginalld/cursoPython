import openeo
import math
import logging
import os
import typer
import rasterio
from rasterio.merge import merge
from concurrent.futures import ThreadPoolExecutor
import time
import geopandas as gpd
import re
from shapely.wkt import loads
import random


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("docker_copernicus\\log\\copernicus_log.txt"),
        logging.StreamHandler()
    ]
)

class CopernicusConnection:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.connection = None

    def initialize(self):
        try:
            logging.info("Inicializando a conexão com a Data Base da copernicus...")
            self.connection = openeo.connect('openeofed.dataspace.copernicus.eu')
            self.connection.authenticate_oidc_client_credentials(self.client_id, self.client_secret, provider_id='CDSE')
        except Exception as e:
            logging.critical(f"Erro ao inicializar o copernicus: {e}", exc_info=True)
            raise RuntimeError(f"Erro ao inicializar o copernicus {e}")

    def get_connection(self):
        if self.connection is None:
            self.initialize()
        return self.connection


class BoundingBoxCalculator:
    @staticmethod
    def calcular(lat, lon, raio_km):
        raio_graus_lat = raio_km / 111
        raio_graus_lon = raio_km / (111 * math.cos(math.radians(lat)))

        return {
            'west': lon - raio_graus_lon,
            'south': lat - raio_graus_lat,
            'east': lon + raio_graus_lon,
            'north': lat + raio_graus_lat,
            'crs': 'EPSG:4326',
        }


class SatelliteImageFetcher:
    def __init__(self, connection):
        self.connection = connection

    def fetch_image(self, satelite, bounding_box, start_date, end_date):
        try:
            logging.info(f"Buscando imagens do {satelite}...")

            if satelite == 'SENTINEL2_L2A':
                # Carregar a coleção
                image = self.connection.load_collection(
                    "SENTINEL2_L2A",
                    spatial_extent=bounding_box,
                    temporal_extent=[start_date, end_date],
                    bands=["B02", "B03", "B04"],
                    max_cloud_cover=20,
                )

                image = image.resample_spatial(resolution=10)
                image = image.reduce_dimension(dimension='t', reducer='median')


            elif satelite == 'SENTINEL2_L1C':
                image = self.connection.load_collection(
                    "SENTINEL2_L2A",
                    spatial_extent=bounding_box,
                    temporal_extent = [start_date, end_date],
                    bands=["B02", "B03", "B04"],
                    max_cloud_cover=20,

                )
                image = image.resample_spatial(resolution=10) 
                image = image.reduce_dimension(dimension='t', reducer='median')

            elif satelite == 'SENTINEL1_GRD':
                image = self.connection.load_collection(
                    "SENTINEL1_GRD",
                    spatial_extent=bounding_box,
                    temporal_extent = [start_date,end_date],
                    bands = ["VV","VH"]
                )
                image = image.sar_backscatter(
                    coefficient = 'sigma0-ellipsoid'
                )

            else:
                logging.warning(f"Satélite {satelite} não suportado!")
                raise ValueError("Satélite não suportado.")

            return image
        except Exception as e:
            logging.error(f'Erro ao obter imagem do {satelite}: {e}', exc_info=True)
            return None


class ImageDownloader:
    def __init__(self,output_dir):
        self.output_dir = output_dir
        self.create_output()

    def create_output(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True) 

    def download(self, image, filename):
        try:
            if image is None:
                logging.error("Tentativa de download com imagem inválida")
                raise ValueError("Imagem inválida.")
            

            filepath = os.path.join(self.output_dir, filename)
            logging.info(f"filepath calculado: {filepath}")
            os.makedirs(os.path.dirname(filepath), exist_ok=True) 
            logging.info(f"Iniciando download da imagem para {filepath}...")
            image.download(filepath)
            logging.info(f'Download concluído')
            return filepath
        except Exception as e:
            logging.error(f"Erro ao fazer download da imagem: {str(e)}")
            raise RuntimeError("Erro ao fazer download da imagem", e)
        
    def download_async(self,image_list,filenames):
        def process_download(image, filename):
            time.sleep(30)
            return self.download(image, filename)

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for idx, (img, fname) in enumerate(zip(image_list, filenames)):
                time.sleep(5)
                future = executor.submit(process_download, img, fname)
                futures.append(future)

            # Verificação dos resultados do download
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Erro no download assíncrono: {e}")
        
def divide_bbox(bbox, tile_size_km, center_lat,raio_condicional):

    radius_km = ((bbox['north'] - bbox['south']) * 111) / 2
    if int(raio_condicional) >= 80:
        desired_divisions = 5
    elif int(raio_condicional) >= 50 and int(raio_condicional) <= 79:
        desired_divisions = 4
    # elif int(raio_condicional) >= 30 and int(raio_condicional) <= 49:
    #     desired_divisions = 3
    else:
        desired_divisions = 3
        logging.info('Entrei no if condicional')

    effective_tile_size = max(tile_size_km, (2 * radius_km) / desired_divisions)
    
    delta_lat = effective_tile_size / 111.0
    delta_lon = effective_tile_size / (111.0 * math.cos(math.radians(center_lat)))
    
    bboxes = []
    current_lat = bbox['south']
    while current_lat < bbox['north']:
        current_lon = bbox['west']
        while current_lon < bbox['east']:
            sub_bbox = {
                'west': current_lon,
                'south': current_lat,
                'east': min(current_lon + delta_lon, bbox['east']),
                'north': min(current_lat + delta_lat, bbox['north']),
                'crs': 'EPSG:4326'
            }
            bboxes.append(sub_bbox)
            current_lon += delta_lon
        current_lat += delta_lat
    return bboxes

def mosaic_tiles(tile_files, output_path):

    src_files = []
    band_count = None
    for fp in tile_files:
        src = rasterio.open(fp)
        if band_count is None:
            band_count = src.count
        elif src.count != band_count:
            logging.warning(f"Arquivo {fp} possui {src.count} bandas, diferente do esperado ({band_count}). Ignorando este arquivo.")
            src.close()
            continue
        src_files.append(src)
    mosaic, out_trans = merge(src_files)

    out_meta = src_files[0].meta.copy()
    out_meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_trans
    })

    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(mosaic)

    for src in src_files:
        src.close()

    return output_path


app = typer.Typer()


@app.command()
def main(
    satelite: str = typer.Argument(..., help="Escolha um satélite (SENTINEL2_L1C, SENTINEL2_L2A, SENTINEL1_GRD)"),
    lat: float = typer.Option(None, help="Latitude da área de interesse"),
    lon: float = typer.Option(None, help="Longitude da área de interesse"),
    tile_id: str = typer.Option(None, help="ID do tile Sentinel-2 (ex: '21KXP')"),
    radius_km: float = typer.Option(10.0, help="Raio da área de interesse em km"),
    start_date: str = typer.Argument(..., help="Data de início (YYYY-MM-DD)"),
    end_date: str = typer.Argument(..., help="Data final (YYYY-MM-DD)"),
    client_id: str = typer.Option('sh-780be612-cdd5-46c2-be80-016e3d9e3941', help="Client ID da conta Copernicus"),
    client_secret: str = typer.Option('wNqrCLhYnogycEclvClgVfrCRzNxjzec', help="Client Secret da conta Copernicus"),
    output_dir: str = typer.Option("docker_copernicus\\imagens", help="Diretório de saída para salvar as imagens"),
    tile_size_km: float = typer.Option(16.0),
    tile_grid_path: str = typer.Option("docker_copernicus\\shapefile_ids\\grade_sentinel_brasil.shp")
):
    copernicus_conn = CopernicusConnection(client_id, client_secret)
    copernicus_conn.initialize()

    lon_filename = 0.0
    if tile_id:
            logging.info(f"Buscando geometria para o tile {tile_id} na grade do Sentinel-2...")
            tile_grid = gpd.read_file(tile_grid_path)
            def clean_html(value):
                return re.sub(r'<.*?>', "", str(value))
            tile_grid = tile_grid.applymap(clean_html)
            tile_grid = tile_grid[tile_grid["NAME"] == tile_id]
            
            if tile_grid.empty:
                logging.error(f"Tile {tile_id} não encontrado na grade Sentinel-2.")
                raise ValueError("Tile ID inválido.")
            
            tile_geometry = loads(tile_grid.geometry.iloc[0])
            minx, miny, maxx, maxy = tile_geometry.bounds

            main_bbox = {
                "west": minx,
                "south": miny,
                "east": maxx,
                "north": maxy,
                "crs": "EPSG:4326"
            }

            lat = (maxy + miny) / 2  # Ponto central do tile
            lon_filename = (maxx + minx) / 2

            bbox_width_km = ((maxx - minx) * 111 * math.cos(math.radians(lat)))  # Aproximando para km
            bbox_height_km = ((maxy - miny) * 111)  # Aproximando para km
            radius_km = max(bbox_width_km, bbox_height_km) / 2  # Raio = metade do maior lado

            logging.info(f"Raio estimado do BBOX do tile {tile_id}: {radius_km:.2f} km")

    elif lat is not None and lon is not None:
        main_bbox = BoundingBoxCalculator.calcular(lat, lon, radius_km)
        logging.info("Entrei aqui sem ID")
    else:
        logging.error("É necessário fornecer latitude/longitude ou um ID de tile Sentinel-2.")
        raise ValueError("Faltam parâmetros para definir a área de interesse.")
    
    logging.info(f"BBox principal: {main_bbox}")

    fetcher = SatelliteImageFetcher(copernicus_conn.get_connection())
    image_downloader = ImageDownloader(output_dir)
    if radius_km >= 21:
        tiles = divide_bbox(main_bbox, tile_size_km, lat, radius_km)
        logging.info(f"Área dividida em {len(tiles)} lotes")

        temp_files = []
        tile_dir = os.path.join(output_dir, "tiles")  # docker_copernicus\imagens\tiles
        tile_dir = os.path.abspath(tile_dir)  # Converte para caminho absoluto
        logging.info(f"Diretório de tiles (absoluto): {tile_dir}")
        if not os.path.exists(tile_dir):
            os.makedirs(tile_dir, exist_ok=True)
            logging.info(f"Diretório {tile_dir} criado com sucesso")

        image_downloader = ImageDownloader(tile_dir)  # Usa tile_dir como output_dir
        images = []
        filenames = []

        for idx, tile_bbox in enumerate(tiles):
            logging.info(f"Lote {idx+1}/{len(tiles)} selecionado para fila de download com bbox: {tile_bbox}")
            image = fetcher.fetch_image(satelite, tile_bbox, start_date, end_date)
            if image is None:
                logging.warning(f"Nenhuma imagem para o lote {idx+1}")
                continue

            tile_filename = f"{satelite}_tile_{idx+1}_{radius_km}_{start_date}_{end_date}.tif"
            logging.info(f"Nome do arquivo para o tile {idx+1}: {tile_filename}")
            tile_filepath = os.path.join(tile_dir, tile_filename)  # Caminho completo apenas para temp_files
            images.append(image)
            filenames.append(tile_filename)  # Apenas o nome do arquivo para download_async

        if images:
            logging.info(f"Lista de filenames para download: {filenames}")
            image_downloader.download_async(images, filenames)
            temp_files.extend([os.path.join(tile_dir, fname) for fname in filenames])
            logging.info(f"Lista de temp_files após download: {temp_files}")
        else:
            logging.error("Nenhum lote foi baixado com sucesso.")
            return

        # Verificação de quais arquivos foram baixados
        for filename in temp_files:
            if os.path.exists(filename):
                logging.info(f"Arquivo baixado com sucesso: {filename}")
            else:
                logging.error(f"Erro: arquivo {filename} não foi encontrado após o download")

        # Filtragem de arquivos que existem
        temp_files = [f for f in temp_files if os.path.exists(f)]

        # Cria o mosaico apenas se houver arquivos válidos
        final_filename = f"{satelite}_{lat}_{lon}_{radius_km}km_{start_date}_{end_date}_mosaic.tif"
        final_filepath = os.path.join(output_dir, final_filename)
        if temp_files:
            mosaic_tiles(temp_files, final_filepath)
            logging.info(f"Mosaico final criado em: {final_filepath}")
        else:
            logging.error("Nenhum arquivo de tile foi baixado com sucesso. Mosaico não criado.")
    else:
        image = fetcher.fetch_image(satelite, main_bbox, start_date, end_date)
        if image is None:
            logging.warning('Nenhuma imagem encontrada')
        filename = f'{satelite}_{lat}_{lon}_{radius_km}km_{start_date}_{end_date}.tif'
        image_downloader.download(image, filename)

if __name__ == "__main__":
    app()