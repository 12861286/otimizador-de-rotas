import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation
from sklearn.cluster import DBSCAN

# Configurações de API
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Verificação de Vizinhos")

loc = get_geolocation()
uploaded_file = st.file_uploader("Suba sua planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    if loc:
        lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
        st.success("📍 GPS Ativo. Verificando rota inteligente...")
    else:
        lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']

    # LÓGICA DE PRÉ-VERIFICAÇÃO: Agrupa quem está perto antes de mover
    def organizar_inteligente(df, l_i, o_i):
        df_temp = df.copy()
        rota_final = []
        l_atual, o_atual = l_i, o_i
        
        while not df_temp.empty:
            # 1. Busca o mais próximo de onde estou
            df_temp['dist'] = np.sqrt((df_temp['Latitude'] - l_atual)**2 + (df_temp['Longitude'] - o_atual)**2)
            idx_proximo = df_temp['dist'].idxmin()
            
            # 2. PRÉ-VERIFICAÇÃO: Quem está num raio de 500m desse próximo?
            ponto_ref = df_temp.loc[idx_proximo]
            vizinhança = df_temp[np.sqrt((df_temp['Latitude'] - ponto_ref['Latitude'])**2 + 
                                       (df_temp['Longitude'] - ponto_ref['Longitude'])**2) < 0.005].copy()
            
            # 3. Ordena esse grupinho interno por proximidade e adiciona na rota
            while not vizinhança.empty:
                vizinhança['dist_interna'] = np.sqrt((vizinhança['Latitude'] - l_atual)**2 + 
                                                   (vizinhança['Longitude'] - o_atual)**2)
                idx_v = vizinhança['dist_interna'].idxmin()
                p_v = vizinhança.loc[idx_v]
                
                rota_final.append(p_v)
                l_atual, o_atual = p_v['Latitude'], p_v['Longitude']
                df_temp = df_temp.drop(idx_v)
                vizinhança = vizinhança.drop(idx_v)
                
        return pd.DataFrame(rota_final)

    df_otimizado = organizar_inteligente(df_raw, lat_ini, lon_ini)
    df_otimizado['Nova_Seq'] = range(1, len(df_otimizado) + 1)

    m = folium.Map(location=[lat_ini, lon_ini], zoom_start=14)

    # TRAÇADO DOS PRÓXIMOS 25 (Respeita o limite da API e sentido da via)
    lote = df_otimizado.head(25)
    pts = [[lat_ini, lon_ini]] + lote[['Latitude', 'Longitude']].values.tolist()
    
    try:
        res = gmaps.directions(pts[0], pts[-1], waypoints=pts[1:-1], mode="driving")
        if res:
            polyline = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
            folium.PolyLine([(p['lat'], p['lng']) for p in polyline], color="#007AFF", weight=6).add_to(m)
    except: pass

    # BALÕES (Números integrados e cores para facilitar a visão)
    for i, row in df_otimizado.iterrows():
        n_n = int(row['Nova_Seq'])
        cor = "#007AFF" if n_n <= 25 else "#495057"
        
        icon_html = f'''
            <div style="width: 42px; height: 52px;">
                <svg viewBox="0 0 384 512">
                    <path fill="{cor}" d="M172 501C26 291 0 269 0 192 0 85 85 0 192 0s192 85 192 192c0 77-26 99-172 309-9 13-29 13-39 0z"/>
                    <text x="50%" y="35%" text-anchor="middle" fill="white" font-family="Arial" font-weight="bold" font-size="120">{n_n}</text>
                </svg>
            </div>'''
        folium.Marker([row['Latitude'], row['Longitude']], icon=folium.DivIcon(icon_size=(42, 52), icon_anchor=(21, 52), html=icon_html)).add_to(m)

    folium_static(m, width=1100)

    # LISTA DE COMANDO GPS
    st.subheader("📋 Ordem de Entrega Verificada")
    for _, row in df_otimizado.head(20).iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.write(f"**{int(row['Nova_Seq'])}º** — {row['Destination Address']}")
            c2.link_button("🚗 Abrir GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
