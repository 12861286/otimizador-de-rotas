import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
from streamlit_js_eval import get_geolocation

# Setup da API
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Ordem da Planilha")

# Tenta capturar sua localização atual
loc = get_geolocation()
uploaded_file = st.file_uploader("Suba sua planilha com a ordem definida", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # Carrega os dados
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # IMPORTANTE: Aqui ele usa a ordem que já está nas linhas da planilha
    # Garante que as colunas Latitude e Longitude existam
    df = df.dropna(subset=['Latitude', 'Longitude'])
    
    # Ponto inicial (GPS ou primeira linha)
    if loc and 'coords' in loc:
        lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
    else:
        lat_ini, lon_ini = df.iloc[0]['Latitude'], df.iloc[0]['Longitude']

    # Mapa Instantâneo
    m = folium.Map(location=[lat_ini, lon_ini], zoom_start=15)

    # TRAÇADO: Faz a linha azul seguindo a ordem das linhas (1, 2, 3...)
    # Pegamos as primeiras 25 paradas para a linha ficar precisa no GPS
    proximos = df.head(25)
    pts_rota = [[lat_ini, lon_ini]] + proximos[['Latitude', 'Longitude']].values.tolist()
    
    try:
        # Pede ao Google o caminho real de direção para essa sequência exata
        res = gmaps.directions(pts_rota[0], pts_rota[-1], waypoints=pts_rota[1:-1], mode="driving")
        if res:
            from googlemaps import convert
            polyline = convert.decode_polyline(res[0]['overview_polyline']['points'])
            folium.PolyLine([(p['lat'], p['lng']) for p in polyline], color="#007AFF", weight=6).add_to(m)
    except:
        # Se a API falhar, desenha linha reta para não travar
        folium.PolyLine(pts_rota, color="#007AFF", weight=2, dash_array='5').add_to(m)

    # BALÕES: Coloca todos os pontos no mapa com o número da linha
    for i, row in df.iterrows():
        num_parada = i + 1 # Usa a ordem da linha
        cor_balao = "#007AFF" if num_parada <= 25 else "#6c757d"
        
        icon_html = f'''
            <div style="width: 35px; height: 35px; background:{cor_balao}; border:2px solid white; 
            border-radius:50%; display:flex; align-items:center; justify-content:center; 
            color:white; font-weight:bold; font-size:13px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
            {num_parada}</div>'''
        
        folium.Marker(
            [row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(html=icon_html),
            popup=f"Parada {num_parada}: {row.get('Destination Address', 'Endereço')}"
        ).add_to(m)

    # Exibe o mapa
    folium_static(m, width=1100)

    # LISTA DE BOTÕES (Sequência exata da planilha)
    st.subheader("📋 Lista de Entregas (Ordem Original)")
    for i, row in df.iterrows():
        num = i + 1
        with st.container():
            col1, col2 = st.columns([5, 1])
            col1.write(f"**{num}º** — {row.get('Destination Address', 'Sem endereço')}")
            col2.link_button("🚗 GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
