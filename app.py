import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
import googlemaps
import io

# 1. Configuração Inicial
st.set_page_config(page_title="Router Master Pro | GMPRO", layout="wide", page_icon="🚚")

# 2. CSS para visual profissional
st.markdown("""
<style>
    .main { background: #0d1117; color: #e6edf3; }
    div[data-testid="stButton"] > button {
        background: linear-gradient(135deg, #238636, #2ea043);
        color: white; border: none; border-radius: 8px; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# 3. CHAVE DE API (Coloque a sua aqui)
API_KEY = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=API_KEY)

# 4. Funções Matemáticas e de Rota
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi, dlambda = np.radians(lat2-lat1), np.radians(lon2-lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2*R*np.arcsin(np.sqrt(a))

def optimize_local(df):
    points = df[['Latitude', 'Longitude']].values
    unvisited = list(range(len(points)))
    route = [unvisited.pop(0)]
    while unvisited:
        last = route[-1]
        next_pt = min(unvisited, key=lambda i: haversine(points[last][0], points[last][1], points[i][0], points[i][1]))
        route.append(next_pt)
        unvisited.remove(next_pt)
    return route

def get_real_roads(ordered_points):
    # Pega o traçado das ruas via Google (limite de 25 por trecho)
    try:
        pts = ordered_points[:25] # Focando no primeiro bloco para performance
        res = gmaps.directions(origin=pts[0], destination=pts[-1], 
                               waypoints=pts[1:-1], mode="driving")
        return googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
    except:
        return None

# 5. Construção do Mapa com Balões Numerados
def build_map(df_ordered, road_coords):
    center = [df_ordered['Latitude'].mean(), df_ordered['Longitude'].mean()]
    m = folium.Map(location=center, zoom_start=13, tiles='CartoDB dark_matter')

    # Desenha as ruas reais se o Google retornar
    if road_coords:
        folium.PolyLine([(p['lat'], p['lng']) for p in road_coords], 
                        color='#58a6ff', weight=5, opacity=0.8).add_to(m)
    else:
        # Linha reta de segurança
        folium.PolyLine(df_ordered[['Latitude', 'Longitude']].values, 
                        color='#58a6ff', weight=2, dash_array='5, 5').add_to(m)

    # Marcadores Numerados (1, 2, 3...)
    for idx, row in df_ordered.iterrows():
        num = idx + 1
        icon_html = f'''<div style="background:#58a6ff; width:28px; height:28px; border-radius:50%; 
                        border:2px solid white; color:white; font-weight:bold; display:flex; 
                        align-items:center; justify-content:center; font-size:11px;">{num}</div>'''
        
        folium.Marker(location=[row['Latitude'], row['Longitude']],
                      icon=folium.DivIcon(html=icon_html),
                      popup=f"Parada {num}").add_to(m)
    return m

# 6. Interface Streamlit
st.title("🚚 Router Master Pro")
uploaded_file = st.file_uploader("Suba sua planilha (.csv ou .xlsx)", type=['csv', 'xlsx'])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    df = df.dropna(subset=['Latitude', 'Longitude']).reset_index(drop=True)
    
    if st.button("🚀 Otimizar e Gerar Mapa"):
        with st.spinner("Calculando melhor rota e desenhando ruas..."):
            # Organiza a ordem
            ordem = optimize_local(df)
            df_final = df.iloc[ordem].reset_index(drop=True)
            
            # Pega o traçado real das ruas
            pontos_coord = df_final[['Latitude', 'Longitude']].values.tolist()
            ruas = get_real_roads(pontos_coord)
            
            # Gera o mapa
            mapa = build_map(df_final, ruas)
            st_folium(mapa, use_container_width=True, height=500)
            
            # Tabela e Download
            st.success(f"Rota de {len(df_final)} paradas pronta!")
            st.dataframe(df_final)
            
            buf = io.BytesIO()
            df_final.to_excel(buf, index=False)
            st.download_button("📥 Baixar Planilha em Ordem", data=buf.getvalue(), 
                               file_name="rota_shopee.xlsx")
