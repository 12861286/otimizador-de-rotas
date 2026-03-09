import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# Configuração básica para abrir rápido
st.set_page_config(page_title="Router Master Pro", layout="wide")

st.title("🚚 Router Master Pro - Modo de Emergência")

# Interface de upload
uploaded_file = st.file_uploader("Suba sua planilha (CSV ou XLSX)", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        # Carrega os dados de forma simples
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Limpa linhas sem coordenadas
        df = df.dropna(subset=['Latitude', 'Longitude'])
        st.success(f"✅ {len(df)} paradas encontradas!")

        # Cria o mapa usando a primeira parada como centro
        centro = [df.iloc[0]['Latitude'], df.iloc[0]['Longitude']]
        m = folium.Map(location=centro, zoom_start=14)

        # Adiciona os balões na ordem exata da planilha
        for i, row in df.iterrows():
            num = i + 1
            # Balão azul simples com o número
            folium.Marker(
                [row['Latitude'], row['Longitude']],
                icon=folium.DivIcon(html=f'''
                    <div style="width: 30px; height: 30px; background:#007AFF; border:2px solid white; 
                    border-radius:50%; display:flex; align-items:center; justify-content:center; 
                    color:white; font-weight:bold; font-size:12px;">{num}</div>'''),
                popup=f"Parada {num}"
            ).add_to(m)

        # Traça a linha azul simples entre os pontos
        pontos = df[['Latitude', 'Longitude']].values.tolist()
        folium.PolyLine(pontos, color="#007AFF", weight=3).add_to(m)

        # Exibe o mapa
        folium_static(m, width=1000)

        # Lista de GPS rápida
        st.subheader("📋 Lista de Entrega")
        for i, row in df.iterrows():
            st.link_button(f"🚩 {i+1}º: {row.get('Destination Address', 'Abrir GPS')}", 
                          f"https://www.google.com/maps/search/?api=1&query={row['Latitude']},{row['Longitude']}")

    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
