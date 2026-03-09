import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation
from sklearn.cluster import KMeans

# Configurações de API
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Fluxo Real de Entrega")

loc = get_geolocation()
uploaded_file = st.file_uploader("Suba sua planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Define início pelo GPS ou 1º ponto
    if loc:
        lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
        st.success("📍 GPS Ativo - Iniciando rota agora.")
    else:
        lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']

    # LÓGICA DE VARREDURA (Evita deixar 83/84 para trás)
    def organizar_fluxo_inteligente(df, l_i, o_i):
        # Agrupamos em blocos geográficos menores (15 zonas)
        kmeans = KMeans(n_clusters=15, random_state=42, n_init=10)
        df['Setor'] = kmeans.fit_predict(df[['Latitude', 'Longitude']])
        
        # Ordena os setores pela proximidade real
        centros = kmeans.cluster_centers_
        dist_centros = np.sqrt((centros[:,0] - l_i)**2 + (centros[:,1] - o_i)**2)
        ordem_setores = np.argsort(dist_centros)
        
        rota_final = []
        l_atual, o_atual = l_i, o_i
        
        for s in ordem_setores:
            df_setor = df[df['Setor'] == s].copy()
            while not df_setor.empty:
                # Busca o próximo ponto considerando a direção do fluxo
                df_setor['dist'] = np.sqrt((df_setor['Latitude'] - l_atual)**2 + (df_setor['Longitude'] - o_atual)**2)
                idx = df_setor['dist'].idxmin()
                ponto = df_setor.loc[idx]
                rota_final.append(ponto)
                l_atual, o_atual = ponto['Latitude'], ponto['Longitude']
                df_setor = df_setor.drop(idx)
        return pd.DataFrame(rota_final)

    df_otimizado = organizar_fluxo_inteligente(df_raw, lat_ini, lon_ini)
    df_otimizado['Nova_Seq'] = range(1, len(df_otimizado) + 1)

    # 3. MAPA
    m = folium.Map(location=[lat_ini, lon_ini], zoom_start=14)

    # TRAÇADO DOS LOTES (25 em 25 para evitar erro MAX_WAYPOINTS)
    #
    lote_atual = df_otimizado.head(25)
    pts_linha = [[lat_ini, lon_ini]] + lote_atual[['Latitude', 'Longitude']].values.tolist()
    
    try:
        # Pede ao Google o caminho considerando contramão e sentido de via
        res = gmaps.directions(pts_linha[0], pts_linha[-1], waypoints=pts_linha[1:-1], mode="driving")
        if res:
            polyline = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
            folium.PolyLine([(p['lat'], p['lng']) for p in polyline], color="#007AFF", weight=6).add_to(m)
    except: pass

    # 4. BALÕES (Com números integrados para não sumirem)
    for i, row in df_otimizado.iterrows():
        n_n = int(row['Nova_Seq'])
        n_o = int(row.get('Parada Original', i+1))
        
        # Cor Azul para as próximas 25, Cinza para o resto
        cor_balao = "#007AFF" if n_n <= 25 else "#6c757d"
        
        icon_html = f'''
            <div style="width: 42px; height: 52px;">
                <svg viewBox="0 0 384 512" xmlns="http://www.w3.org/2000/svg">
                    <path fill="{cor_balao}" d="M172 501C26 291 0 269 0 192 0 85 85 0 192 0s192 85 192 192c0 77-26 99-172 309-9 13-29 13-39 0z"/>
                    <text x="50%" y="35%" text-anchor="middle" fill="white" font-family="Arial" font-weight="bold" font-size="120">{n_n}</text>
                </svg>
            </div>'''
        folium.Marker([row['Latitude'], row['Longitude']], icon=folium.DivIcon(icon_size=(42, 52), icon_anchor=(21, 52), html=icon_html)).add_to(m)

    folium_static(m, width=1100)

    # 5. LISTA DE COMANDO (Botão GPS para cada parada)
    st.subheader("🚀 Sequência de Trabalho")
    for _, row in df_otimizado.head(25).iterrows():
        col1, col2 = st.columns([4, 1])
        col1.write(f"**{int(row['Nova_Seq'])}º** — {row['Destination Address']}")
        col2.link_button("🚗 GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
