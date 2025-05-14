# brazil_data_cube/downloader/geometry_utils.py

import geopandas as gpd
from shapely.geometry import shape
import logging

logger = logging.getLogger(__name__)

class GeometryUtils:
    def __init__(self, tile_grid_path):
        self.tile_grid_path = tile_grid_path

    def is_good_geometry(self, item, tile_id):
        tiles_gdf = gpd.read_file(self.tile_grid_path)
        tile_row = tiles_gdf[tiles_gdf["NAME"] == tile_id]

        if tile_row.empty:
            logger.warning(f"Tile {tile_id} não encontrado na grade do Sentinel-2.")
            return False

        tile_geom = tile_row.iloc[0].geometry
        item_geom = shape(item.geometry)
        intersection = tile_geom.intersection(item_geom)

        if intersection.area / tile_geom.area >= 0.82:
            return True
        else:
            logger.debug(f"Imagem fora do tile {tile_id} - área de interseção insuficiente.")
            return False