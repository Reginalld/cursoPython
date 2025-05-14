# stac_downloader.py

import typer
from brazil_data_cube.bdc_connection import BdcConnection
from brazil_data_cube.downloader.fetcher import SatelliteImageFetcher
from brazil_data_cube.downloader.image_downloader import ImagemDownloader
from brazil_data_cube.bounding_box_handler import BoundingBoxHandler
from brazil_data_cube.processors.image_processor import ImageProcessor
from brazil_data_cube.tile_processor import TileProcessor
import os
import logging

from brazil_data_cube.logger import setup_logger

setup_logger()

logger = logging.getLogger(__name__)

app = typer.Typer()

@app.command()
def main(
    satelite: str = typer.Argument(..., help="Escolha um satélite (ex: S2_L2A-1)"),
    lat: float = typer.Option(None, help="Latitude da área de interesse"),
    lon: float = typer.Option(None, help="Longitude da área de interesse"),
    tile_id: str = typer.Option(None, help="ID do tile Sentinel-2 (ex: '21KXP')"),
    radius_km: float = typer.Option(10.0, help="Raio da área de interesse em km"),
    start_date: str = typer.Argument(..., help="Data de início (YYYY-MM-DD)"),
    end_date: str = typer.Argument(..., help="Data final (YYYY-MM-DD)"),
    output_dir: str = typer.Option("imagens", help="Diretório de saída para salvar as imagens"),
    tile_grid_path: str = typer.Option("shapefile_ids\\grade_sentinel_brasil.shp"),
    max_cloud_cover: float = typer.Option(20.0, help="Máximo de nuvens")
):
    """
    Baixa e processa imagens de satélite do Brazil Data Cube.
    """
    # Inicializa dependências
    bdc_conn = BdcConnection().get_connection()
    fetcher = SatelliteImageFetcher(bdc_conn)
    downloader = ImagemDownloader(output_dir)
    bbox_handler = BoundingBoxHandler(reduction_factor=0.2)

    if tile_id in ["Paraná", "parana"]:
        TileProcessor(fetcher, downloader, output_dir, tile_grid_path, max_cloud_cover).processar_tiles_parana(satelite, start_date, end_date)
    else:
        main_bbox, lat_final, lon_final, radius_final = bbox_handler.obter_bounding_box(tile_id, lat, lon, radius_km, tile_grid_path)

        image_assets = fetcher.fetch_image(satelite, main_bbox, start_date, end_date, max_cloud_cover, tile_grid_path, tile_id or "")
        if not image_assets:
            print("Nenhuma imagem encontrada.")
            return

        r = downloader.download(image_assets['B04'], f"{radius_final:.2f}KM_{satelite}_{lat_final:.3f}_{lon_final:.3f}_{start_date}_{end_date}_red")
        g = downloader.download(image_assets['B03'], f"{radius_final:.2f}KM_{satelite}_{lat_final:.3f}_{lon_final:.3f}_{start_date}_{end_date}_green")
        b = downloader.download(image_assets['B02'], f"{radius_final:.2f}KM_{satelite}_{lat_final:.3f}_{lon_final:.3f}_{start_date}_{end_date}_blue")

        output_path = os.path.join(output_dir, f"{radius_final:.2f}KM_{satelite}_{lat_final:.3f}_{lon_final:.3f}_{start_date}_{end_date}_RGB.tif")
        ImageProcessor(satelite).merge_rgb_tif(r, g, b, output_path)

if __name__ == "__main__":
    app()