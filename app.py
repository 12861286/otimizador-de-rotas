import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation

# 1. Configurações
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Trajetória Linear e GPS")

# Captura sua localização
loc = get_geolocation()

uploaded_file = st.file_uploader("Suba sua planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    if 'Parada Original' not in df_raw.columns:
        df_raw['Parada Original'] = range(1, len(df_raw) + 1)

    # Define Ponto de Partida Real
    if loc:
        lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
        st.success("📍 GPS detectado! Iniciando de onde você está.")
    else:
        lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']
        st.info("ℹ️ GPS não disponível. Iniciando do 1º item da lista.")

    # --- ALGORITMO DE PROXIMIDADE (Corrige a trajetória) ---
    def organizar_rota_sequencial(df, l_start, o_start):
        df_t = df.copy()
        rota = []
        curr_l, curr_o = l_start, o_start
        while not df_t.empty:
            # Calcula a distância direta para evitar "pulos" geográficos
            dist = np.sqrt((df_t['Latitude'] - curr_l)**2 + (df_t['Longitude'] - curr_o)**2)
            idx = dist.idxmin()
            ponto = df_t.loc[idx]
            rota.append(ponto)
            curr_l, curr_o = ponto['Latitude'], ponto['Longitude']
            df_t = df_t.drop(idx)
        return pd.DataFrame(rota)

    df_otimizado = organizar_rota_sequencial(df_raw, lat_ini, lon_ini)
    df_otimizado['Nova_Seq'] = range(1, len(df_otimizado) + 1)

    # 3. Mapa
    m = folium.Map(location=[lat_ini, lon_ini], zoom_start=14)

    # --- BALÃO DE PARTIDA (VOCÊ) ---
    folium.Marker(
        [lat_ini, lon_ini], 
        tooltip="PONTO DE PARTIDA", 
        icon=folium.Icon(color='red', icon='home', prefix='fa')
    ).add_to(m)

    # --- DESENHO DA TRAJETÓRIA (Ponto a Ponto para evitar cruzamentos) ---
    pontos_rota = [[lat_ini, lon_ini]] + df_otimizado[['Latitude', 'Longitude']].values.tolist()
    
    # Desenhamos em blocos menores (10 em 10) para garantir precisão nas ruas
    for i in range(len(pontos_rota) - 1):
        try:
            res = gmaps.directions(pontos_rota[i], pontos_rota[i+1], mode="driving")
            if res:
                polyline = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
                folium.PolyLine([(p['lat'], p['lng']) for p in polyline], color="#007AFF", weight=5, opacity=0.8).add_to(m)
        except:
            continue

    # --- BALÕES COM NÚMEROS AJUSTADOS ---
    for i, row in df_otimizado.iterrows():
        n_nova = int(row['Nova_Seq'])
        n_orig = int(row['Parada Original'])
        
        icon_html = f'''
            <div style="position: relative; width: 42px; height: 52px;">
                <svg viewBox="0 0 384 512" style="width: 42px; height: 52px; position: absolute; z-index: 1;">
                    <defs>
                        <linearGradient id="grad{n_nova}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                            <stop offset="50%" style="stop-color:#343a40;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#grad{n_nova})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <span style="position: absolute; top: 2px; width: 42px; text-align: center; z-index: 100; color: white; font-weight: bold; font-size: 14px; font-family: Arial; pointer-events: none;">{n_nova}</span>
                <span style="position: absolute; top: 18px; width: 42px; text-align: center; z-index: 100; color: #00FF00; font-weight: bold; font-size: 10px; font-family: Arial; pointer-events: none;">{n_orig}</span>
            </div>'''
        
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(icon_size=(42, 52), icon_anchor=(21, 52), html=icon_html)
        ).add_to(m)

    folium_static(m, width=1100)

    # Lista de GPS
    st.subheader("📋 Sequência Lógica de Trabalho")
    for _, row in df_otimizado.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{int(row['Nova_Seq'])}º** — {row['Destination Address']} (Original: {int(row['Parada Original'])})")
        c2.link_button("🚗 GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
