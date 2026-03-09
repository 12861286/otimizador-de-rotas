import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation

# 1. Configurações Iniciais
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Correção de Números nos Balões")

# Captura localização para início da rota
loc = get_geolocation()

uploaded_file = st.file_uploader("Suba sua planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    if 'Parada Original' not in df_raw.columns:
        df_raw['Parada Original'] = range(1, len(df_raw) + 1)

    # Define Ponto de Partida
    if loc:
        lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
        st.success("📍 GPS detectado! Calculando a partir da sua posição.")
    else:
        lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']
        st.info("ℹ️ GPS não disponível. Iniciando do primeiro endereço da lista.")

    # Algoritmo de Proximidade (Evita saltos na rota)
    def organizar_por_vizinho(df, l_start, o_start):
        df_t = df.copy()
        rota = []
        curr_l, curr_o = l_start, o_start
        while not df_t.empty:
            dist = np.sqrt((df_t['Latitude'] - curr_l)**2 + (df_t['Longitude'] - curr_o)**2)
            idx = dist.idxmin()
            ponto = df_t.loc[idx]
            rota.append(ponto)
            curr_l, curr_o = ponto['Latitude'], ponto['Longitude']
            df_t = df_t.drop(idx)
        return pd.DataFrame(rota)

    df_otimizado = organizar_por_vizinho(df_raw, lat_ini, lon_ini)
    df_otimizado['Nova_Seq'] = range(1, len(df_otimizado) + 1)

    # 3. Mapa
    m = folium.Map(location=[lat_ini, lon_ini], zoom_start=14)

    # Traçado das ruas (linha azul)
    caminho_pontos = [[lat_ini, lon_ini]] + df_otimizado[['Latitude', 'Longitude']].values.tolist()
    for i in range(0, len(caminho_pontos)-1, 15):
        fim = min(i + 15, len(caminho_pontos))
        res = gmaps.directions(caminho_pontos[i], caminho_pontos[fim-1], waypoints=caminho_pontos[i+1:fim-1], mode="driving")
        if res:
            polyline = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
            folium.PolyLine([(p['lat'], p['lng']) for p in polyline], color="#007AFF", weight=6).add_to(m)

    # 4. BALÕES COM NÚMEROS FORÇADOS (Correção de Visibilidade)
    for i, row in df_otimizado.iterrows():
        n_nova = int(row['Nova_Seq'])
        n_orig = int(row['Parada Original'])
        
        # HTML com z-index alto e cores fixas
        icon_html = f'''
            <div style="position: relative; width: 42px; height: 52px; display: flex; flex-direction: column; align-items: center;">
                <svg viewBox="0 0 384 512" style="width: 42px; height: 52px; position: absolute; top: 0; left: 0; z-index: 1;">
                    <defs>
                        <linearGradient id="grad{n_nova}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                            <stop offset="50%" style="stop-color:#343a40;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#grad{n_nova})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <span style="position: absolute; top: 3px; z-index: 100; color: white; font-weight: bold; font-size: 13px; font-family: Arial; pointer-events: none;">{n_nova}</span>
                <span style="position: absolute; top: 18px; z-index: 100; color: #FFFF00; font-weight: bold; font-size: 10px; font-family: Arial; pointer-events: none;">{n_orig}</span>
            </div>'''
        
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(icon_size=(42, 52), icon_anchor=(21, 52), html=icon_html)
        ).add_to(m)

    folium_static(m, width=1100)

    # Lista de GPS abaixo do mapa
    st.subheader("📋 Sequência de Entrega")
    for _, row in df_otimizado.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{int(row['Nova_Seq'])}º** — {row['Destination Address']} (Original: {int(row['Parada Original'])})")
        c2.link_button("🚗 GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
