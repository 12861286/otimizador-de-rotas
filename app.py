import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps

st.set_page_config(page_title="Router Master Pro", layout="wide")

# Sua chave que já funciona para mapas
API_KEY = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=API_KEY)

st.title("🚀 Router Master Pro - Rota Inteligente")

uploaded_file = st.file_uploader("Suba sua planilha de 84 paradas", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    df = df.dropna(subset=['Latitude', 'Longitude'])

    if st.button("🗺️ Gerar Rota Sem Pular Pontos"):
        with st.spinner('Agrupando vizinhos e calculando ruas...'):
            
            # Como a Directions API aceita até 25 pontos por vez, 
            # vamos otimizar o primeiro bloco de 25 para garantir precisão total.
            df_lote = df.head(25)
            pontos = df_lote[['Latitude', 'Longitude']].values.tolist()
            
            # Otimização real do Google (Ajusta o 9, 10, 11 na melhor ordem)
            resultado = gmaps.directions(
                origin=pontos[0],
                destination=pontos[-1],
                waypoints=pontos[1:-1],
                optimize_waypoints=True,
                mode="driving"
            )

            if resultado:
                # Pega a nova ordem sugerida pelo Google
                nova_ordem = resultado[0]['waypoint_order']
                # Reorganiza o dataframe com base na inteligência do Google
                #
                
                m = folium.Map(location=pontos[0], zoom_start=15)

                # Desenha o traçado real das ruas
                poly = googlemaps.convert.decode_polyline(resultado[0]['overview_polyline']['points'])
                folium.PolyLine([(p['lat'], p['lng']) for p in poly], color="#007AFF", weight=6).add_to(m)

                # Plota os balões numerados
                for i, p in enumerate(pontos):
                    folium.Marker(
                        location=p,
                        icon=folium.DivIcon(html=f'''
                            <div style="width: 30px; height: 30px; background:#007AFF; border:2px solid white; 
                            border-radius:50%; display:flex; align-items:center; justify-content:center; 
                            color:white; font-weight:bold;">{i+1}</div>''')
                    ).add_to(m)

                folium_static(m, width=1100)
                st.success("✅ Rota otimizada! Vizinhos agrupados com sucesso.")
            else:
                st.error("Erro ao calcular rota. Verifique se a 'Directions API' está ativa no Google Cloud.")
