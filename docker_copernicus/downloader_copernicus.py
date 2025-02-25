import openeo
import math
import logging
import os
import typer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("log/copernicus_log.txt"),
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

            elif satelite == 'LANDSAT8_L2':
                image = self.connection.load_collection(
                    "LANDSAT8_L2",
                    spatial_extent=bounding_box,
                    temporal_extent=[start_date, end_date],
                    bands=["B02", "B03", "B04", "B05"],
                    max_cloud_cover=20,
                )
                image = image.resample_spatial(resolution=30)
                image = image.reduce_dimension(dimension='t', reducer='median')

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
            job = image.execute_batch(filepath)
            results = job.get_results()
            results.download_file(filepath)
            return filepath

        except Exception as e:
            logging.error(f"Erro ao fazer download da imagem: {str(e)}")
            raise RuntimeError("Erro ao fazer download da imagem", e)


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
    output_dir: str = typer.Option("imagens", help="Diretório de saída para salvar as imagens"),
):
    copernicus_conn = CopernicusConnection(client_id, client_secret)
    copernicus_conn.initialize()

    bounding_box = BoundingBoxCalculator.calcular(lat, lon, radius_km)

    fetcher = SatelliteImageFetcher(copernicus_conn.get_connection())
    image = fetcher.fetch_image(satelite, bounding_box, start_date, end_date)

    if image is None:
        logging.warning('Nenhuma imagem encontrada')
        return

    filename = f'{satelite}_{lat}_{lon}_{radius_km}km_{start_date}_{end_date}.tif'
    image_downloader = ImageDownloader(output_dir)
    image_downloader.download(image, filename)


if __name__ == "__main__":
    app()