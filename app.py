import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation

# Configurações
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Início pelo seu GPS")

# Tenta pegar sua localização real
loc = get_geolocation()

uploaded_file = st.file_uploader("Suba sua planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    if 'Parada Original' not in df_raw.columns:
        df_raw['Parada Original'] = range(1, len(df_raw) + 1)

    # Define o ponto de partida (Seu GPS ou a 1ª da lista)
    if loc:
        lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
        st.success(f"📍 GPS Ativo! Iniciando de sua posição atual.")
    else:
        st.warning("⚠️ GPS não detectado. Iniciando pelo primeiro endereço da lista.")
        lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']

    # Lógica de Vizinho Mais Próximo (Igual GPS profissional)
    def calcular_rota_limpa(df, l_ini, o_ini):
        df_t = df.copy()
        rota = []
        l_atual, o_atual = l_ini, o_ini
        while not df_t.empty:
            dist = np.sqrt((df_t['Latitude'] - l_atual)**2 + (df_t['Longitude'] - o_atual)**2)
            idx = dist.idxmin()
            ponto = df_t.loc[idx]
            rota.append(ponto)
            l_atual, o_atual = ponto['Latitude'], ponto['Longitude']
            df_t = df_t.drop(idx)
        return pd.DataFrame(rota)

    df_otimizado = calcular_rota_limpa(df_raw, lat_ini, lon_ini)
    df_otimizado['Nova_Seq'] = range(1, len(df_otimizado) + 1)

    # Mapa
    m = folium.Map(location=[lat_ini, lon_ini], zoom_start=13)
    folium.Marker([lat_ini, lon_ini], icon=folium.Icon(color='red', icon='info-sign'), tooltip="VOCÊ").add_to(m)

    # Desenho das ruas (em blocos para não dar erro)
    pontos = [[lat_ini, lon_ini]] + df_otimizado[['Latitude', 'Longitude']].values.tolist()
    for i in range(0, len(pontos)-1, 15):
        fim = min(i + 15, len(pontos))
        res = gmaps.directions(pontos[i], pontos[fim-1], waypoints=pontos[i+1:fim-1], mode="driving")
        if res:
            shape = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
            folium.PolyLine([(p['lat'], p['lng']) for p in shape], color="#007AFF", weight=6, opacity=0.8).add_to(m)

    # Balões Bicolores
    for i, row in df_otimizado.iterrows():
        n_nova, n_orig = int(row['Nova_Seq']), int(row['Parada Original'])
        icon_html = f'''
            <div style="position: relative; width: 42px; height: 52px;">
                <svg viewBox="0 0 384 512" style="width: 42px; height: 52px; position: absolute;">
                    <defs><linearGradient id="g{n_nova}" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                        <stop offset="50%" style="stop-color:#343a40;stop-opacity:1" />
                    </linearGradient></defs>
                    <path fill="url(#g{n_nova})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <div style="position: absolute; top: 4px; width: 42px; text-align: center; color: white; font-weight: bold; font-size: 14px;">{n_nova}</div>
                <div style="position: absolute; top: 20px; width: 42px; text-align: center; color: #00FF00; font-weight: bold; font-size: 11px;">{n_orig}</div>
            </div>'''
        folium.Marker([row['Latitude'], row['Longitude']], icon=folium.DivIcon(icon_size=(42, 52), icon_anchor=(21, 52), html=icon_html)).add_to(m)

    folium_static(m, width=1100)

    # Botões de GPS
    for _, row in df_otimizado.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{int(row['Nova_Seq'])}º** — {row['Destination Address']} (Original: {int(row['Parada Original'])})")
        c2.link_button("🚗 GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
