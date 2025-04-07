import openeo
import math
import logging
import os
import typer
import rasterio
from rasterio.merge import merge
import rasterio.warp
from concurrent.futures import ThreadPoolExecutor
import time
import geopandas as gpd
import re
from shapely.wkt import loads
from rasterio.errors import RasterioIOError
from rasterio.merge import merge
from openeo.rest.connection import OpenEoApiError
import subprocess




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
                    bands=["B02", "B03", "B04","B08"],
                    max_cloud_cover=40,
                )

                image = image.resample_spatial(resolution=10)
                image = image.reduce_dimension(dimension='t', reducer='median')


            elif satelite == 'SENTINEL2_L1C':
                image = self.connection.load_collection(
                    "SENTINEL2_L2A",
                    spatial_extent=bounding_box,
                    temporal_extent = [start_date, end_date],
                    bands=["B02", "B03", "B04","B08"],
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

    def download(self, image, filename,delay, retry=2):
        try:
            if image is None:
                logging.error("Tentativa de download com imagem inválida")
                raise ValueError("Imagem inválida.")
            time.sleep(delay)

            filepath = os.path.join(self.output_dir, filename)
            logging.info(f"filepath calculado: {filepath}")
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            logging.info(f"Iniciando download da imagem para {filepath}...")
            image.download(filepath)
            logging.info("Download concluído")
            return filepath

        except OpenEoApiError as e:
            if "429" in str(e) and retry > 0:
                logging.warning(f"Erro 429: Too Many Requests. Tentando novamente ({retry} tentativas restantes)...")
                time.sleep(10)  # Espera antes de tentar novamente
                return self.download(image, filename, delay, retry - 1)
            else:
                logging.error(f"Erro ao fazer download da imagem: {str(e)}")
                raise RuntimeError("Erro ao fazer download da imagem", e)

        except Exception as e:
            logging.error(f"Erro ao fazer download da imagem: {str(e)}")
            raise RuntimeError("Erro ao fazer download da imagem", e)
        
    def download_async(self,image_list,filenames):
        def process_download(image, filename,delay):
            return self.download(image, filename,delay)

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for idx, (img, fname) in enumerate(zip(image_list, filenames)):
                delay = idx * 2
                time.sleep(7)
                future = executor.submit(process_download, img, fname, delay)
                futures.append(future)

            # Verificação dos resultados do download
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Erro no download assíncrono: {e}")
        
class BBoxProcessor:
    def __init__(self, bbox, tile_size_km, center_lat, raio_condicional):
        self.bbox = bbox
        self.tile_size_km = tile_size_km
        self.center_lat = center_lat
        self.raio_condicional = raio_condicional
             
    def divide_bbox(self):

        radius_km = ((self.bbox['north'] - self.bbox['south']) * 111) / 2
        if int(self.raio_condicional) >= 80:
            desired_divisions = 5
        elif int(self.raio_condicional) >= 50 and int(self.raio_condicional) <= 79:
            desired_divisions = 4
        else:
            desired_divisions = 3
            logging.info('Entrei no if condicional')

        effective_tile_size = max(self.tile_size_km, (2 * radius_km) / desired_divisions)
        
        delta_lat = effective_tile_size / 111.0
        delta_lon = effective_tile_size / (111.0 * math.cos(math.radians(self.center_lat)))
        
        bboxes = []
        current_lat = self.bbox['south']
        while current_lat < self.bbox['north']:
            current_lon = self.bbox['west']
            while current_lon < self.bbox['east']:
                sub_bbox = {
                    'west': current_lon,
                    'south': current_lat,
                    'east': min(current_lon + delta_lon, self.bbox['east']),
                    'north': min(current_lat + delta_lat, self.bbox['north']),
                    'crs': 'EPSG:4326'
                }
                bboxes.append(sub_bbox)
                current_lon += delta_lon
            current_lat += delta_lat
        return bboxes

class TileMosaicker:
    def __init__(self, tile_files, output_path):
        self.tile_files = tile_files
        self.output_path = output_path

    def mosaic_tiles(self):
        src_files = []
        band_count = None
        valid_files = []
        common_crs = "EPSG:32721"  # CRS comum definido

        for fp in self.tile_files:
            try:
                with rasterio.open(fp) as src:
                    if src.count == 0:
                        raise rasterio.errors.RasterioIOError(f"Arquivo {fp} não possui bandas válidas.")

                    if band_count is None:
                        band_count = src.count
                    elif src.count != band_count:
                        logging.warning(f"Arquivo {fp} possui {src.count} bandas, diferente do esperado ({band_count}). Ignorando.")
                        continue

                    if src.crs != common_crs:
                        logging.warning(f"Arquivo {fp} tem CRS diferente ({src.crs}). Reprojetando...")

                        reprojected_fp = fp.replace(".tif", "_reprojected.tif")
                        cmd = [
                            "gdalwarp",
                            "-t_srs", common_crs,
                            "-dstnodata", "-32768",
                            "-overwrite",
                            fp,
                            reprojected_fp
                        ]

                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode != 0:
                            logging.error(f"Erro ao reprojetar {fp}: {result.stderr}")
                            continue

                        valid_files.append(reprojected_fp)
                        src_files.append(rasterio.open(reprojected_fp))
                        continue

                    valid_files.append(fp)
                    src_files.append(rasterio.open(fp))

            except rasterio.errors.RasterioIOError as e:
                logging.error(f"Erro ao abrir {fp}: {e}")
                os.remove(fp)
                logging.info(f"Arquivo corrompido {fp} foi removido.")

        if not src_files:
            logging.error("Nenhum arquivo válido para mosaico.")
            return None

        # Fusão dos arquivos ajustados
        mosaic, out_trans = rasterio.merge.merge(src_files)

        out_meta = src_files[0].meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_trans,
            "count": src_files[0].count,
            "dtype": src_files[0].dtypes[0],
            "crs": common_crs
        })

        with rasterio.open(self.output_path, "w", **out_meta) as dest:
            dest.write(mosaic)

        for src in src_files:
            src.close()

        logging.info(f"Mosaico salvo em: {self.output_path}")
        return self.output_path


app = typer.Typer()


TILES_PARANA = [
    "21JYM", "21JYN", "21KYP","22JBS","22JBT", "22KBU", "22KBV", "22JCS", "22JCT", 
    "22KCU", "22KCV", "22JDS", "22JDT", "22KDU", "22KDV","22JES", "22JET", "22KEU", 
    "22KEV", "22JFS", "22JFT", "22KFU", "22JGS", "22JGT"
]

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

    fetcher = SatelliteImageFetcher(copernicus_conn.get_connection())
    image_downloader = ImageDownloader(output_dir)


    if tile_id in ["Paraná", "parana"]:
        logging.info("Iniciando download para todos os tiles do Paraná...")
        
        tile_dir = os.path.join(output_dir, "tiles")
        os.makedirs(tile_dir, exist_ok=True)
        
        tile_mosaic_files = []
        
        for tile in TILES_PARANA:
            logging.info(f"Processando tile {tile}...")
            
            tile_grid = gpd.read_file(tile_grid_path)
            tile_grid = tile_grid[tile_grid["NAME"] == tile]

            if tile_grid.empty:
                logging.warning(f"Tile {tile} não encontrado na grade Sentinel-2. Pulando...")
                continue

            tile_geometry = tile_grid.geometry.iloc[0]
            minx, miny, maxx, maxy = tile_geometry.bounds

            main_bbox = {
                "west": minx,
                "south": miny,
                "east": maxx,
                "north": maxy,
                "crs": "EPSG:4326"
            }

            lat = (maxy + miny) / 2
            lon = (maxx + minx) / 2
            bbox_width_km = ((maxx - minx) * 111 * math.cos(math.radians(lat)))
            bbox_height_km = ((maxy - miny) * 111)
            radius_km = max(bbox_width_km, bbox_height_km) / 2

            processor = BBoxProcessor(main_bbox, tile_size_km, lat, radius_km)
            tiles = processor.divide_bbox()
            
            image_downloader = ImageDownloader(tile_dir)
            images = []
            filenames = []

            for idx, tile_bbox in enumerate(tiles):
                logging.info(f"Lote {idx+1}/{len(tiles)} do tile {tile}...")
                
                image = fetcher.fetch_image(satelite, tile_bbox, start_date, end_date)
                if image is None:
                    logging.warning(f"Nenhuma imagem encontrada para lote {idx+1}")
                    continue
                
                tile_filename = f"{satelite}_{tile}_{lat:.5f}_{lon:.5f}_tile_{idx+1}_{radius_km:.2f}km_{start_date}_{end_date}.tif"
                filenames.append(tile_filename)
                images.append(image)

            if images:
                image_downloader.download_async(images, filenames)
                tile_files = [os.path.join(tile_dir, fname) for fname in filenames]
                # Verifica se os arquivos baixados existem
                tile_files = [f for f in tile_files if os.path.exists(f)]
            else:
                logging.warning(f"Nenhum dado baixado para tile {tile}.")
                continue

            tile_mosaic_output = os.path.join(tile_dir, f"{satelite}_{tile}_{start_date}_{end_date}_mosaic.tif")
            if tile_files:
                processor_mosaic = TileMosaicker(tile_files, tile_mosaic_output)
                processor_mosaic.mosaic_tiles()
                logging.info(f"Mosaico do tile {tile} criado: {tile_mosaic_output}")
                tile_mosaic_files.append(tile_mosaic_output)
            else:
                logging.warning(f"Nenhum mosaico criado para tile {tile}.")

        if tile_mosaic_files:
            parana_mosaic_output = os.path.join(output_dir, f"{satelite}_Parana_mosaic_{start_date}_{end_date}_2.tif")
            processor_mosaic = TileMosaicker(tile_mosaic_files, parana_mosaic_output)
            processor_mosaic.mosaic_tiles()
            logging.info(f"Mosaico final do Paraná criado em: {parana_mosaic_output}")
        else:
            logging.error("Nenhum mosaico foi criado para o Paraná.")

    else:
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

            lat = (maxy + miny) / 2
            lon = (maxx + minx) / 2

            bbox_width_km = ((maxx - minx) * 111 * math.cos(math.radians(lat)))
            bbox_height_km = ((maxy - miny) * 111)
            radius_km = max(bbox_width_km, bbox_height_km) / 2

            logging.info(f"Raio estimado do BBOX do tile {tile_id}: {radius_km:.2f} km")

        elif lat is not None and lon is not None:
            main_bbox = BoundingBoxCalculator.calcular(lat, lon, radius_km)
            logging.info("Processando sem tile ID...")
        else:
            logging.error("É necessário fornecer latitude/longitude ou um ID de tile Sentinel-2.")
            raise ValueError("Faltam parâmetros para definir a área de interesse.")

        logging.info(f"BBox principal: {main_bbox}")

        if radius_km >= 21:
            processor = BBoxProcessor(main_bbox, tile_size_km, lat, radius_km)
            tiles = processor.divide_bbox()
            logging.info(f"Área dividida em {len(tiles)} lotes")

            temp_files = []
            tile_dir = os.path.join(output_dir, "tiles")
            tile_dir = os.path.abspath(tile_dir)

            if not os.path.exists(tile_dir):
                os.makedirs(tile_dir, exist_ok=True)

            image_downloader = ImageDownloader(tile_dir)
            images = []
            filenames = []

            for idx, tile_bbox in enumerate(tiles):
                logging.info(f"Lote {idx+1}/{len(tiles)} sendo processado...")
                image = fetcher.fetch_image(satelite, tile_bbox, start_date, end_date)

                if image is None:
                    logging.warning(f"Nenhuma imagem encontrada para o lote {idx+1}")
                    continue

                if tile_id:
                    tile_filename = f"{satelite}_{tile_id}_{lat:.5f}_{lon:.5f}_tile_{idx+1}_{radius_km:.2f}km_{start_date}_{end_date}.tif"
                else:
                    tile_filename = f"{satelite}_{lat:.5f}_{lon:.5f}_tile_{idx+1}_{radius_km:.2f}km_{start_date}_{end_date}.tif"

                filenames.append(tile_filename)
                images.append(image)

            if images:
                image_downloader.download_async(images, filenames)
                temp_files.extend([os.path.join(tile_dir, fname) for fname in filenames])
            else:
                logging.error("Nenhum lote foi baixado com sucesso.")
                return

            for filename in temp_files:
                if os.path.exists(filename):
                    logging.info(f"Arquivo baixado com sucesso: {filename}")
                else:
                    logging.error(f"Erro: arquivo {filename} não foi encontrado")

            temp_files = [f for f in temp_files if os.path.exists(f)]

            if tile_id:
                final_filename = f"{satelite}_{tile_id}_{lat:.5f}_{lon:.5f}_{radius_km:.2f}km_{start_date}_{end_date}_mosaic.tif"
            else:
                final_filename = f"{satelite}_{lat:.5f}_{lon:.5f}_{radius_km:.2f}km_{start_date}_{end_date}_mosaic.tif"

            final_filepath = os.path.join(output_dir, final_filename)

            if temp_files:
                processor_mosaic = TileMosaicker(temp_files, final_filepath)
                processor_mosaic.mosaic_tiles()
                logging.info(f"Mosaico final criado em: {final_filepath}")
            else:
                logging.error("Nenhum arquivo de tile foi baixado com sucesso. Mosaico não criado.")
        else:
            image = fetcher.fetch_image(satelite, main_bbox, start_date, end_date)
            if image is None:
                logging.warning("Nenhuma imagem encontrada")
                return

            if tile_id:
                filename = f"{satelite}_{tile_id}_{lat:.5f}_{lon:.5f}_{radius_km:.2f}km_{start_date}_{end_date}.tif"
            else:
                filename = f"{satelite}_{lat:.5f}_{lon:.5f}_{radius_km:.2f}km_{start_date}_{end_date}.tif"

            image_downloader.download(image, filename,delay=0)

if __name__ == "__main__":
    app()