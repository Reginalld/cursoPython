import openeo
import math
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("copernicus/log/copernicus_log.txt"),
        logging.StreamHandler() #Exibe no console
    ]
)

def initialize_copernicus(client_id, client_secret):
    try:
        logging.info("Inicializando a conexão com a Data Base da copernicus...")
        connection = openeo.connect('openeofed.dataspace.copernicus.eu')
        connection.authenticate_oidc_client_credentials(client_id,client_secret,provider_id='CDSE')
        return connection
    except Exception as e:
        logging.critical(f"Erro ao inicializar o copernicus: {e}", exc_info=True)
        raise RuntimeError(f"Erro ao iniciazliar o copernicus {e}")
    
def create_output(output_dir):
    # Função para criar o diretório de saída, caso não exista
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)



def calcular_bouding_box (lat,lon,raio_km):
    raio_graus_lat = raio_km / 111
    raio_graus_lon = raio_km / (111 * math.cos(math.radians(lat)))

    west = lon - raio_graus_lon
    east = lon + raio_graus_lon
    south = lat - raio_graus_lat
    north = lat + raio_graus_lat

    return {'west': west, 'south':south, 'east':east, 'north': north,'crs': 'EPSG:4326',}

def get_satelite_image(connection,satelite,bounding_box,start_date,end_date,lat,lon,radius):
    try:
        logging.info(f"Buscando imagens do {satelite} para ({lat}, {lon}) com raio de {radius}km...")
        if satelite == 'SENTINEL2_L2A':
            image = connection.load_collection(
                "SENTINEL2_L2A",
                spatial_extent=bounding_box,
                temporal_extent = [start_date, end_date],
                bands=["B02", "B03", "B04", "B08"],
                max_cloud_cover=20,

            )
            image = image.reduce_dimension(dimension='t', reducer='median')

        elif satelite == 'SENTINEL2_L1C':
            image = connection.load_collection(
                "SENTINEL2_L2A",
                spatial_extent=bounding_box,
                temporal_extent = [start_date, end_date],
                bands=["B02", "B03", "B04", "B08"],
                max_cloud_cover=20,

            )
            image = image.reduce_dimension(dimension='t', reducer='median')
        
        elif satelite == 'SENTINEL1_GRD':
            image = connection.load_collection(
                "SENTINEL1_GRD",
                spatial_extent=bounding_box,
                temporal_extent = [start_date,end_date],
                bands = ["VV","VH"]
            )
            image = image.sar_backscatter(
                coefficient = 'sigma0-ellipsoid'
            )

        else:
            logging.warning(f"Satélite {satelite} não suportado!")
            raise ValueError("Satélite não suportado. Escolha entre os satélites informados")
        
        return image

    except Exception as e:
        logging.error(f'Erro ao obter imagem do {satelite}: {e}', exc_info=True)
        return None
    
def download_image(image, output_dir, filename,radius):
    try:
        if image is None:
            logging.error("Tentativa de download com imagem inválida")
            raise ValueError("Imagem inválida. Verifique os parâmetros")
        filepath = os.path.join(output_dir,filename)
        logging.info(f"Iniciando download da imagem para {filepath}...")

        # if radius >=97:
        #     image.execute_batch()
        image.execute_batch(filepath)
        logging.info(f"Download concluído: {filepath}...")
        return filepath
    

    
    except Exception as e:
        logging.critical(f"Erro ao fazer download da imagem {e}", exc_info=True)
        raise RuntimeError("Erro ao fazer download da imagem",e)

ponto_central_lat = -25.436234077037668 
ponto_central_lon = -54.59553194719978
raio_km = 90
start_date = '2024-12-25'
end_date = '2025-01-25'
satelite = 'SENTINEL2_L1C'

satelites = ['SENTINEL3_OLCI_L1B',
 'SENTINEL3_SLSTR',
 'SENTINEL_5P_L2',
 'COPERNICUS_VEGETATION_PHENOLOGY_PRODUCTIVITY_10M_SEASON1',
 'COPERNICUS_VEGETATION_PHENOLOGY_PRODUCTIVITY_10M_SEASON2',
 'COPERNICUS_PLANT_PHENOLOGY_INDEX',
 'ESA_WORLDCOVER_10M_2020_V1',
 'ESA_WORLDCOVER_10M_2021_V2',
 'COPERNICUS_VEGETATION_INDICES',
 'SENTINEL2_L1C',
 'SENTINEL2_L2A',
 'SENTINEL1_GRD',
 'COPERNICUS_30',
 'LANDSAT8_L2',
 'SENTINEL3_SYN_L2_SYN',
 'SENTINEL3_SLSTR_L2_LST',
 'SENTINEL1_GLOBAL_MOSAICS']

# job = datacube.execute_batch("../../imagens/evi-composite.tiff", out_format="GTiff", title="Sentinel2_Download")

def main():
    client_id = 'sh-780be612-cdd5-46c2-be80-016e3d9e3941'
    client_secret = 'wNqrCLhYnogycEclvClgVfrCRzNxjzec'
    output_dir = '../../imagens'
    connection = initialize_copernicus(client_id,client_secret)
    bounding_box = calcular_bouding_box(ponto_central_lat,ponto_central_lon,raio_km)
    create_output(output_dir)
    image = get_satelite_image(connection,satelite,bounding_box,start_date,end_date,ponto_central_lat,ponto_central_lon,raio_km)
    
    if image is None:
        logging.warning('Nenhuma imagem encontrada')

    filename = f'{satelite}_{ponto_central_lat}_{ponto_central_lon}_{raio_km}km_{start_date}_{end_date}.tif'
    download_image(image,output_dir,filename,raio_km)

main()