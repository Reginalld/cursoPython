# brazil_data_cube/processors/image_processor.py

import numpy as np
import rasterio
from rasterio.plot import reshape_as_image
import logging
import math
from typing import Optional


logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self, satelite: str):
        self.satelite = satelite

    def merge_rgb_tif(self, r: str, g: str, b: str, output_path: str) -> str:
        """
        Mescla bandas R, G e B em um único GeoTIFF RGB.
        
        Args:
            r (str): Caminho da banda vermelha
            g (str): Caminho da banda verde
            b (str): Caminho da banda azul
            output_path (str): Caminho para salvar imagem final

        Returns:
            str: Caminho do arquivo salvo
        """
        logger.info(f"Mesclando bandas RGB para: {output_path}")

        with rasterio.open(r) as red, \
             rasterio.open(g) as green, \
             rasterio.open(b) as blue:

            # Lê bandas e converte zeros em NaN
            r_band = red.read(1).astype(float)
            g_band = green.read(1).astype(float)
            b_band = blue.read(1).astype(float)

            r_band[r_band == 0] = np.nan
            g_band[g_band == 0] = np.nan
            b_band[b_band == 0] = np.nan

            # Funções de normalização
            def normalize_soft(array):
                array_min, array_max = np.nanmin(array), np.nanmax(array)
                if array_max - array_min == 0:
                    return np.zeros_like(array, dtype=np.uint8)
                scaled = (array - array_min) / (array_max - array_min) * 255
                return np.nan_to_num(scaled, nan=0).astype(np.uint8)

            def normalize_percentile(array):
                p2, p98 = np.nanpercentile(array, (2, 98))
                array = np.clip(array, p2, p98)
                if np.nanmax(array) - np.nanmin(array) == 0:
                    return np.zeros_like(array, dtype=np.uint8)
                scaled = (array - np.nanmin(array)) / (np.nanmax(array) - np.nanmin(array)) * 255
                return np.nan_to_num(scaled, nan=0).astype(np.uint8)

            norm_func = normalize_soft if self.satelite == 'S2-16D-2' else normalize_percentile

            r_norm = norm_func(r_band)
            g_norm = norm_func(g_band)
            b_norm = norm_func(b_band)

            # Máscara de valores NaN
            nan_mask = np.isnan(r_band) | np.isnan(g_band) | np.isnan(b_band)
            r_norm[nan_mask] = 0
            g_norm[nan_mask] = 0
            b_norm[nan_mask] = 0

            # Empilha como RGB
            rgb = np.stack([r_norm, g_norm, b_norm], axis=0)

            # Atualiza o profile para uint8
            profile = red.profile
            profile.update(count=3, dtype=rasterio.uint8, driver="GTiff")

            # Salva o arquivo
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(rgb[0], 1)
                dst.write(rgb[1], 2)
                dst.write(rgb[2], 3)

            logger.info(f"Imagem RGB salva em: {output_path}")