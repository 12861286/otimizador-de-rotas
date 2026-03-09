import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation
from sklearn.cluster import KMeans

# 1. Configurações Iniciais
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Lotes de 25 Paradas")

loc = get_geolocation()
uploaded_file = st.file_uploader("Suba sua planilha", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    if 'Parada Original' not in df_raw.columns:
        df_raw['Parada Original'] = range(1, len(df_raw) + 1)

    # Coordenada Inicial (GPS ou primeiro ponto)
    if loc:
        lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
        st.success("📍 GPS Conectado. Traçando rota do local atual.")
    else:
        lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']

    # 2. Otimização por Proximidade (Corrige o ponto 29 fora de ordem)
    def organizar_rota(df, l_i, o_i):
        # Aumentamos o número de clusters para 10 para evitar "saltos" no mapa
        kmeans = KMeans(n_clusters=10, random_state=42, n_init=10)
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

    df_otimizado = organizar_rota(df_raw, lat_ini, lon_ini)
    df_otimizado['Nova_Seq'] = range(1, len(df_otimizado) + 1)

    # 3. Criação do Mapa
    m = folium.Map(location=[lat_ini, lon_ini], zoom_start=14)

    # REGRA: Traçar apenas as primeiras 25 paradas para evitar o erro do Google
    proximos_pontos = df_otimizado.head(25)
    pts_linha = [[lat_ini, lon_ini]] + proximos_pontos[['Latitude', 'Longitude']].values.tolist()
    
    try:
        # Pede a trajetória completa considerando o sentido das ruas
        res = gmaps.directions(
            origin=pts_linha[0],
            destination=pts_linha[-1],
            waypoints=pts_linha[1:-1],
            mode="driving",
            optimize_waypoints=False # Já otimizamos no Python
        )
        if res:
            polyline = res[0]['overview_polyline']['points']
            route = googlemaps.convert.decode_polyline(polyline)
            folium.PolyLine([(p['lat'], p['lng']) for p in route], color="#007AFF", weight=6, opacity=0.8).add_to(m)
            st.info(f"🛣️ Linha azul traçada para as primeiras 25 paradas. Respeitando mãos de via.")
    except Exception as e:
        st.warning("Não foi possível traçar a linha exata, mostrando conexão simples.")

    # 4. BALÕES: Mostrar TODOS os 82 balões (sempre visíveis)
    for i, row in df_otimizado.iterrows():
        n_n, n_o = int(row['Nova_Seq']), int(row['Parada Original'])
        
        # Cor do balão: Azul para as próximas 25, Cinza para o resto
        cor_topo = "#007AFF" if n_n <= 25 else "#808080"
        
        icon_html = f'''
            <div style="width: 42px; height: 52px;">
                <svg viewBox="0 0 384 512">
                    <defs><linearGradient id="g{n_n}" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="50%" style="stop-color:{cor_topo};" />
                        <stop offset="50%" style="stop-color:#343a40;" />
                    </linearGradient></defs>
                    <path fill="url(#g{n_n})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                    <text x="50%" y="32%" dominant-baseline="middle" text-anchor="middle" fill="white" font-family="Arial" font-weight="bold" font-size="110">{n_n}</text>
                    <text x="50%" y="58%" dominant-baseline="middle" text-anchor="middle" fill="#00FF00" font-family="Arial" font-weight="bold" font-size="80">{n_o}</text>
                </svg>
            </div>'''
        
        folium.Marker(
            [row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(icon_size=(42, 52), icon_anchor=(21, 52), html=icon_html)
        ).add_to(m)

    folium_static(m, width=1100)

    # 5. Lista de Entrega com Botão GPS
    st.subheader("📋 Sequência de Entregas")
    for _, row in df_otimizado.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{int(row['Nova_Seq'])}º** — {row['Destination Address']} (Original: {int(row['Parada Original'])})")
        c2.link_button("🚗 Ir", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
