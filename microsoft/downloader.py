import planetary_computer
import pystac_client
import rasterio
import requests

catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace,
)

time_range = "2020-12-01/2020-12-31"
bbox = [-54.6457, -25.4808, -54.5457, -25.3908]

search = catalog.search(collections=["landsat-c2-l2"], bbox=bbox, datetime=time_range)

items = list(search.items())
if not items:
    print("Nenhuma imagem encontrada para esta área.")
    exit()

item = items[0]

signed_item = planetary_computer.sign(item)

band_url = signed_item.assets["red"].href

output_filename = "landsat8_red_band.tif"

response = requests.get(band_url)
if response.status_code == 200:
    with open(output_filename, "wb") as file:
        file.write(response.content)
    print(f"Imagem baixada com sucesso: {output_filename}")
else:
    print("Erro ao baixar a imagem.")
