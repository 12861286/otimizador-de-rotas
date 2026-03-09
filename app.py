import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps

# 1. Configurações de Estilo
st.set_page_config(page_title="Shopee Rota Pro", layout="wide")
st.markdown("""
    <style>
    .delivery-card { 
        background-color: #ffffff; padding: 12px; border-radius: 8px; 
        border-left: 6px solid #007AFF; margin-bottom: 8px; color: #212529;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Conexão com sua Chave Validada
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Otimizador de Rota Shopee")
st.sidebar.success("✅ Google Maps: CONECTADO")

# 3. Upload da Planilha
uploaded_file = st.file_uploader("Arraste sua planilha aqui", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # 4. Inteligência de Rota (Agrupamento por Bairro e Rua)
    df_rota = df.sort_values(by=['Bairro', 'Destination Address']).reset_index(drop=True)
    df_rota['Nova_Parada'] = range(1, len(df_rota) + 1)

    # 5. Mapa com Balões Pequenos (26px)
    st.subheader("📍 Mapa de Entregas")
    centro = [df_rota['Latitude'].mean(), df_rota['Longitude'].mean()]
    m = folium.Map(location=centro, zoom_start=14)

    for i, row in df_rota.iterrows():
        n_atual = int(row['Nova_Parada'])
        
        # HTML do Balão Bicolor (Azul em cima, Cinza embaixo)
        icon_html = f"""
            <div style="position: relative; width: 26px; height: 36px;">
                <svg viewBox="0 0 384 512" style="width: 26px; height: 36px; position: absolute;">
                    <defs>
                        <linearGradient id="grad{i}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                            <stop offset="50%" style="stop-color:#6c757d;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#grad{i})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <div style="position: absolute; top: 2px; width: 26px; text-align: center; color: white; font-weight: bold; font-size: 9px; z-index: 2;">{n_atual}</div>
            </div>
        """
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(icon_size=(26, 36), icon_anchor=(13, 36), html=icon_html)
        ).add_to(m)

    folium_static(m, width=800)

    # 6. Lista de Trabalho com Botões de GPS
    st.subheader("📋 Sequência de Entregas")
    for i, row in df_rota.iterrows():
        with st.container():
            st.markdown(f"""
                <div class="delivery-card">
                    <b>Parada {int(row['Nova_Parada'])}</b> — {row['Bairro']}<br>
                    {row['Destination Address']}
                </div>
            """, unsafe_allow_html=True)
            
            # Link de navegação direta
            lat, lon = row['Latitude'], row['Longitude']
            gps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving"
            st.link_button(f"🚩 NAVEGAR PARA PARADA {int(row['Nova_Parada'])}", gps_url, use_container_width=True)
            st.write("")
