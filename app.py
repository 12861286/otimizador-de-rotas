import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

st.set_page_config(page_title="Shopee Pro - Carlos", layout="wide")

# Estilo dos Cards e Interface
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
    }
    .btn-nav {
        background-color: #007AFF !important;
        color: white !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 Roteirizador Shopee")

uploaded_file = st.file_uploader("Suba sua planilha aqui", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Simulação de otimização (Agrupamento por proximidade)
    df_otimizado = df.sort_values(by=['Latitude', 'Longitude']).reset_index(drop=True)
    df_otimizado['Nova_Parada'] = df_otimizado.index + 1

    # MAPA
    st.subheader("📍 Mapa de Entregas")
    centro_lat, centro_lon = df['Latitude'].mean(), df['Longitude'].mean()
    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=14)

    for i, row in df_otimizado.iterrows():
        n_atual = int(row['Nova_Parada'])
        n_orig = int(row['Stop'])
        
        # HTML do Balão Duplo Personalizado
        icon_html = f"""
            <div style="
                width: 50px; 
                height: 50px; 
                background-color: white; 
                border: 2px solid #007AFF; 
                border-radius: 8px; 
                display: flex; 
                flex-direction: column; 
                overflow: hidden;
                box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
                text-align: center;
                font-family: Arial;
            ">
                <div style="background-color: #007AFF; color: white; flex: 1.5; font-size: 16px; font-weight: bold; display: flex; align-items: center; justify-content: center;">
                    {n_atual}
                </div>
                <div style="background-color: #eeeeee; color: #555555; flex: 1; font-size: 11px; display: flex; align-items: center; justify-content: center; border-top: 1px solid #ccc;">
                    {n_orig}
                </div>
            </div>
        """
        
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(
                icon_size=(50, 50),
                icon_anchor=(25, 50),
                html=icon_html
            ),
            popup=f"Parada {n_atual} (Original: {n_orig})"
        ).add_to(m)

    folium_static(m, width=700)

    # LISTA DE CARDS
    st.subheader("📋 Sequência de Trabalho")
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
            
            # Link direto para o Google Maps
            lat, lon = row['Latitude'], row['Longitude']
            link = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving"
            st.link_button(f"🚩 IR PARA PARADA {int(row['Nova_Parada'])}", link, use_container_width=True)
            st.write("")
