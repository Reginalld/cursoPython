import pystac_client
import os
from urllib.parse import urlparse
import requests
from pystac import Asset
from tqdm import tqdm
import os
from urllib.parse import urlparse
import numpy as np
import requests
import rasterio
from rasterio.plot import reshape_as_image
from pystac import Asset
from tqdm import tqdm
from PIL import Image
import logging
import math
import typer
from shapely.wkt import loads
import geopandas as gpd
import re
import subprocess
from rasterio.merge import merge
import time
import planetary_computer
from pystac.extensions.eo import EOExtension as eo




logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("microsoft\\log\\brazil_data_cube_log.txt"),
        logging.StreamHandler()
    ]
)

class BdcConnection:
    def __init__(self):
        self.connection = None

    def initialize(self):
        try:
            logging.info("Inicializando a conexão com o Microsoft planetary computer...")
            self.connection = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",
                                                         modifier=planetary_computer.sign_inplace,)
        except Exception as e:
            logging.critical(f"Erro ao inicializar o BDC: {e}", exc_info=True)
            raise RuntimeError(f"Erro ao inicializar o BDC {e}")
    
    def get_connection(self):
        if self.connection is None:
            self.initialize()
        return self.connection
    
class BoundingBoxCalculator:
    @staticmethod
    def calcular(lat, lon, raio_km):
        raio_graus_lat = raio_km / 111
        raio_graus_lon = raio_km / (111 * math.cos(math.radians(lat)))

        return [
            lon - raio_graus_lon,
            lat - raio_graus_lat,
            lon + raio_graus_lon,
            lat + raio_graus_lat,
        ]

class SatelliteImageFetcher:
    def __init__(self, connection):
        self.connection = connection
    
    def fetch_image(self, satelite, bounding_box, start_date, end_date, max_cloud_cover):
        try:
            logging.info(f"Buscando imagens do {satelite}...")

            filt = None
            max_items = 10  

            if satelite == 'S2_L2A-1':
                ...
            elif satelite == 'landsat-c2-l2':
                ...
            else:
                logging.warning(f"Satélite {satelite} não suportado!")
                raise ValueError("Satélite não suportado.")

            search_result = self.connection.search(
                bbox=bounding_box,
                datetime=[start_date, end_date],
                collections=[satelite],
                query={"eo:cloud_cover": {"lt":10}}
            )

            items = search_result.item_collection()

            if not items:
                logging.warning("Nenhuma imagem encontrada.")
                return None
            

            selected_items = min(items, key=lambda item: eo.ext(item).cloud_cover)

            if not selected_items:
                logging.warning("Nenhuma imagem.")
                return None

            # Ordena pela menor cobertura de nuvem
            items = sorted(items, key=lambda item: item.properties['eo:cloud_cover'])

            # Seleciona o melhor item
            logging.info(len(items))
            best_item = items[0]
            logging.info(best_item.properties)
            cloud_cover = best_item.properties['eo:cloud_cover']
            logging.info(f"Imagem selecionada com {cloud_cover}% de nuvem.")

            return best_item.assets

        except Exception as e:
            logging.error(f"Erro ao obter imagem do {satelite}: {e}", exc_info=True)
            return None

        
class ImagemDownloader:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.create_output()

    def create_output(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def download(self, asset, filename, request_options={}):
            try:
                if asset is None:
                    logging.error("Tentativa de download com asset inválido")
                    raise ValueError("Asset inválido.")
                
                filepath = os.path.join(self.output_dir, filename)
                logging.info(f"Iniciando download da imagem para {filepath}...")

                response = requests.get(asset.href, stream=True, **request_options)
                total_bytes = int(response.headers.get('content-length', 0))
                chunk_size = 1024 * 16
                
                with tqdm.wrapattr(open(filepath, 'wb'), 'write', miniters=1, total=total_bytes, desc=os.path.basename(filepath)) as fout:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        fout.write(chunk)

                return filepath  # Retorna o caminho do arquivo baixado

            except Exception as e:
                logging.error(f"Erro ao fazer download da imagem: {str(e)}")
                raise RuntimeError("Erro ao fazer download da imagem", e)
        
def merge_rgb_tif(r, g, b, output_path, satelite):
    """Combina as bandas R, G e B e salva como um arquivo GeoTIFF normalizado."""
    with rasterio.open(r) as red, \
         rasterio.open(g) as green, \
         rasterio.open(b) as blue:

        # Lê os dados das bandas
        r = red.read(1)
        g = green.read(1)
        b = blue.read(1)

        def normalize_soft(array):
            """Normalização min-max suave (usada pelo S2-16D-2)"""
            array_min, array_max = array.min(), array.max()
            if array_max - array_min == 0:
                return np.zeros_like(array, dtype=np.uint8)
            return ((array - array_min) / (array_max - array_min) * 255).astype(np.uint8)

        def normalize_landsat_c2(array):
            """Normalização baseada em reflectância para Landsat Collection 2 Level 2"""
            array = array.astype("float32") / 10000.0
            array = np.clip(array, 0, 1)
            return (array * 255).astype(np.uint8)

        def normalize_percentile_common(r, g, b, gamma=1.0):
            """Normalização com percentil comum entre bandas e correção gama"""
            stacked = np.stack([r, g, b])
            p2, p98 = np.percentile(stacked, (2, 98))

            def apply(arr):
                arr = np.clip(arr, p2, p98)
                arr = (arr - p2) / (p98 - p2)
                arr = np.power(arr, gamma)
                return (arr * 255).astype(np.uint8)

            return apply(r), apply(g), apply(b)

        # Aplica a normalização apropriada
        if satelite == 'S2-16D-2':
            r_norm, g_norm, b_norm = normalize_percentile_common(r, g, b, gamma=1.1)
        elif satelite == 'landsat-c2-l2':
            r_norm = normalize_landsat_c2(r)
            g_norm = normalize_landsat_c2(g)
            b_norm = normalize_landsat_c2(b)
        else:
            r_norm, g_norm, b_norm = normalize_percentile_common(r, g, b)

        # Empilha as bandas normalizadas
        rgb = np.stack([r_norm, g_norm, b_norm], axis=0)

        # Cria metadados para o novo arquivo
        profile = red.profile
        profile.update(
            count=3,
            dtype=rasterio.uint8,
            driver="GTiff"
        )

        # Salva o arquivo GeoTIFF
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(rgb[0], 1)
            dst.write(rgb[1], 2)
            dst.write(rgb[2], 3)

        print(f"Imagem RGB GeoTIFF salva em: {output_path}")



def mosaic_tiles(tile_files, output_path):
    src_files = []
    band_count = None
    valid_files = []
    common_crs = "EPSG:32721"  # CRS comum definido

    for fp in tile_files:
        try:
            with rasterio.open(fp) as src:
                if src.count == 0:
                    raise rasterio.errors.RasterioIOError(f"Arquivo {fp} não possui bandas válidas.")

                if band_count is None:
                    band_count = src.count
                elif src.count != band_count:
                    logging.warning(f"Arquivo {fp} possui {src.count} bandas, diferente do esperado ({band_count}). Ignorando.")
                    continue
                logging.info(src.crs)
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
                    time.sleep(5)
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

    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(mosaic)

    for src in src_files:
        src.close()

    logging.info(f"Mosaico salvo em: {output_path}")
    return output_path
        
app = typer.Typer()

TILES_PARANA = [
    "21JYM","21JYN", "21KYP","22JBS","22JBT","22KBU","22KBV","22JCS", "22JCT", "22KCU", "22KCV", "22JDS",
"22JDT", "22KDU", "22KDV","22JES", "22JET", "22KEU", 
    "22KEV", "22JFS", "22JFT", "22KFU", "22JGS", "22JGT"
]






@app.command()
def main(
    satelite: str = typer.Argument(..., help="Escolha um satélite (???)"),
    lat: float = typer.Option(None, help="Latitude da área de interesse"),
    lon: float = typer.Option(None, help="Longitude da área de interesse"),
    tile_id: str = typer.Option(None, help="ID do tile Sentinel-2 (ex: '21KXP')"),
    radius_km: float = typer.Option(10.0, help="Raio da área de interesse em km"),
    start_date: str = typer.Argument(..., help="Data de início (YYYY-MM-DD)"),
    end_date: str = typer.Argument(..., help="Data final (YYYY-MM-DD)"),
    output_dir: str = typer.Option("microsoft\\images", help="Diretório de saída para salvar as imagens"),
    tile_grid_path: str = typer.Option("microsoft\\shapefile_ids\\grade_sentinel_brasil.shp"),
    max_cloud_cover: float = typer.Option(20.0, help="Máximo de nuvens")
):
    bdc_conn = BdcConnection()
    fetcher = SatelliteImageFetcher(bdc_conn.get_connection())
    image_downloader = ImagemDownloader(output_dir)

    if tile_id in ["Paraná", "parana"]:
        logging.info("Iniciando todos os downloads do Paraná")

        tile_mosaic_files = []
        for tile in TILES_PARANA:
            logging.info(f"Processando tile {tile}...")
            tile_grid = gpd.read_file(tile_grid_path)
            tile_grid = tile_grid[tile_grid["NAME"] == tile]

            if tile_grid.empty:
                logging.warning(f"Tile {tile} não encontrado na grade Sentinel-2. Pulando...")
                continue

           # Fator de redução para diminuir a bounding box (exemplo: reduzir em 2% para evitar margens excessivas)
            REDUCTION_FACTOR = 0.2

            tile_geometry = tile_grid.geometry.iloc[0]
            minx, miny, maxx, maxy = tile_geometry.bounds

            # Ajuste para reduzir a bounding box em um pequeno percentual
            center_x = (minx + maxx) / 2
            center_y = (miny + maxy) / 2
            width = (maxx - minx) * REDUCTION_FACTOR
            height = (maxy - miny) * REDUCTION_FACTOR

            new_minx = center_x - (width / 2)
            new_maxx = center_x + (width / 2)
            new_miny = center_y - (height / 2)
            new_maxy = center_y + (height / 2)

            main_bbox = [new_minx, new_miny, new_maxx, new_maxy]

            logging.info(f"Main_bbox ajustado: {main_bbox} do tile: {tile}")

            image_assets = fetcher.fetch_image(satelite, main_bbox, start_date, end_date, max_cloud_cover)
            if not image_assets:
                logging.warning(f"Nenhuma imagem encontrada para tile {tile}.")
                continue

            logging.info("Baixando e processando imagens...")
            r = image_downloader.download(image_assets['red'], f"{satelite}_{tile}_{start_date}_{end_date}_red")
            g = image_downloader.download(image_assets['green'], f"{satelite}_{tile}_{start_date}_{end_date}_green")
            b = image_downloader.download(image_assets['blue'], f"{satelite}_{tile}_{start_date}_{end_date}_blue")
            tile_mosaic_output = os.path.join(output_dir, f"{satelite}_{tile}_{start_date}_{end_date}_RGB.tif")
            merge_rgb_tif(r, g, b, tile_mosaic_output,satelite)
            tile_mosaic_files.append(tile_mosaic_output)

        if tile_mosaic_files:
            parana_mosaic_output = os.path.join(output_dir, f"{satelite}_Parana_mosaic_{start_date}_{end_date}.tif")
            mosaic_tiles(tile_mosaic_files, parana_mosaic_output)
            logging.info(f"Mosaico final do Paraná criado em: {parana_mosaic_output}")
        else:
            logging.error("Nenhum mosaico foi criado para o Paraná.")
    else:
        if tile_id:
            logging.info(f"Buscando geometria para o tile {tile_id} na grade do Sentinel-2...")
            tile_grid = gpd.read_file(tile_grid_path)
            tile_grid = tile_grid[tile_grid["NAME"] == tile_id]

            if tile_grid.empty:
                logging.error(f"Tile {tile_id} não encontrado na grade Sentinel-2.")
                raise ValueError("Tile ID inválido.")

            REDUCTION_FACTOR = 0.2
            tile_geometry = tile_grid.geometry.iloc[0]
            minx, miny, maxx, maxy = tile_geometry.bounds

            center_x = (minx + maxx) / 2
            center_y = (miny + maxy) / 2
            width = (maxx - minx) * REDUCTION_FACTOR
            height = (maxy - miny) * REDUCTION_FACTOR

            new_minx = center_x - (width / 2)
            new_maxx = center_x + (width / 2)
            new_miny = center_y - (height / 2)
            new_maxy = center_y + (height / 2)

            main_bbox = [new_minx, new_miny, new_maxx, new_maxy]

            lat = (maxy + miny) / 2
            lon = (maxx + minx) / 2
            bbox_width_km = ((maxx - minx) * 111 * math.cos(math.radians(lat)))
            bbox_height_km = ((maxy - miny) * 111)
            radius_km = max(bbox_width_km, bbox_height_km) / 2

        elif lat is not None and lon is not None:
            main_bbox = BoundingBoxCalculator.calcular(lat, lon, radius_km)
            logging.info("Processando sem tile ID...")
        else:
            logging.error("É necessário fornecer latitude/longitude ou um ID de tile Sentinel-2.")
            raise ValueError("Faltam parâmetros para definir a área de interesse.")

        logging.info(f"BBox principal: {main_bbox}")
        image_assets = fetcher.fetch_image(satelite, main_bbox, start_date, end_date, max_cloud_cover)
        if not image_assets:
            logging.warning("Nenhuma imagem encontrada")
            return

        logging.info("Baixando e processando imagens...")
        r = image_downloader.download(image_assets['red'], f"{radius_km}_{satelite}_{lat}_{lon}_{start_date}_{end_date}_red")
        g = image_downloader.download(image_assets['green'], f"{radius_km}_{satelite}_{lat}_{lon}_{start_date}_{end_date}_green")
        b = image_downloader.download(image_assets['blue'], f"{radius_km}_{satelite}_{lat}_{lon}_{start_date}_{end_date}_blue")
        output_path = os.path.join(output_dir, f"{radius_km}_{satelite}_{lat}_{lon}_{start_date}_{end_date}_RGB.tif")
        merge_rgb_tif(r, g, b, output_path,satelite)

if __name__ == "__main__":
    app()