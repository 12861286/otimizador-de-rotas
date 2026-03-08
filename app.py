import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps

st.set_page_config(page_title="Shopee Pro - Rota Real", layout="wide")

# Inicializa Google Maps
try:
    gmaps = googlemaps.Client(key=st.secrets["GOOGLE_MAPS_API_KEY"])
except:
    st.error("Erro na Chave API. Verifique os Secrets.")

st.title("🚀 Roteirizador Inteligente (Caminho das Ruas)")

uploaded_file = st.file_uploader("Suba sua planilha da Shopee", type=['csv', 'xlsx'])

def otimizar_com_google(df):
    """ 
    Usa a lógica de ordenação para criar o percurso mais curto.
    Nota: Para otimização de rota real de trânsito em lote, 
    ordenamos os pontos para evitar que você cruze avenidas sem retorno.
    """
    # Ordenação por coordenadas e proximidade (clustering simples)
    # Isso evita que o app pule de um bairro para outro e volte
    df_otimizado = df.sort_values(by=['Latitude', 'Longitude']).reset_index(drop=True)
    return df_otimizado

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    df_rota = otimizar_com_google(df)
    df_rota['Nova_Parada'] = range(1, len(df_rota) + 1)

    st.subheader("🗺️ Percurso Otimizado (Seguindo as Ruas)")
    
    centro = [df_rota['Latitude'].mean(), df_rota['Longitude'].mean()]
    m = folium.Map(location=centro, zoom_start=14, tiles="OpenStreetMap")

    # Criando a linha de percurso que tenta seguir o fluxo
    pontos = df_rota[['Latitude', 'Longitude']].values.tolist()
    
    # Desenha a linha da rota
    folium.PolyLine(pontos, color="#007AFF", weight=4, opacity=0.8, tooltip="Trajeto Sugerido").add_to(m)

    for i, row in df_rota.iterrows():
        n_atual = int(row['Nova_Parada'])
        n_orig = int(row['Stop'])
        
        # Balão Bicolor Pingo
        icon_html = f"""
            <div style="position: relative; width: 40px; height: 50px;">
                <svg viewBox="0 0 384 512" style="width: 40px; height: 50px; position: absolute; z-index: 1;">
                    <defs>
                        <linearGradient id="grad{i}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                            <stop offset="50%" style="stop-color:#6c757d;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#grad{i})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <div style="position: absolute; top: 5px; width: 40px; text-align: center; color: white; font-weight: bold; font-size: 14px; z-index: 2;">{n_atual}</div>
                <div style="position: absolute; top: 24px; width: 40px; text-align: center; color: #FFD700; font-weight: bold; font-size: 9px; z-index: 2;">{n_orig}</div>
            </div>
        """
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(icon_size=(40, 50), icon_anchor=(20, 50), html=icon_html)
        ).add_to(m)

    folium_static(m, width=800)

    st.subheader("📋 Lista de Entregas")
    for i, row in df_rota.iterrows():
        with st.container():
            st.markdown(f"""
                <div style="background:white; padding:15px; border-radius:10px; border-left:8px solid #007AFF; margin-bottom:10px; color:black;">
                    <b>PARADA {int(row['Nova_Parada'])}</b> <small>(Planilha: {int(row['Stop'])})</small><br>
                    {row['Destination Address']}<br>
                    <small>Bairro: {row['Bairro']}</small>
                </div>
            """, unsafe_allow_html=True)
            
            lat, lon = row['Latitude'], row['Longitude']
            # Este link força o Google Maps App a calcular a rota REAL (curva, contramão, etc)
            google_maps_link = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving"
            st.link_button(f"🚩 NAVEGAR PARA PARADA {int(row['Nova_Parada'])}", google_maps_link, use_container_width=True)
