import os
import requests
import rasterio
import numpy as np
from rasterio.plot import reshape_as_raster
from pystac_client import Client

# Parâmetros de busca
CLOUD_COVER_MAX = 20  # Percentual máximo de cobertura de nuvens

# URL do STAC do INPE
datainpe = "https://data.inpe.br/bdc/stac/v1/"
catalogo = Client.open(datainpe)

# Definição da coleção, bbox e intervalo de datas
bbox = [-54.6457, -25.4808, -54.5457, -25.3908]
intervalo = "2024-05-01/2024-05-15"
search = catalogo.search(
    collections=["landsat-2"], bbox=bbox, datetime=intervalo
)

# Obter os itens retornados
items = search.item_collection()

# Filtrar imagens pela cobertura de nuvens
items_filtrados = [item for item in items if item.properties.get("eo:cloud_cover", 100) <= CLOUD_COVER_MAX]

if not items_filtrados:
    print("Nenhuma imagem encontrada dentro do limite de nuvens!")
    exit()

# Pegar o primeiro item filtrado
primeiro = items_filtrados[0]
ativos = primeiro.assets

# URLs das bandas
urls = {
    "red": ativos["red"].href,
    "green": ativos["green"].href,
    "blue": ativos["blue"].href,
}

# Função para baixar e salvar as imagens na pasta /images
def baixar_imagem(url, nome):
    caminho = os.path.join("inpe/images", nome)
    if not os.path.exists(caminho):  # Evita baixar novamente se já existe
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(caminho, "wb") as f:
                f.write(r.content)
            print(f"Baixado: {caminho}")
        else:
            print(f"Erro ao baixar {nome}")
            return None
    return caminho

# Baixar imagens
arquivos = {banda: baixar_imagem(url, f"{banda}.tif") for banda, url in urls.items()}

# Abrir as bandas com rasterio
def abrir_banda(nome):
    with rasterio.open(nome) as src:
        return src.read(1), src.meta  # Retorna os dados e metadados

red, meta = abrir_banda(arquivos["red"])
green, _ = abrir_banda(arquivos["green"])
blue, _ = abrir_banda(arquivos["blue"])

# Criar matriz RGB (stack)
rgb = np.stack([red, green, blue], axis=0)

# Atualizar metadados para 3 bandas
meta.update({"count": 3, "dtype": "uint16"})  # Ajuste conforme necessário

# Salvar imagem RGB na pasta /images
caminho_rgb = os.path.join("inpe/images", "rgb_merged.tif")
with rasterio.open(caminho_rgb, "w", **meta) as dst:
    dst.write(rgb)

print(f"Imagem RGB salva em: {caminho_rgb}")
