import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

st.set_page_config(page_title="Shopee Pro - Carlos", layout="wide")

# Estilo da Interface
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .delivery-card { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 12px; 
        border-left: 8px solid #007AFF; 
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: #212529;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 Roteirizador Shopee")

uploaded_file = st.file_uploader("Suba sua planilha aqui", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Otimização por proximidade
    df_otimizado = df.sort_values(by=['Latitude', 'Longitude']).reset_index(drop=True)
    df_otimizado['Nova_Parada'] = df_otimizado.index + 1

    st.subheader("📍 Mapa de Entregas")
    centro_lat, centro_lon = df['Latitude'].mean(), df['Longitude'].mean()
    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=14)

    for i, row in df_otimizado.iterrows():
        n_atual = int(row['Nova_Parada'])
        n_orig = int(row['Stop'])
        
        # HTML CORRIGIDO: O texto agora fica GARANTIDO na frente da gota
        icon_html = f"""
            <div style="position: relative; width: 50px; height: 60px;">
                <svg viewBox="0 0 384 512" style="width: 50px; height: 60px; fill: #007AFF; position: absolute; top: 0; left: 0; z-index: 1;">
                    <path d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <div style="
                    position: absolute; 
                    top: 5px; 
                    width: 50px; 
                    text-align: center; 
                    color: white; 
                    font-weight: bold; 
                    font-size: 18px; 
                    z-index: 2;
                    font-family: Arial;
                ">{n_atual}</div>
                <div style="
                    position: absolute; 
                    top: 28px; 
                    width: 50px; 
                    text-align: center; 
                    color: #FFD700; 
                    font-weight: bold; 
                    font-size: 11px; 
                    z-index: 2;
                    font-family: Arial;
                ">{n_orig}</div>
            </div>
        """
        
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(
                icon_size=(50, 60),
                icon_anchor=(25, 60),
                html=icon_html
            ),
            popup=f"Nova: {n_atual} | Original: {n_orig}"
        ).add_to(m)

    folium_static(m, width=700)

    # LISTA DE CARDS
    st.subheader("📋 Sequência de Entregas")
    for i, row in df_otimizado.iterrows():
        with st.container():
            st.markdown(f"""
            <div class="delivery-card">
                <b style="font-size: 1.2em; color: #007AFF;">PARADA {int(row['Nova_Parada'])}</b> 
                <span style="color: #888;">(Original: {int(row['Stop'])})</span><br>
                <b>Endereço:</b> {row['Destination Address']}<br>
                <b>Bairro:</b> {row['Bairro']}
            </div>
            """, unsafe_allow_html=True)
            
            link = f"https://www.google.com/maps/dir/?api=1&destination={row['Latitude']},{row['Longitude']}&travelmode=driving"
            st.link_button(f"🚩 INICIAR GPS - PARADA {int(row['Nova_Parada'])}", link, use_container_width=True)
            st.write("")
