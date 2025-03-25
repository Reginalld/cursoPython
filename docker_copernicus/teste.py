import os
import glob
import rasterio
from rasterio.merge import merge
from rasterio.enums import Resampling
import numpy as np

def get_valid_tiles(tile_dir):
    """Filtra imagens com exatamente 3 bandas."""
    tile_paths = sorted(glob.glob(os.path.join(tile_dir, "*.tif")))
    valid_tiles = []
    for path in tile_paths:
        with rasterio.open(path) as src:
            if src.count == 3:
                valid_tiles.append(path)
    return valid_tiles

def merge_tiles_in_blocks(tile_dir, output_file, block_size=3):
    """
    Faz a fusão de tiles em blocos menores para evitar estouro de memória.
    Processa blocos, converte para uint8 e ajusta o metadata para remover nodata inválido.
    """
    valid_tiles = get_valid_tiles(tile_dir)
    if not valid_tiles:
        raise ValueError("Nenhum tile válido encontrado com 3 bandas.")
    
    # Cria diretório temporário para armazenar os blocos
    temp_dir = os.path.join(tile_dir, "temp_blocks")
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_files = []  # Lista para armazenar os blocos temporários
    
    # Processa em blocos
    for i in range(0, len(valid_tiles), block_size):
        block_files = valid_tiles[i:i + block_size]
        # Abre os arquivos do bloco e realiza o merge
        src_files = [rasterio.open(f) for f in block_files]
        sub_mosaic, out_trans = merge(src_files, resampling=Resampling.nearest)
        for src in src_files:
            src.close()
        
        # Converte os valores para uint8 (garante que os valores estejam entre 0 e 255)
        sub_mosaic = np.clip(sub_mosaic, 0, 255).astype(np.uint8)
        
        # Define o nome do bloco temporário
        block_filename = os.path.join(temp_dir, f"block_{i//block_size}.tif")
        temp_files.append(block_filename)
        
        meta = src.meta.copy()
        # Remove ou redefine nodata para evitar conflito com uint8
        meta.pop("nodata", None)
        meta.update({
                "driver": "GTiff",
                "height": sub_mosaic.shape[1],
                "width": sub_mosaic.shape[2],
                "transform": out_trans,
                "dtype": "uint8",
                "compress": "lzw"
            })
        
        with rasterio.open(block_filename, "w", **meta) as dst:
            dst.write(sub_mosaic)
    
    # Junta os blocos temporários
    temp_srcs = [rasterio.open(f) for f in temp_files]
    final_mosaic, final_trans = merge(temp_srcs, resampling=Resampling.nearest)
    for src in temp_srcs:
        src.close()
    
    # Atualiza o metadata para o mosaico final
    with rasterio.open(temp_files[0]) as src:
        meta = src.meta.copy()
        meta.pop("nodata", None)
        meta.update({
            "driver": "GTiff",
            "height": final_mosaic.shape[1],
            "width": final_mosaic.shape[2],
            "transform": final_trans,
            "dtype": "uint8"
        })
    
    with rasterio.open(output_file, "w", **meta) as dst:
        dst.write(final_mosaic)
    
    # Remove arquivos temporários
    for temp in temp_files:
        os.remove(temp)
    os.rmdir(temp_dir)
    
    print("Mosaico final gerado com sucesso!")


if __name__ == "__main__":
    tile_dir = "docker_copernicus\\imagens\\tiles"
    output_file = "docker_copernicus\\imagens\\mosaic_final.tif"
    merge_tiles_in_blocks(tile_dir, output_file)
