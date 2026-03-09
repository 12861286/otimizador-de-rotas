import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation

# Setup leve
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Carregamento Rápido")

# Tenta pegar GPS, mas não trava se não conseguir
loc = get_geolocation()
uploaded_file = st.file_uploader("Suba sua planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Define ponto de partida
    if loc and 'coords' in loc:
        lat_i, lon_i = loc['coords']['latitude'], loc['coords']['longitude']
    else:
        lat_i, lon_i = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']

    # LÓGICA DE VIZINHO IMEDIATO (Rápida e sem erros)
    def organizar_sequencia_rapida(df, start_lat, start_lon):
        temp_df = df.copy()
        rota = []
        curr_lat, curr_lon = start_lat, start_lon
        
        while not temp_df.empty:
            # Calcula distância simples para todos os pontos
            temp_df['d'] = np.sqrt((temp_df['Latitude'] - curr_lat)**2 + (temp_df['Longitude'] - curr_lon)**2)
            
            # Pega o MAIS PRÓXIMO (Isso evita pular o 10 se ele estiver do lado do 9)
            idx = temp_df['d'].idxmin()
            ponto = temp_df.loc[idx]
            rota.append(ponto)
            
            # Atualiza posição e remove o ponto
            curr_lat, curr_lon = ponto['Latitude'], ponto['Longitude']
            temp_df = temp_df.drop(idx)
            
        return pd.DataFrame(rota)

    with st.spinner('Montando mapa...'):
        df_otimizado = organizar_sequencia_rapida(df_raw, lat_i, lon_i)
        df_otimizado['Seq'] = range(1, len(df_otimizado) + 1)

        # Cria mapa base
        m = folium.Map(location=[lat_i, lon_i], zoom_start=15)

        # Desenha a linha azul (Apenas para as primeiras 25 para ser instantâneo)
        proximos = df_otimizado.head(25)
        pts = [[lat_i, lon_i]] + proximos[['Latitude', 'Longitude']].values.tolist()
        
        try:
            res = gmaps.directions(pts[0], pts[-1], waypoints=pts[1:-1], mode="driving")
            if res:
                poly = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
                folium.PolyLine([(p['lat'], p['lng']) for p in poly], color="#007AFF", weight=6).add_to(m)
        except:
            folium.PolyLine(pts, color="#007AFF", weight=2, dash_array='5').add_to(m)

        # Renderiza os Balões
        for _, row in df_otimizado.iterrows():
            n = int(row['Seq'])
            cor = "#007AFF" if n <= 25 else "#6c757d"
            
            icon_html = f'''
                <div style="width: 40px; height: 40px; background:{cor}; border:2px solid white; border-radius:50%; 
                display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:14px;">
                {n}</div>'''
            folium.Marker([row['Latitude'], row['Longitude']], 
                          icon=folium.DivIcon(html=icon_html)).add_to(m)

        folium_static(m, width=1100)

    # Lista de paradas rápida
    st.subheader("📋 Próximas Entregas")
    for _, row in df_otimizado.head(15).iterrows():
        col1, col2 = st.columns([4, 1])
        col1.write(f"**{int(row['Seq'])}º** — {row['Destination Address']}")
        col2.link_button("🚗 GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
