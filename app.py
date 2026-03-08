import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

st.set_page_config(page_title="Shopee Pro - Carlos", layout="wide")

# Estilo da Interface e Cards
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .delivery-card { 
        background-color: #ffffff; padding: 12px; border-radius: 10px; 
        border-left: 6px solid #007AFF; margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1); color: #212529; font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 Roteirizador Otimizado")

uploaded_file = st.file_uploader("Suba sua planilha aqui", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # OTIMIZAÇÃO: Ordena por Bairro e depois por nome da Rua
    # Isso agrupa as entregas na mesma região, evitando cruzar avenidas toda hora
    df_otimizado = df.sort_values(by=['Bairro', 'Destination Address']).reset_index(drop=True)
    df_otimizado['Nova_Parada'] = range(1, len(df_otimizado) + 1)

    st.subheader("📍 Mapa de Visão Geral")
    centro = [df_otimizado['Latitude'].mean(), df_otimizado['Longitude'].mean()]
    m = folium.Map(location=centro, zoom_start=14)

    # Linha de percurso mais fina
    pontos = df_otimizado[['Latitude', 'Longitude']].values.tolist()
    folium.PolyLine(pontos, color="#007AFF", weight=2, opacity=0.4).add_to(m)

    for i, row in df_otimizado.iterrows():
        n_atual = int(row['Nova_Parada'])
        n_orig = int(row['Stop'])
        
        # BALÃO AINDA MENOR (32px de largura)
        icon_html = f"""
            <div style="position: relative; width: 32px; height: 42px;">
                <svg viewBox="0 0 384 512" style="width: 32px; height: 42px; position: absolute; z-index: 1;">
                    <defs>
                        <linearGradient id="grad{i}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                            <stop offset="50%" style="stop-color:#6c757d;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#grad{i})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <div style="position: absolute; top: 3px; width: 32px; text-align: center; color: white; font-weight: bold; font-size: 11px; z-index: 2;">{n_atual}</div>
                <div style="position: absolute; top: 18px; width: 32px; text-align: center; color: #FFD700; font-weight: bold; font-size: 8px; z-index: 2;">{n_orig}</div>
            </div>
        """
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(icon_size=(32, 42), icon_anchor=(16, 42), html=icon_html)
        ).add_to(m)

    folium_static(m, width=700)

    st.subheader("📋 Lista de Sequência")
    for i, row in df_otimizado.iterrows():
        with st.container():
            st.markdown(f"""
                <div class="delivery-card">
                    <b>{int(row['Nova_Parada'])}</b> <small>(Original: {int(row['Stop'])})</small> - {row['Destination Address']}<br>
                    <small>Bairro: {row['Bairro']}</small>
                </div>
            """, unsafe_allow_html=True)
            
            lat, lon = row['Latitude'], row['Longitude']
            # Este link abre o Google Maps REAL que resolve a contramão
            link = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving"
            st.link_button(f"🚩 NAVEGAR PARADA {int(row['Nova_Parada'])}", link, use_container_width=True)
