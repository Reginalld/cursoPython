import os
from urllib.parse import urlparse

import pystac_client
import os
from urllib.parse import urlparse
import numpy as np
import requests
import rasterio
from rasterio.plot import reshape_as_image
from pystac import Asset
from tqdm import tqdm
from PIL import Image
import math

def calcular(lat, lon, raio_km):
    raio_graus_lat = raio_km / 111
    raio_graus_lon = raio_km / (111 * math.cos(math.radians(lat)))

    return {
        lon - raio_graus_lon,
        lat - raio_graus_lat,
        lon + raio_graus_lon,
        lat + raio_graus_lat,
    }

service = pystac_client.CLient.open('https://data.inpe.br/bdc/stac/v1/')
bb = calcular(-25.436158455202953, -54.595674941183646,5)
item_search = service.search(bbox=(bb),
                             datetime='2018-08-01/2019-07-31',
                             collections=['S2-16D-2'])
assets = item_search.assets




# item_search = service.search(
#     bbox=(bb), 
#     datetime='2024-02-01/2024-10-31',
#     collections=['S2-16D-2']
# )

# for item in item_search.items():
#     print(item)

# assets = item.assets
# for k in assets.keys():
#     print(k)

# def download(asset: Asset, directory: str = "images", chunk_size: int = 1024 * 16, **request_options) -> str:
#     """Baixa um ativo STAC e salva no diretório especificado."""
#     os.makedirs(directory, exist_ok=True)
#     output_file = os.path.join(directory, urlparse(asset.href).path.split('/')[-1])
    
#     response = requests.get(asset.href, stream=True, **request_options)
#     total_bytes = int(response.headers.get('content-length', 0))
    
#     with tqdm.wrapattr(open(output_file, 'wb'), 'write', miniters=1, total=total_bytes, desc=os.path.basename(output_file)) as fout:
#         for chunk in response.iter_content(chunk_size=chunk_size):
#             fout.write(chunk)

#     return output_file  # Retorna o caminho do arquivo baixado

# def merge_rgb_tif(bands: dict, output_path: str = "images/sentinel2_image.tif"):
#     """Combina as bandas R, G e B e salva como um arquivo GeoTIFF."""
#     with rasterio.open(bands['R']) as red, \
#          rasterio.open(bands['G']) as green, \
#          rasterio.open(bands['B']) as blue:
        
#         # Lê os dados das bandas
#         r = red.read(1)
#         g = green.read(1)
#         b = blue.read(1)

#         # Normaliza para 0-255
#         def normalize(band):
#             return ((band - band.min()) / (band.max() - band.min()) * 255).astype(np.uint8)

#         rgb = np.stack([normalize(r), normalize(g), normalize(b)], axis=0)  # Formato (3, altura, largura)

#         # Cria metadados para o novo arquivo
#         profile = red.profile
#         profile.update(
#             count=3,  # Três bandas (RGB)
#             dtype=rasterio.uint8,  # Salvar como uint8 para imagens coloridas
#             driver="GTiff"  # Formato GeoTIFF
#         )

#         # Salva o arquivo GeoTIFF
#         with rasterio.open(output_path, 'w', **profile) as dst:
#             dst.write(rgb[0], 1)  # Escreve a banda vermelha
#             dst.write(rgb[1], 2)  # Escreve a banda verde
#             dst.write(rgb[2], 3)  # Escreve a banda azul

#         print(f"Imagem RGB GeoTIFF salva em: {output_path}")

# # Exemplo de uso: Baixar as bandas RGB e gerar a imagem combinada em GeoTIFF
# bands_rgb = {
#     "R": download(assets['B04']),  # Banda Vermelha
#     "G": download(assets['B03']),  # Banda Verde
#     "B": download(assets['B02'])   # Banda Azul
# }

# merge_rgb_tif(bands_rgb)
