import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# Configuração de Página
st.set_page_config(page_title="Logística Pro - Shopee", layout="wide")

# Estilização Profissional (Tema Claro com Cards Modernos)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stApp { color: #212529; }
    .delivery-card { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #dee2e6;
        border-left: 6px solid #007AFF; 
        margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .badge-new {
        background-color: #007AFF;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
    }
    .badge-old {
        background-color: #e9ecef;
        color: #6c757d;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        margin-left: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Logística Pro - Carlos")

uploaded_file = st.file_uploader("📂 Carregar Planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Lógica de Reordenação Geográfica (Otimização)
    df_otimizado = df.sort_values(by=['Latitude', 'Longitude']).reset_index(drop=True)
    df_otimizado['Nova_Parada'] = df_otimizado.index + 1

    st.subheader("🗺️ Mapa de Rota Profissional")

    centro_lat = df['Latitude'].mean()
    centro_lon = df['Longitude'].mean()
    
    # Criando o mapa
    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=14, tiles="cartodbpositron")

    for i, row in df_otimizado.iterrows():
        # HTML do Marcador Profissional (Pino com número)
        num_exibido = f"{int(row['Stop'])}➔{int(row['Nova_Parada'])}"
        
        icon_html = f"""
            <div style="position: relative; width: 40px; height: 40px;">
                <svg viewBox="0 0 384 512" style="width: 40px; height: 40px; fill: #007AFF; filter: drop-shadow(2px 2px 2px rgba(0,0,0,0.3));">
                    <path d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <div style="
                    position: absolute; 
                    top: 12px; 
                    left: 0; 
                    width: 40px; 
                    text-align: center; 
                    color: white; 
                    font-weight: bold; 
                    font-size: 10px;
                    font-family: Arial;
                ">{num_exibido}</div>
            </div>
        """
        
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(f"<b>Parada {row['Nova_Parada']}</b><br>{row['Destination Address']}", max_width=300),
            icon=folium.DivIcon(
                icon_size=(40, 40),
                icon_anchor=(20, 40),
                html=icon_html
            )
        ).add_to(m)

    folium_static(m, width=700)

    st.subheader("📋 Lista de Trabalho")
    
    for i, row in df_otimizado.iterrows():
        with st.container():
            st.markdown(f"""
            <div class="delivery-card">
                <span class="badge-new">Parada {int(row['Nova_Parada'])}</span>
                <span class="badge-old">Original: {int(row['Stop'])}</span><br><br>
                <b style="font-size: 18px; color: #1a1a1a;">{row['Destination Address']}</b><br>
                <span style="color: #495057;">📍 {row['Bairro']} | 📦 {row['SPX TN']}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Botão de Navegação Estilizado
            maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['Latitude']},{row['Longitude']}&travelmode=driving"
            st.link_button(f"🗺️ INICIAR NAVEGAÇÃO", maps_url, use_container_width=True)
            st.write("")
