import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation
from sklearn.cluster import KMeans

# 1. Configurações
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Correção de Sequência")

loc = get_geolocation()
uploaded_file = st.file_uploader("Suba sua planilha", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    if 'Parada Original' not in df_raw.columns:
        df_raw['Parada Original'] = range(1, len(df_raw) + 1)

    # Início da Rota
    if loc:
        lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
    else:
        lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']

    # Lógica de Agrupamento para manter pontos próximos (Corrige o 29 e 10)
    def organizar_por_proximidade(df, l_i, o_i):
        # Usamos 8 clusters para separar melhor as áreas de Contagem/BH
        kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
        df['Cluster'] = kmeans.fit_predict(df[['Latitude', 'Longitude']])
        
        centros = kmeans.cluster_centers_
        dist_c = np.sqrt((centros[:,0] - l_i)**2 + (centros[:,1] - o_i)**2)
        ordem_c = np.argsort(dist_c)
        
        rota_f, l_a, o_a = [], l_i, o_i
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

    df_otimizado = organizar_por_proximidade(df_raw, lat_ini, lon_ini)
    df_otimizado['Nova_Seq'] = range(1, len(df_otimizado) + 1)

    m = folium.Map(location=[lat_ini, lon_ini], zoom_start=14)
    folium.Marker([lat_ini, lon_ini], icon=folium.Icon(color='red', icon='play')).add_to(m)

    # TRAÇADO INDIVIDUAL (Corrige o erro de MAX_WAYPOINTS e segue a ordem real)
    pts = [[lat_ini, lon_ini]] + df_otimizado[['Latitude', 'Longitude']].values.tolist()
    
    # Vamos desenhar apenas as linhas entre os pontos para não estourar o Google
    for i in range(len(pts) - 1):
        try:
            # Traçado ponto a ponto garante que o 29 ligue no 30, e assim por diante
            res = gmaps.directions(pts[i], pts[i+1], mode="driving")
            if res:
                line = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
                folium.PolyLine([(p['lat'], p['lng']) for p in line], color="#007AFF", weight=4, opacity=0.8).add_to(m)
        except:
            # Se a rua for sem saída ou erro de mapa, faz uma linha reta simples
            folium.PolyLine([pts[i], pts[i+1]], color="#007AFF", weight=2, dash_array='5').add_to(m)

    # 4. BALÕES (SVG com números integrados para não sumirem)
    for i, row in df_otimizado.iterrows():
        n_n, n_o = int(row['Nova_Seq']), int(row['Parada Original'])
        icon_html = f'''
            <div style="width: 42px; height: 52px;">
                <svg viewBox="0 0 384 512" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <linearGradient id="g{n_n}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                            <stop offset="50%" style="stop-color:#343a40;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#g{n_n})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                    <text x="50%" y="32%" dominant-baseline="middle" text-anchor="middle" fill="white" font-family="Arial" font-weight="bold" font-size="110">{n_n}</text>
                    <text x="50%" y="58%" dominant-baseline="middle" text-anchor="middle" fill="#00FF00" font-family="Arial" font-weight="bold" font-size="80">{n_o}</text>
                </svg>
            </div>'''
        folium.Marker([row['Latitude'], row['Longitude']], icon=folium.DivIcon(icon_size=(42, 52), icon_anchor=(21, 52), html=icon_html)).add_to(m)

    folium_static(m, width=1100)

    # Botões de GPS
    for _, row in df_otimizado.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{int(row['Nova_Seq'])}º** — (Original: {int(row['Parada Original'])}) {row['Destination Address']}")
        c2.link_button("🚗 GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")from streamlit_js_eval import get_geolocation
from sklearn.cluster import KMeans

# 1. Configurações
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Correção Final dos Balões")

loc = get_geolocation()

uploaded_file = st.file_uploader("Suba sua planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    if 'Parada Original' not in df_raw.columns:
        df_raw['Parada Original'] = range(1, len(df_raw) + 1)

    # Início da Rota
    if loc:
        lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
        st.success("📍 GPS Conectado.")
    else:
        lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']

    # Lógica de Agrupamento por Setores (Resolve 81, 82, 10, 70)
    def organizar_por_zonas(df, l_i, o_i):
        kmeans = KMeans(n_clusters=6, random_state=42, n_init=10)
        df['Cluster'] = kmeans.fit_predict(df[['Latitude', 'Longitude']])
        centros = kmeans.cluster_centers_
        dist_c = np.sqrt((centros[:,0] - l_i)**2 + (centros[:,1] - o_i)**2)
        ordem_c = np.argsort(dist_c)
        rota_f, l_a, o_a = [], l_i, o_i
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

    m = folium.Map(location=[lat_ini, lon_ini], zoom_start=14)
    folium.Marker([lat_ini, lon_ini], icon=folium.Icon(color='red', icon='home')).add_to(m)

    # Desenho da Linha (Ponto a Ponto)
    pts = [[lat_ini, lon_ini]] + df_otimizado[['Latitude', 'Longitude']].values.tolist()
    for i in range(len(pts) - 1):
        try:
            res = gmaps.directions(pts[i], pts[i+1], mode="driving")
            if res:
                line = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
                folium.PolyLine([(p['lat'], p['lng']) for p in line], color="#007AFF", weight=5).add_to(m)
        except: continue

    # 4. BALÕES BICOLORES COM NÚMEROS FORÇADOS (SVG TEXT)
    for i, row in df_otimizado.iterrows():
        n_n, n_o = int(row['Nova_Seq']), int(row['Parada Original'])
        
        # O segredo: Colocar o <text> dentro do <svg> garante que eles nunca sumam
        icon_html = f'''
            <div style="width: 42px; height: 52px;">
                <svg viewBox="0 0 384 512" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <linearGradient id="grd{n_n}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                            <stop offset="50%" style="stop-color:#343a40;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#grd{n_n})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                    <text x="50%" y="32%" dominant-baseline="middle" text-anchor="middle" fill="white" font-family="Arial" font-weight="bold" font-size="110">{n_n}</text>
                    <text x="50%" y="58%" dominant-baseline="middle" text-anchor="middle" fill="#00FF00" font-family="Arial" font-weight="bold" font-size="80">{n_o}</text>
                </svg>
            </div>'''
        
        folium.Marker(
            [row['Latitude'], row['Longitude']], 
            icon=folium.DivIcon(icon_size=(42, 52), icon_anchor=(21, 52), html=icon_html)
        ).add_to(m)

    folium_static(m, width=1100)

    # Lista de Botões
    for _, row in df_otimizado.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{int(row['Nova_Seq'])}º** — {row['Destination Address']} (Original: {int(row['Parada Original'])})")
        c2.link_button("🚗 GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
