import planetary_computer
from pystac_client import Client

# URL correta para o catálogo STAC
URL = "https://planetarycomputer.microsoft.com/api/stac/v1"

# Conectar ao catálogo
client = Client.open(URL)

# Definir parâmetros da busca
latitude, longitude = -25.4, -49.2  # Exemplo de coordenadas
data_inicio, data_fim = "2024-01-01", "2024-01-28"

# Criar a query para buscar imagens Sentinel-2
search = client.search(
    collections=["sentinel-2-l2a"],
    bbox=[longitude - 1, latitude - 1, longitude + 1, latitude + 1],  # Caixa delimitadora
    datetime=f"{data_inicio}/{data_fim}",
    max_items=5
)

# Listar os resultados encontrados
items = list(search.get_items())
print(f"Encontrados {len(items)} produtos.")

# Exibir detalhes do primeiro item encontrado
if items:
    item = items[0]  # Pegando o primeiro resultado
    print(f"ID do item: {item.id}")
    print(f"Assets disponíveis: {list(item.assets.keys())}")

    # Pegar a URL autenticada de um asset (exemplo: banda 4 - Vermelho)
    asset_url = item.assets["B04"].href
    signed_url = planetary_computer.sign(asset_url)
    print(f"URL autenticada da Banda 4: {signed_url}")

import requests

# Caminho onde deseja salvar a imagem
output_file = "sentinel_b04.tif"

# Fazer o download do arquivo
response = requests.get(signed_url, stream=True)
if response.status_code == 200:
    with open(output_file, "wb") as file:
        for chunk in response.iter_content(chunk_size=1024):
            file.write(chunk)
    print(f"Download concluído! Arquivo salvo como {output_file}")
else:
    print(f"Erro ao baixar a imagem. Código HTTP: {response.status_code}")