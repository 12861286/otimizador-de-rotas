import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation

# Configurações de Performance
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Sistema de Proximidade Real")

loc = get_geolocation()
uploaded_file = st.file_uploader("Suba sua planilha", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    if 'Parada Original' not in df_raw.columns:
        df_raw['Parada Original'] = range(1, len(df_raw) + 1)

    # Local de partida
    if loc:
        lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
        st.success("📍 GPS Ativo.")
    else:
        lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']

    # LÓGICA "LIMPA TRILHOS": Pega o mais próximo, um por um, sem pular áreas
    def organizar_por_proximidade_pura(df, l_i, o_i):
        df_temp = df.copy()
        rota_final = []
        l_atual, o_atual = l_i, o_i
        
        while not df_temp.empty:
            # Calcula distância simples para todos os pontos restantes
            df_temp['dist'] = np.sqrt((df_temp['Latitude'] - l_atual)**2 + (df_temp['Longitude'] - o_atual)**2)
            idx_proximo = df_temp['dist'].idxmin()
            ponto = df_temp.loc[idx_proximo]
            
            rota_final.append(ponto)
            l_atual, o_atual = ponto['Latitude'], ponto['Longitude']
            df_temp = df_temp.drop(idx_proximo)
            
        return pd.DataFrame(rota_final)

    df_otimizado = organizar_por_proximidade_pura(df_raw, lat_ini, lon_ini)
    df_otimizado['Nova_Seq'] = range(1, len(df_otimizado) + 1)

    m = folium.Map(location=[lat_ini, lon_ini], zoom_start=14)
    
    # Traçado das primeiras 25 (Limite do Google)
    proximos = df_otimizado.head(25)
    pts_rota = [[lat_ini, lon_ini]] + proximos[['Latitude', 'Longitude']].values.tolist()
    
    try:
        res = gmaps.directions(pts_rota[0], pts_rota[-1], waypoints=pts_rota[1:-1], mode="driving")
        if res:
            poly = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
            folium.PolyLine([(p['lat'], p['lng']) for p in poly], color="#007AFF", weight=6).add_to(m)
            st.info("🛣️ Exibindo trajeto detalhado para as próximas 25 paradas.")
    except:
        st.warning("Exibindo apenas os balões devido ao limite da API.")

    # Renderização de TODOS os 82 Balões com números fixos no SVG
    for i, row in df_otimizado.iterrows():
        n_n, n_o = int(row['Nova_Seq']), int(row['Parada Original'])
        cor = "#007AFF" if n_n <= 25 else "#495057" # Azul para o lote atual, Cinza para o resto
        
        icon_html = f'''
            <div style="width: 42px; height: 52px;">
                <svg viewBox="0 0 384 512" xmlns="http://www.w3.org/2000/svg">
                    <defs><linearGradient id="g{n_n}" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="50%" style="stop-color:{cor};" />
                        <stop offset="50%" style="stop-color:#212529;" />
                    </linearGradient></defs>
                    <path fill="url(#g{n_n})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                    <text x="50%" y="30%" dominant-baseline="middle" text-anchor="middle" fill="white" font-family="Arial" font-weight="bold" font-size="110">{n_n}</text>
                    <text x="50%" y="56%" dominant-baseline="middle" text-anchor="middle" fill="#00FF00" font-family="Arial" font-weight="bold" font-size="80">{n_o}</text>
                </svg>
            </div>'''
        folium.Marker([row['Latitude'], row['Longitude']], icon=folium.DivIcon(icon_size=(42, 52), icon_anchor=(21, 52), html=icon_html)).add_to(m)

    folium_static(m, width=1100)

    # Botões de GPS
    for _, row in df_otimizado.iterrows():
        with st.expander(f"{int(row['Nova_Seq'])}º — {row['Destination Address']}"):
            st.write(f"Parada Original: {int(row['Parada Original'])}")
            st.link_button("🚀 Abrir no Maps", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
