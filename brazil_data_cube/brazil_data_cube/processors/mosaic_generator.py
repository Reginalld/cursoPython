# brazil_data_cube/processors/mosaic_generator.py

import rasterio
from rasterio.merge import merge
import subprocess
import os
import time
import logging

logger = logging.getLogger(__name__)

class MosaicGenerator:
    def __init__(self, common_crs="EPSG:32721"):
        self.common_crs = common_crs

    def mosaic_tiles(self, tile_files, output_path):
        """
        Cria um mosaico a partir de múltiplos arquivos GeoTIFF.
        Se necessário, reprojeta os arquivos para o CRS comum.
        """
        src_files = []
        band_count = None
        valid_files = []

        for fp in tile_files:
            try:
                with rasterio.open(fp) as src:
                    if src.count == 0:
                        raise rasterio.errors.RasterioIOError(f"Arquivo {fp} não possui bandas válidas.")

                    if band_count is None:
                        band_count = src.count
                    elif src.count != band_count:
                        logger.warning(f"Arquivo {fp} possui {src.count} bandas, diferente do esperado ({band_count}). Ignorando.")
                        continue

                    if src.crs != self.common_crs:
                        logger.warning(f"Arquivo {fp} tem CRS diferente ({src.crs}). Reprojetando...")
                        reprojected_fp = fp.replace(".tif", "_reprojected.tif")
                        cmd = [
                            "gdalwarp",
                            "-t_srs", self.common_crs,
                            "-dstnodata", "-32768",
                            "-overwrite",
                            fp,
                            reprojected_fp
                        ]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode != 0:
                            logger.error(f"Erro ao reprojetar {fp}: {result.stderr}")
                            continue
                        time.sleep(20)  # Tempo para garantir que o arquivo esteja pronto
                        valid_files.append(reprojected_fp)
                        src_files.append(rasterio.open(reprojected_fp))
                        continue

                    valid_files.append(fp)
                    src_files.append(rasterio.open(fp))

            except rasterio.errors.RasterioIOError as e:
                logger.error(f"Erro ao abrir {fp}: {e}")
                os.remove(fp)
                logger.info(f"Arquivo corrompido {fp} foi removido.")

        if not src_files:
            logger.error("Nenhum arquivo válido para mosaico.")
            return None

        # Faz o merge dos tiles
        mosaic, out_trans = merge(src_files)

        # Atualiza metadados
        out_meta = src_files[0].meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_trans,
            "count": src_files[0].count,
            "dtype": src_files[0].dtypes[0],
            "crs": self.common_crs
        })

        # Salva o mosaico final
        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(mosaic)

        for src in src_files:
            src.close()

        logger.info(f"Mosaico salvo em: {output_path}")
        return output_path