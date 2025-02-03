import requests
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
import unidecode

def login(email, password):
    base_url = "https://api-service.fogocruzado.org.br/api/v2/"
    response_auth = requests.post(
        base_url + "auth/login",
        data={"email": email, "password": password},
    )
    if response_auth.status_code != 201:
        raise ValueError("Login failed")
    content = response_auth.json()
    return content['data']['accessToken']

def get_states(token):
    response = requests.get(
        "https://api-service.fogocruzado.org.br/api/v2/states",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        raise ValueError("Failed to fetch states")
    states_data = response.json()['data']
    return pd.DataFrame(states_data)

def flatten_occurrences(occurrences):
    flat_data = []

    for occurrence in occurrences:
        flat_occurrence = {
            'id': occurrence['id'],
            'documentNumber': occurrence['documentNumber'],
            'address': occurrence['address'],
            'latitude': occurrence['latitude'],
            'longitude': occurrence['longitude'],
            'date': occurrence['date'],
            'policeAction': occurrence['policeAction'],
            'agentPresence': occurrence['agentPresence'],
            'state_id': occurrence['state']['id'],
            'state_name': occurrence['state']['name'],
            'city_id': occurrence['city']['id'],
            'city_name': occurrence['city']['name'],
            'neighborhood_id': occurrence['neighborhood']['id'] if occurrence['neighborhood'] else None,
            'neighborhood_name': occurrence['neighborhood']['name'] if occurrence['neighborhood'] else None,
            'victims_count': len(occurrence['victims']),
        }

        for victim in occurrence['victims']:
            victim_info = {
                'victim_id': victim['id'],
                'victim_type': victim['type'],
                'victim_age': victim['age'],
                'victim_genre': victim['genre']['name'] if victim['genre'] else None,
            }
            flat_occurrence.update(victim_info)

        flat_data.append(flat_occurrence)

    return pd.DataFrame(flat_data)

def get_occurrences(token, state_ids):
    all_occurrences = []
    base_url = "https://api-service.fogocruzado.org.br/api/v2/occurrences?order=ASC&"

    for state_id in state_ids:
        url = f"{base_url}idState={state_id}"
        response = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        
        if response.status_code == 200:
            occurrences_data = response.json()['data']
            all_occurrences.extend(occurrences_data)

    if not all_occurrences:
        return pd.DataFrame()

    df = flatten_occurrences(all_occurrences)
    
    return df

def plot_occurrences_map(states_df, occurrences_df):
    shapefile_path = r'C:\Users\elome\OneDrive\Desktop\python_projects\fogo_cruzado\arquivos\shape\BR_UF_2023.shp'
    brasil_map = gpd.read_file(shapefile_path)

    def normalizar_nome_estado(nome):
        return unidecode.unidecode(nome.upper())

    state_name_map = {
        normalizar_nome_estado(nome_api): nome_shapefile
        for nome_api in occurrences_df['state_name'].unique()
        for nome_shapefile in brasil_map['NM_UF'].unique()
        if normalizar_nome_estado(nome_api) in normalizar_nome_estado(nome_shapefile)
    }

    occurrences_count = occurrences_df.groupby('state_name').size().reset_index(name='counts')
    
    occurrences_count['normalized_state'] = occurrences_count['state_name'].apply(normalizar_nome_estado)
    occurrences_count['mapped_state'] = occurrences_count['normalized_state'].map(state_name_map)
    
    merged = brasil_map.merge(
        occurrences_count,
        left_on='NM_UF',
        right_on='mapped_state',
        how='left'
    )

    merged['counts'] = merged['counts'].fillna(0)

    fig, ax = plt.subplots(1, 1, figsize=(15, 15))
    
    merged.plot(
        column='counts',
        ax=ax,
        legend=True,
        legend_kwds={
            'label': "Número de Ocorrências por Estado",
            'orientation': "horizontal"
        },
        cmap='OrRd',
        edgecolor='0.8',
        linewidth=0.8,
        vmin=0,
        vmax=merged['counts'].max()
    )
    
    plt.title('Mapa de Ocorrências no Brasil', fontsize=15)
    ax.axis('off')
    plt.tight_layout()
    
    plt.show()

def main(email, password):
    try:
        token = login(email, password)
        states_df = get_states(token)
        state_ids = states_df['id'].tolist()
        occurrences_df = get_occurrences(token, state_ids)

        if not occurrences_df.empty:
            plot_occurrences_map(states_df, occurrences_df)

    except Exception as e:
        print(f"Erro durante a execução: {str(e)}")

email = "maioelom@gmail.com"
password = "ab123def"
main(email, password)
