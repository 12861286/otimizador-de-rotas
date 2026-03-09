import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation
from sklearn.cluster import KMeans # Para agrupar pontos próximos

# 1. Configurações
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Otimização por Setores")

loc = get_geolocation()

uploaded_file = st.file_uploader("Suba sua planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    if 'Parada Original' not in df_raw.columns:
        df_raw['Parada Original'] = range(1, len(df_raw) + 1)

    if loc:
        lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
        st.success("📍 GPS detectado! Roteirizando por proximidade de zona.")
    else:
        lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']
        st.info("ℹ️ Iniciando pelo 1º ponto da lista.")

    # --- NOVA LÓGICA: AGRUPAMENTO POR K-MEANS ---
    def organizar_por_setores(df, l_ini, o_ini):
        # Criamos 6 zonas/setores para garantir que ele limpe áreas vizinhas
        n_clusters = 6 if len(df) > 30 else 3
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df['Cluster'] = kmeans.fit_predict(df[['Latitude', 'Longitude']])
        
        # Ordena os clusters pela distância do seu ponto inicial
        centros = kmeans.cluster_centers_
        dist_centros = np.sqrt((centros[:,0] - l_ini)**2 + (centros[:,1] - o_ini)**2)
        ordem_clusters = np.argsort(dist_centros)
        
        rota_final = []
        l_atual, o_atual = l_ini, o_ini
        
        for c in ordem_clusters:
            df_cluster = df[df['Cluster'] == c].copy()
            # Dentro de cada cluster, aplicamos o vizinho mais próximo
            while not df_cluster.empty:
                dist = np.sqrt((df_cluster['Latitude'] - l_atual)**2 + (df_cluster['Longitude'] - o_atual)**2)
                idx = dist.idxmin()
                ponto = df_cluster.loc[idx]
                rota_final.append(ponto)
                l_atual, o_atual = ponto['Latitude'], ponto['Longitude']
                df_cluster = df_cluster.drop(idx)
                
        return pd.DataFrame(rota_final)

    with st.spinner('Agrupando entregas por região...'):
        df_otimizado = organizar_por_setores(df_raw, lat_ini, lon_ini)
        df_otimizado['Nova_Seq'] = range(1, len(df_otimizado) + 1)

    # 3. Mapa
    m = folium.Map(location=[lat_ini, lon_ini], zoom_start=14)
    folium.Marker([lat_ini, lon_ini], tooltip="INÍCIO", icon=folium.Icon(color='red', icon='play')).add_to(m)

    # Trajetória ponto a ponto (mais limpa)
    pontos_rota = [[lat_ini, lon_ini]] + df_otimizado[['Latitude', 'Longitude']].values.tolist()
    for i in range(len(pontos_rota) - 1):
        try:
            res = gmaps.directions(pontos_rota[i], pontos_rota[i+1], mode="driving")
            if res:
                poly = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
                folium.PolyLine([(p['lat'], p['lng']) for p in poly], color="#007AFF", weight=5).add_to(m)
        except: continue

    # 4. Balões com Números Ajustados (Mais para cima)
    for i, row in df_otimizado.iterrows():
        n_nova, n_orig = int(row['Nova_Seq']), int(row['Parada Original'])
        icon_html = f'''
            <div style="position: relative; width: 42px; height: 52px;">
                <svg viewBox="0 0 384 512" style="width: 42px; height: 52px; position: absolute;">
                    <defs><linearGradient id="g{n_nova}" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                        <stop offset="50%" style="stop-color:#212529;stop-opacity:1" />
                    </linearGradient></defs>
                    <path fill="url(#g{n_nova})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <span style="position: absolute; top: 1px; width: 42px; text-align: center; color: white; font-weight: bold; font-size: 14px; z-index:10;">{n_nova}</span>
                <span style="position: absolute; top: 17px; width: 42px; text-align: center; color: #00FF00; font-weight: bold; font-size: 10px; z-index:10;">{n_orig}</span>
            </div>'''
        folium.Marker([row['Latitude'], row['Longitude']], icon=folium.DivIcon(icon_size=(42, 52), icon_anchor=(21, 52), html=icon_html)).add_to(m)

    folium_static(m, width=1100)
