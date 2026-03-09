import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation
from sklearn.cluster import KMeans # Agora vai funcionar com o requirements atualizado

# 1. Configurações (Mantendo sua chave e projeto)
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Versão Estável")

loc = get_geolocation()

uploaded_file = st.file_uploader("Suba sua planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    if 'Parada Original' not in df_raw.columns:
        df_raw['Parada Original'] = range(1, len(df_raw) + 1)

    if loc:
        lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
        st.success("📍 GPS Ativo! Roteirizando a partir de sua posição.")
    else:
        lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']

    # --- LÓGICA DE AGRUPAMENTO (Resolve os pontos 81, 82, 10, 70) ---
    def organizar_por_zonas(df, l_i, o_i):
        # Divide em 6 setores geográficos para limpar a área antes de sair dela
        kmeans = KMeans(n_clusters=6, random_state=42, n_init=10)
        df['Cluster'] = kmeans.fit_predict(df[['Latitude', 'Longitude']])
        
        # Ordena os grupos pela proximidade do seu início
        centros = kmeans.cluster_centers_
        dist_c = np.sqrt((centros[:,0] - l_i)**2 + (centros[:,1] - o_i)**2)
        ordem_c = np.argsort(dist_c)
        
        rota_f = []
        l_a, o_a = l_i, o_i
        for c in ordem_c:
            df_c = df[df['Cluster'] == c].copy()
            while not df_c.empty:
                d = np.sqrt((df_c['Latitude'] - l_a)**2 + (df_c['Longitude'] - o_a)**2)
                idx = d.idxmin()
                p = df_c.loc[idx]
                rota_f.append(p)
                l_a, o_a = p['Latitude'], p['Longitude']
                df_c = df_c.drop(idx)
        return pd.DataFrame(rota_f)

    df_otimizado = organizar_por_zonas(df_raw, lat_ini, lon_ini)
    df_otimizado['Nova_Seq'] = range(1, len(df_otimizado) + 1)

    # 3. Mapa e Traçado
    m = folium.Map(location=[lat_ini, lon_ini], zoom_start=14)
    folium.Marker([lat_ini, lon_ini], icon=folium.Icon(color='red', icon='home')).add_to(m)

    # Linha azul ponto a ponto (Evita o emaranhado de linhas)
    pts = [[lat_ini, lon_ini]] + df_otimizado[['Latitude', 'Longitude']].values.tolist()
    for i in range(len(pts) - 1):
        try:
            # Desenha trechos curtos para seguir as ruas corretamente
            res = gmaps.directions(pts[i], pts[i+1], mode="driving")
            if res:
                line = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
                folium.PolyLine([(p['lat'], p['lng']) for p in line], color="#007AFF", weight=5, opacity=0.8).add_to(m)
        except: continue

    # 4. Balões com números ajustados (Nova Seq no topo, Original embaixo)
    for i, row in df_otimizado.iterrows():
        n_n, n_o = int(row['Nova_Seq']), int(row['Parada Original'])
        icon_html = f'''
            <div style="position: relative; width: 42px; height: 52px;">
                <svg viewBox="0 0 384 512" style="width: 42px; height: 52px; position: absolute;">
                    <defs><linearGradient id="gr{n_n}" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                        <stop offset="50%" style="stop-color:#343a40;stop-opacity:1" />
                    </linearGradient></defs>
                    <path fill="url(#gr{n_n})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <div style="position: absolute; top: 2px; width: 42px; text-align: center; color: white; font-weight: bold; font-size: 14px; z-index:10;">{n_n}</div>
                <div style="position: absolute; top: 18px; width: 42px; text-align: center; color: #00FF00; font-weight: bold; font-size: 10px; z-index:10;">{n_o}</div>
            </div>'''
        folium.Marker([row['Latitude'], row['Longitude']], icon=folium.DivIcon(icon_size=(42, 52), icon_anchor=(21, 52), html=icon_html)).add_to(m)

    folium_static(m, width=1100)

    # Botões de GPS
    for _, row in df_otimizado.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{int(row['Nova_Seq'])}º** — {row['Destination Address']} (Original: {int(row['Parada Original'])})")
        c2.link_button("🚗 GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
