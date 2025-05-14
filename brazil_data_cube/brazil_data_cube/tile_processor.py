# brazil_data_cube/tile_processor.py

import time
import logging
import geopandas as gpd
from .config import TILES_PARANA
from .bounding_box_handler import BoundingBoxHandler
from .logger import ResultManager
from brazil_data_cube.processors.image_processor import ImageProcessor
from brazil_data_cube.processors.mosaic_generator import MosaicGenerator
import os

logger = logging.getLogger(__name__)

class TileProcessor:
    SAT_SUPPORTED = ['S2_L2A-1', 'S2-16D-2']

    def __init__(self, fetcher, downloader, output_dir, tile_grid_path, max_cloud_cover):
        self.fetcher = fetcher
        self.downloader = downloader
        self.output_dir = output_dir
        self.tile_grid_path = tile_grid_path
        self.max_cloud_cover = max_cloud_cover
        self.bbox_handler = BoundingBoxHandler()
        self.result_manager = ResultManager()
        self.image_processor = ImageProcessor(satelite="")  # Será redefinido na execução
        self.mosaic_generator = MosaicGenerator()

    def processar_tiles_parana(self, satelite, start_date, end_date):
        if satelite not in self.SAT_SUPPORTED:
            logger.error(f"Satélite '{satelite}' não é suportado.")
            self.result_manager.log_error_csv("Paraná", satelite, "Satélite não suportado")
            return

        tile_mosaic_files = []
        results_time_estimated = []

        for tile in TILES_PARANA:
            start = time.perf_counter()
            logger.info(f"Processando tile {tile}...")

            tile_grid = gpd.read_file(self.tile_grid_path)
            tile_grid = tile_grid[tile_grid["NAME"] == tile]

            if tile_grid.empty:
                logger.warning(f"Tile {tile} não encontrado na grade Sentinel-2. Pulando...")
                continue

            main_bbox = self.bbox_handler.calcular_bbox_reduzido(tile_grid)

            image_assets = self.fetcher.fetch_image(
                satelite, main_bbox, start_date, end_date,
                self.max_cloud_cover, self.tile_grid_path, tile
            )

            if not image_assets:
                logger.warning(f"Nenhuma imagem encontrada para o tile {tile}.")
                continue

            logger.info("Baixando e processando imagens...")
            r = self.downloader.download(image_assets['B04'], f"{satelite}_{start_date}_{end_date}_red")
            g = self.downloader.download(image_assets['B03'], f"{satelite}_{start_date}_{end_date}_green")
            b = self.downloader.download(image_assets['B02'], f"{satelite}_{start_date}_{end_date}_blue")

            tile_mosaic_output = os.path.join(self.output_dir, f"{satelite}_{tile}_{start_date}_{end_date}_RGB.tif")
            ImageProcessor(satelite).merge_rgb_tif(r, g, b, tile_mosaic_output)

            tile_mosaic_files.append(tile_mosaic_output)
            duration = time.perf_counter() - start
            results_time_estimated.append({"Tile_id": tile, "duration_sec": duration})

        self.result_manager.gerenciar_resultados(
            tile_mosaic_files, results_time_estimated, self.output_dir, satelite, start_date, end_date
        )