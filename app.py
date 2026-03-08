import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# Configuração de página
st.set_page_config(page_title="Circuit Style - Shopee", layout="wide")

# CSS para visual "Dark Mode" e botões grandes
st.markdown("""
    <style>
    .main { background-color: #121212; }
    .stApp { background-color: #121212; color: #FFFFFF; }
    .delivery-card { 
        background-color: #1E1E1E; 
        padding: 20px; 
        border-radius: 12px; 
        border-left: 5px solid #007AFF; 
        margin-bottom: 15px;
    }
    .stop-number {
        background-color: #007AFF;
        color: white;
        padding: 5px 12px;
        border-radius: 50%;
        font-weight: bold;
        margin-right: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📍 Rota Shopee Otimizada")

uploaded_file = st.file_uploader("Subir arquivo da Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Criando o Mapa com Folium (permite números nos balões)
    st.subheader("🗺️ Mapa de Percurso")
    
    # Centraliza o mapa na primeira entrega
    centro_lat = df['Latitude'].mean()
    centro_lon = df['Longitude'].mean()
    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=14, tiles="cartodbpositron" if False else "OpenStreetMap")

    for i, row in df.iterrows():
        # Adiciona marcador com o número da parada
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=f"Parada {row['Stop']}\n{row['Destination Address']}",
            icon=folium.DivIcon(html=f"""
                <div style="
                    background-color: #007AFF; 
                    color: white; 
                    border-radius: 50%; 
                    width: 25px; 
                    height: 25px; 
                    display: flex; 
                    justify-content: center; 
                    align-items: center; 
                    font-weight: bold;
                    border: 2px solid white;
                    shadow: 2px 2px 5px rgba(0,0,0,0.5);
                ">{row['Stop']}</div>""")
        ).add_to(m)

    folium_static(m, width=700)

    # Lista de Entregas estilo Circuit
    st.subheader("📦 Próximas Entregas")
    
    for i, row in df.iterrows():
        with st.container():
            st.markdown(f"""
            <div class="delivery-card">
                <span class="stop-number">{row['Stop']}</span>
                <b style="font-size: 18px;">{row['Destination Address']}</b><br>
                <span style="color: #BBBBBB;">Bairro: {row['Bairro']} | Pacote: {row['SPX TN']}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Botão de Navegação
            lat, lon = row['Latitude'], row['Longitude']
            # Link otimizado para abrir direto no App do Google Maps/Waze no celular
            maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving"
            
            st.link_button(f"🚀 NAVEGAR PARA PARADA {row['Stop']}", maps_url, use_container_width=True)
            st.write("")
