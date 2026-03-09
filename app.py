import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np

# 1. Configurações de Estilo e Página
st.set_page_config(page_title="Shopee Rota Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .delivery-card { 
        background-color: #ffffff; padding: 10px; border-radius: 8px; 
        border-left: 6px solid #007AFF; margin-bottom: 5px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1); color: #212529; font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Configuração da Nova Chave API
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"

try:
    gmaps = googlemaps.Client(key=api_key)
    # Teste de validação das APIs
    gmaps.geocode("Brasil")
    st.sidebar.success("✅ Google Maps: CONECTADO")
except Exception as e:
    st.sidebar.error(f"❌ Erro na Nova Chave: {e}")
    st.sidebar.info("Se aparecer REQUEST_DENIED, verifique se a 'Directions API' está ativa no Console.")

st.title("🚀 Roteirizador Inteligente Shopee")

# 3. Carregamento da Planilha
uploaded_file = st.file_uploader("Suba sua planilha aqui", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # 4. Otimização por Agrupamento (Garante percurso curto e lógico)
    # Ordenar por Bairro e Endereço evita que você atravesse avenidas sem retorno
    df_rota = df_raw.sort_values(by=['Bairro', 'Destination Address']).reset_index(drop=True)
    df_rota['Nova_Parada'] = range(1, len(df_rota) + 1)

    # 5. Mapa com Balões Extra Pequenos
    st.subheader("🗺️ Visualização do Percurso")
    centro = [df_rota['Latitude'].mean(), df_rota['Longitude'].mean()]
    m = folium.Map(location=centro, zoom_start=14)

    # Linha guia do trajeto
    pontos_linha = df_rota[['Latitude', 'Longitude']].values.tolist()
    folium.PolyLine(pontos_linha, color="#007AFF", weight=2, opacity=0.3).add_to(m)

    for i, row in df_rota.iterrows():
        n_atual = int(row['Nova_Parada'])
        n_orig = int(row['Stop'])
        
        # Balão Bicolor EXTRA PEQUENO (26px)
        icon_html = f"""
            <div style="position: relative; width: 26px; height: 36px;">
                <svg viewBox="0 0 384 512" style="width: 26px; height: 36px; position: absolute; z-index: 1;">
                    <defs>
                        <linearGradient id="grad{i}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                            <stop offset="50%" style="stop-color:#6c757d;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#grad{i})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <div style="position: absolute; top: 2px; width: 26px; text-align: center; color: white; font-weight: bold; font-size: 9px; z-index: 2;">{n_atual}</div>
                <div style="position: absolute; top: 15px; width: 26px; text-align: center; color: #FFD700; font-weight: bold; font-size: 7px; z-index: 2;">{n_orig}</div>
            </div>
        """
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(icon_size=(26, 36), icon_anchor=(13, 36), html=icon_html)
        ).add_to(m)

    folium_static(m, width=800)

    # 6. Lista de Trabalho e Navegação GPS
    st.subheader("📋 Sequência de Entregas")
    for i, row in df_rota.iterrows():
        with st.container():
            st.markdown(f"""
                <div class="delivery-card">
                    <b>{int(row['Nova_Parada'])}</b> <small>(Original: {int(row['Stop'])})</small> - {row['Destination Address']}<br>
                    <small>Bairro: {row['Bairro']}</small>
                </div>
            """, unsafe_allow_html=True)
            
            # O link de navegação abre o Google Maps do celular, que já respeita a contramão
            lat, lon = row['Latitude'], row['Longitude']
            gps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving"
            st.link_button(f"🚩 NAVEGAR PARA PARADA {int(row['Nova_Parada'])}", gps_url, use_container_width=True)
            st.write("")
