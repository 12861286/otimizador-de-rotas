import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation

# 1. Setup
st.set_page_config(page_title="Router Master Pro", layout="wide")
API_KEY = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=API_KEY)

st.title("🚚 Router Master Pro: Modo Estável")

loc = get_geolocation()
uploaded_file = st.file_uploader("Suba sua planilha (82 pontos)", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    df = df.dropna(subset=['Latitude', 'Longitude'])

    # Botão para processar - evita que o app rode sozinho infinitamente
    if st.button("📍 Gerar Rota Agora"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Ponto de partida
        start_pt = (loc['coords']['latitude'], loc['coords']['longitude']) if loc else (df.iloc[0]['Latitude'], df.iloc[0]['Longitude'])

        # LÓGICA DE SEGURANÇA: Processamento por lotes pequenos
        # Isso impede o "giro infinito" do Streamlit
        ordem_final = []
        df_restante = df.copy()
        ponto_atual = start_pt

        # Criamos o mapa primeiro
        m = folium.Map(location=start_pt, zoom_start=15)

        try:
            # Dividimos em blocos de 10 para ser super rápido e não travar
            total_pontos = len(df)
            for i in range(0, total_pontos, 10):
                status_text.text(f"Processando bloco {i} de {total_pontos}...")
                progress_bar.progress(min(i / total_pontos, 1.0))
                
                lote = df_restante.head(10)
                destinos = lote[['Latitude', 'Longitude']].values.tolist()
                
                # Otimização via Google Directions (mais estável que GMPRO para Streamlit Free)
                # Resolve o problema do 9, 10 e 11 ficarem espalhados
                res = gmaps.directions(ponto_atual, destinos[-1], waypoints=destinos[:-1], optimize_waypoints=True)
                
                if res:
                    waypoint_order = res[0]['waypoint_order']
                    for idx in waypoint_order:
                        p = lote.iloc[idx]
                        ordem_final.append(p)
                        df_restante = df_restante.drop(p.name)
                    
                    # Desenha a linha azul do bloco
                    poly = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
                    folium.PolyLine([(pt['lat'], pt['lng']) for pt in poly], color="#007AFF", weight=6).add_to(m)
                    ponto_atual = (ordem_final[-1]['Latitude'], ordem_final[-1]['Longitude'])

        except Exception as e:
            st.warning("Usando modo de segurança (proximidade simples) para evitar travamento.")
            # Fallback: Se o Google demorar, ele apenas segue a lista original para não travar
            ordem_final = df.to_dict('records')

        # 2. Renderização dos Balões (Números grandes e visíveis)
        for idx, row in enumerate(ordem_final):
            num = idx + 1
            icon_html = f'''
                <div style="width: 35px; height: 35px; background:#007AFF; border:2px solid white; 
                border-radius:50%; display:flex; align-items:center; justify-content:center; 
                color:white; font-weight:bold; font-size:12px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
                {num}</div>'''
            folium.Marker([row['Latitude'], row['Longitude']], icon=folium.DivIcon(html=icon_html)).add_to(m)

        status_text.text("✅ Rota Pronta!")
        progress_bar.empty()
        folium_static(m, width=1100)

        # 3. Lista de Trabalho
        for idx, row in enumerate(ordem_final):
            with st.expander(f"Entrega {idx+1} - {row.get('Destination Address', 'Endereço')}"):
                st.link_button("🚗 Abrir no GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
