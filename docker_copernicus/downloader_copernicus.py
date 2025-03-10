import openeo
import math
import logging
import os
import typer
import rasterio
from rasterio.merge import merge


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
                    bands=["B02", "B03", "B04", "B08"],
                    max_cloud_cover=20,
                )

                image = image.resample_spatial(resolution=10)
                image = image.reduce_dimension(dimension='t', reducer='median')


            elif satelite == 'SENTINEL2_L1C':
                image = self.connection.load_collection(
                    "SENTINEL2_L2A",
                    spatial_extent=bounding_box,
                    temporal_extent = [start_date, end_date],
                    bands=["B02", "B03", "B04", "B08"],
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
            os.makedirs(self.output_dir) 

    def download(self,image, filename):
        try:
            if image is None:
                logging.error("Tentativa de download com imagem inválida")
                raise ValueError("Imagem inválida.")
            
            filepath = os.path.join(self.output_dir, filename)
            logging.info(f"Iniciando download da imagem para {filepath}...")
            image.download(filepath)
            # job = image.execute_batch(filepath)
            # results = job.get_results()
            # results.download_file(filepath)
            logging.info(f'Download concluído')
            return filepath

        except Exception as e:
            logging.error(f"Erro ao fazer download da imagem: {str(e)}")
            raise RuntimeError("Erro ao fazer download da imagem", e)
        
def divide_bbox(bbox, tile_size_km, center_lat,raio_condicional):

    radius_km = ((bbox['north'] - bbox['south']) * 111) / 2
    if raio_condicional >= 50:
        desired_divisions = 4
    else:
        desired_divisions = 3
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
    for fp in tile_files:
        src = rasterio.open(fp)
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
    lat: float = typer.Argument(..., help="Latitude da área de interesse"),
    lon: float = typer.Argument(..., help="Longitude da área de interesse"),
    radius_km: float = typer.Argument(10.0, help="Raio da área de interesse em km"),
    start_date: str = typer.Argument(..., help="Data de início (YYYY-MM-DD)"),
    end_date: str = typer.Argument(..., help="Data final (YYYY-MM-DD)"),
    client_id: str = typer.Option('sh-780be612-cdd5-46c2-be80-016e3d9e3941', help="Client ID da conta Copernicus"),
    client_secret: str = typer.Option('wNqrCLhYnogycEclvClgVfrCRzNxjzec', help="Client Secret da conta Copernicus"),
    output_dir: str = typer.Option("docker_copernicus\\imagens", help="Diretório de saída para salvar as imagens"),
    tile_size_km: float = typer.Option(18.0)
):
    copernicus_conn = CopernicusConnection(client_id, client_secret)
    copernicus_conn.initialize()

    main_bbox = BoundingBoxCalculator.calcular(lat, lon, radius_km)
    logging.info(f"BBox principal: {main_bbox}")
    if radius_km >=21:
        tiles = divide_bbox(main_bbox, tile_size_km, lat,radius_km)
        logging.info(f"Área dividida em {len(tiles)} lotes")

        fetcher = SatelliteImageFetcher(copernicus_conn.get_connection())
        temp_files = []
        tile_dir = os.path.join(output_dir, "tiles")
        if not os.path.exists(tile_dir):
            os.makedirs(tile_dir)

        for idx, tile_bbox in enumerate(tiles):
            logging.info(f"Baixando lote {idx+1}/{len(tiles)} com bbox: {tile_bbox}")
            image = fetcher.fetch_image(satelite, tile_bbox, start_date, end_date)
            if image is None:
                logging.warning(f"Nenhuma imagem para o lote {idx+1}")
                continue
            tile_filename = f"{satelite}_tile_{idx+1}_{radius_km}_{start_date}_{end_date}.tif"
            try:
                ImageDownloader(tile_dir).download(image, tile_filename)
                temp_files.append(os.path.join(tile_dir, tile_filename))
            except Exception as e:
                logging.error(f"Erro ao baixar o lote {idx+1}: {e}")

        if not temp_files:
            logging.error("Nenhum lote foi baixado com sucesso.")
            return

        final_filename = f"{satelite}_{lat}_{lon}_{radius_km}km_{start_date}_{end_date}_mosaic.tif"
        final_filepath = os.path.join(output_dir, final_filename)
        mosaic_tiles(temp_files, final_filepath)
        logging.info(f"Mosaico final criado em: {final_filepath}")
    else:
        fetcher = SatelliteImageFetcher(copernicus_conn.get_connection())
        image = fetcher.fetch_image(satelite, main_bbox, start_date, end_date)
        if image is None:
            logging.warning('Nenhuma imagem encontrada')
        filename = f'{satelite}_{lat}_{lon}_{radius_km}km_{start_date}_{end_date}.tif'
        image_downloader = ImageDownloader(output_dir)
        image_downloader.download(image, filename)


if __name__ == "__main__":
    app()