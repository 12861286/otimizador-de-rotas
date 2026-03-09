import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps

# Configurações do App
st.set_page_config(page_title="Router Master Pro", layout="wide")

# Chave de API - Certifique-se que as APIs Directions e Distance Matrix estão ativas
API_KEY = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=API_KEY)

st.title("🚚 Router Master Pro: Versão Estável")

# Upload do Arquivo
uploaded_file = st.file_uploader("Suba sua planilha de entregas", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # Carregamento rápido dos dados
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        df = df.dropna(subset=['Latitude', 'Longitude'])
        st.success(f"✅ {len(df)} paradas carregadas!")

        # Botão de disparo - ISSO EVITA O APP FICAR "CODANDO" INFINITAMENTE
        if st.button("🗺️ Gerar Mapa de Entregas"):
            with st.spinner('Desenhando rota...'):
                
                # Ponto de partida padrão (primeira linha da planilha)
                start_lat = df.iloc[0]['Latitude']
                start_lon = df.iloc[0]['Longitude']

                # Cria o mapa centralizado
                m = folium.Map(location=[start_lat, start_lon], zoom_start=14)

                # BALÕES: Coloca os pontos na ordem exata da planilha (sem adivinhação)
                # Respeita a sequência que você já tem
                for i, row in df.iterrows():
                    num = i + 1
                    icon_html = f'''
                        <div style="width: 32px; height: 32px; background:#007AFF; border:2px solid white; 
                        border-radius:50%; display:flex; align-items:center; justify-content:center; 
                        color:white; font-weight:bold; font-size:12px;">{num}</div>'''
                    
                    folium.Marker(
                        [row['Latitude'], row['Longitude']],
                        icon=folium.DivIcon(html=icon_html),
                        popup=f"Entrega {num}"
                    ).add_to(m)

                # Desenha a linha azul de conexão entre os pontos
                coords = df[['Latitude', 'Longitude']].values.tolist()
                folium.PolyLine(coords, color="#007AFF", weight=3, opacity=0.7).add_to(m)

                # Exibe o mapa
                folium_static(m, width=1100)

                # LISTA DE TRABALHO ABAIXO DO MAPA
                st.subheader("📋 Lista de GPS")
                for i, row in df.iterrows():
                    col1, col2 = st.columns([4, 1])
                    col1.write(f"**{i+1}º** — {row.get('Destination Address', 'Ver no GPS')}")
                    col2.link_button("🚗 Abrir", f"https://www.google.com/maps/search/?api=1&query={row['Latitude']},{row['Longitude']}")

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
