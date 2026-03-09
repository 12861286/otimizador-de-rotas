import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation
from sklearn.cluster import KMeans

# Configurações
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Versão Fluxo Contínuo")

loc = get_geolocation()
uploaded_file = st.file_uploader("Suba sua planilha", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    if loc:
        lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
        st.success("📍 GPS Conectado.")
    else:
        lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']

    # LÓGICA DE FLUXO (Corrige o erro de deixar pontos para trás)
    def organizar_fluxo_contínuo(df, l_i, o_i):
        # Usamos 12 setores para garantir que áreas pequenas sejam fechadas totalmente
        kmeans = KMeans(n_clusters=12, random_state=42, n_init=10)
        df['Setor'] = kmeans.fit_predict(df[['Latitude', 'Longitude']])
        
        centros = kmeans.cluster_centers_
        # Ordena os setores pela distância do ponto inicial
        dist_setores = np.sqrt((centros[:,0] - l_i)**2 + (centros[:,1] - o_i)**2)
        ordem_setores = np.argsort(dist_setores)
        
        rota_final = []
        l_atual, o_atual = l_i, o_i
        
        for s in ordem_setores:
            df_setor = df[df['Setor'] == s].copy()
            while not df_setor.empty:
                # Dentro de cada setor, pega sempre o mais próximo
                df_setor['dist'] = np.sqrt((df_setor['Latitude'] - l_atual)**2 + (df_setor['Longitude'] - o_atual)**2)
                idx = df_setor['dist'].idxmin()
                ponto = df_setor.loc[idx]
                rota_final.append(ponto)
                l_atual, o_atual = ponto['Latitude'], ponto['Longitude']
                df_setor = df_setor.drop(idx)
        return pd.DataFrame(rota_final)

    df_otimizado = organizar_fluxo_contínuo(df_raw, lat_ini, lon_ini)
    df_otimizado['Nova_Seq'] = range(1, len(df_otimizado) + 1)

    m = folium.Map(location=[lat_ini, lon_ini], zoom_start=14)

    # TRAÇADO EM LOTES (Para evitar o erro de MAX_WAYPOINTS)
    # Mostra a linha azul para as primeiras 25 paradas
    lote_linha = df_otimizado.head(25)
    pts_lote = [[lat_ini, lon_ini]] + lote_linha[['Latitude', 'Longitude']].values.tolist()
    
    try:
        res = gmaps.directions(pts_lote[0], pts_lote[-1], waypoints=pts_lote[1:-1], mode="driving")
        if res:
            poly = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
            folium.PolyLine([(p['lat'], p['lng']) for p in poly], color="#007AFF", weight=6).add_to(m)
    except: pass

    # BALÕES (Sempre visíveis com a cor do lote atual)
    for i, row in df_otimizado.iterrows():
        n_n, n_o = int(row['Nova_Seq']), int(row.get('Parada Original', i+1))
        cor = "#007AFF" if n_n <= 25 else "#495057"
        
        icon_html = f'''
            <div style="width: 42px; height: 52px;">
                <svg viewBox="0 0 384 512">
                    <defs><linearGradient id="g{n_n}" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="50%" style="stop-color:{cor};" />
                        <stop offset="50%" style="stop-color:#212529;" />
                    </linearGradient></defs>
                    <path fill="url(#g{n_n})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                    <text x="50%" y="30%" dominant-baseline="middle" text-anchor="middle" fill="white" font-family="Arial" font-weight="bold" font-size="110">{n_n}</text>
                </svg>
            </div>'''
        folium.Marker([row['Latitude'], row['Longitude']], icon=folium.DivIcon(icon_size=(42, 52), html=icon_html)).add_to(m)

    folium_static(m, width=1100)
    
    # LISTA COM BOTÃO DE FILTRO
    st.subheader("📋 Lista de Entregas Otimizada")
    mostrar_apenas_proximas = st.checkbox("Mostrar apenas as próximas 15 paradas", value=True)
    
    lista_exibicao = df_otimizado.head(15) if mostrar_apenas_proximas else df_otimizado
    
    for _, row in lista_exibicao.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            col1.write(f"**{int(row['Nova_Seq'])}º** — {row['Destination Address']}")
            col2.link_button("🚗 GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
